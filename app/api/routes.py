from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.agent.graph import agent_graph
from app.agent.demo import demo_plan
from app.services.campus_tools import TOOLS
from app.storage.repository import add_event, create_task, finish_task, get_task, metric_rows

router = APIRouter(prefix="/api")


class RequestBody(BaseModel):
    student_id: str = Field(min_length=2, max_length=64)
    message: str = Field(min_length=2, max_length=2000)
    confirm_actions: bool = False


def run_request(body: RequestBody, baseline: bool = False) -> dict:
    task_id = str(uuid4())
    mode = "baseline" if baseline else "agent"
    create_task(task_id, body.student_id, body.message, mode)
    if baseline:
        add_event(task_id, "baseline", "Running deterministic rule-based baseline.")
    try:
        if baseline:
            plan = demo_plan(body.message)
            tool_map = {tool.name: tool for tool in TOOLS}
            results = []
            add_event(task_id, "plan", "Rule-based plan created.", {"steps": [item["tool"] for item in plan]})
            for item in plan:
                args = dict(item["args"])
                args.setdefault("student_id", body.student_id)
                if item["tool"] in {"book_lab", "prepare_leave_application"}:
                    args["confirmed"] = body.confirm_actions
                add_event(task_id, "tool_call", f"Calling {item['tool']}.", {"tool": item["tool"], "arguments": args})
                observed = tool_map[item["tool"]].invoke(args)
                results.append({"tool": item["tool"], "result": observed})
                add_event(task_id, "observation", f"Observed result from {item['tool']}.", {"tool": item["tool"], "result": observed})
            needs_confirmation = any(item["result"].get("status") == "confirmation_required" for item in results)
            status = "awaiting_confirmation" if needs_confirmation else "completed"
            response = ("I couldn't identify a supported campus service in that request. Please specify lab booking, attendance, or leave."
                        if not plan else "Here are the results: " + "; ".join(f"{item['tool']}: {item['result']}" for item in results))
            if needs_confirmation:
                response += " Review the details and submit again with confirmation to proceed."
            result = {"status": status, "response": response, "results": results}
            add_event(task_id, "status", f"Task {status}.", {"status": status})
        else:
            result = agent_graph.invoke({"task_id": task_id, "student_id": body.student_id,
                                         "message": body.message, "confirm_actions": body.confirm_actions})
        finish_task(task_id, result.get("status", "completed"), result.get("response", ""))
        return {"task_id": task_id, "status": result.get("status"), "response": result.get("response"),
                "results": result.get("results", []), "mode": "baseline" if baseline else "agent"}
    except Exception as exc:
        finish_task(task_id, "escalated", "The request could not be completed; staff follow-up is required.")
        add_event(task_id, "escalation", "Agent execution failed and was escalated.", {"error": str(exc)})
        raise HTTPException(status_code=500, detail={"task_id": task_id, "message": "Agent execution failed; see task event log."}) from exc


@router.post("/requests")
def create_request(body: RequestBody) -> dict:
    return run_request(body)


@router.post("/baseline")
def run_baseline(body: RequestBody) -> dict:
    # Keep the comparison path deterministic and use the same validated tool/API layer.
    return run_request(body, baseline=True)


@router.get("/tasks/{task_id}")
def task_status(task_id: str) -> dict:
    result = get_task(task_id)
    if not result:
        raise HTTPException(status_code=404, detail="Task not found")
    return result


@router.get("/metrics")
def metrics() -> dict:
    rows = metric_rows()
    summary = {}
    for mode in ("agent", "baseline"):
        mode_rows = [status for status, row_mode in rows if row_mode == mode]
        completed = sum(status == "completed" for status in mode_rows)
        summary[mode] = {"total": len(mode_rows), "completed": completed,
                         "completion_rate": round(completed / len(mode_rows), 3) if mode_rows else 0.0,
                         "by_status": {status: mode_rows.count(status) for status in set(mode_rows)}}
    return {"comparison": summary,
            "note": "Run the same labeled request set through /api/requests and /api/baseline for a meaningful comparison."}
