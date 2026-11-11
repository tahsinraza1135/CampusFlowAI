from typing import TypedDict

from langchain_openai import ChatOpenAI
from langgraph.graph import END, START, StateGraph

from app.agent.demo import demo_plan
from app.config import settings
from app.services.campus_tools import TOOLS
from app.storage.repository import add_event


class AgentState(TypedDict, total=False):
    task_id: str
    student_id: str
    message: str
    confirm_actions: bool
    plan: list[dict]
    results: list[dict]
    response: str
    status: str


TOOL_MAP = {tool.name: tool for tool in TOOLS}


def plan_node(state: AgentState) -> dict:
    add_event(state["task_id"], "planning", "Creating a task plan.")
    if settings.agent_mode.lower() == "llm":
        if not settings.model_api_key:
            raise ValueError("MODEL_API_KEY is required when AGENT_MODE=llm")
        model = ChatOpenAI(model=settings.model_name, api_key=settings.model_api_key,
                           base_url=settings.model_base_url, temperature=0)
        prompt = (
            "Return a JSON array of tool calls for this campus request. Allowed tools: "
            "check_attendance(student_id), check_lab_availability(date_text,time_slot,purpose), "
            "book_lab(student_id,lab_id,date_text,time_slot,confirmed), "
            "prepare_leave_application(student_id,start_date,end_date,reason,confirmed). "
            "Use only needed tools, do not invent dates, and do not book or submit without explicit confirmation. "
            "Return JSON only, format [{\"tool\": name, \"args\": {...}}]. Request: " + state["message"]
        )
        raw = model.invoke(prompt).content
        import json
        plan = json.loads(raw if isinstance(raw, str) else "[]")
        if not isinstance(plan, list):
            raise ValueError("Model plan must be a JSON array")
    else:
        plan = demo_plan(state["message"])
    safe_plan = []
    for item in plan[: settings.max_tool_steps]:
        name = item.get("tool")
        if name in TOOL_MAP and isinstance(item.get("args", {}), dict):
            safe_plan.append({"tool": name, "args": item.get("args", {})})
    add_event(state["task_id"], "plan", "Plan created.", {"steps": [x["tool"] for x in safe_plan]})
    return {"plan": safe_plan, "results": []}


def execute_node(state: AgentState) -> dict:
    results = []
    for item in state.get("plan", []):
        name, args = item["tool"], dict(item.get("args", {}))
        args.setdefault("student_id", state["student_id"])
        if name in {"book_lab", "prepare_leave_application"}:
            args["confirmed"] = bool(state.get("confirm_actions", False))
        tool = TOOL_MAP[name]
        add_event(state["task_id"], "tool_call", f"Calling {name}.", {"tool": name, "arguments": args})
        try:
            result = tool.invoke(args)
            results.append({"tool": name, "result": result})
            add_event(state["task_id"], "observation", f"Observed result from {name}.", {"tool": name, "result": result})
        except Exception as exc:
            result = {"status": "error", "message": str(exc)}
            results.append({"tool": name, "result": result})
            add_event(state["task_id"], "escalation", f"Tool {name} failed; staff follow-up may be needed.", {"error": str(exc)})
    needs_confirmation = any(r["result"].get("status") == "confirmation_required" for r in results)
    failed = any(r["result"].get("status") == "error" for r in results)
    status = "awaiting_confirmation" if needs_confirmation else ("escalated" if failed else "completed")
    if not state.get("plan"):
        response = "I couldn't identify a supported campus service in that request. Please specify lab booking, attendance, or leave."
    else:
        response = "Here are the results: " + "; ".join(f"{r['tool']}: {r['result']}" for r in results)
        if needs_confirmation:
            response += " Review the details and submit again with confirmation to proceed."
        if failed:
            response += " I recorded the issue for staff follow-up."
    add_event(state["task_id"], "status", f"Task {status}.", {"status": status})
    return {"results": results, "response": response, "status": status}


builder = StateGraph(AgentState)
builder.add_node("plan", plan_node)
builder.add_node("execute_observe", execute_node)
builder.add_edge(START, "plan")
builder.add_edge("plan", "execute_observe")
builder.add_edge("execute_observe", END)
agent_graph = builder.compile()
