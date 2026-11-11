import re


def demo_plan(message: str) -> list[dict]:
    text = message.lower()
    plan = []
    if "attendance" in text or "shortage" in text:
        plan.append({"tool": "check_attendance", "args": {}})
    if "lab" in text or "laboratory" in text:
        plan.append({"tool": "check_lab_availability", "args": {"date_text": "tomorrow", "time_slot": "afternoon", "purpose": "student request"}})
        if "confirm" in text or "book" in text or "reserve" in text:
            plan.append({"tool": "book_lab", "args": {"lab_id": "LAB-204", "date_text": "tomorrow", "time_slot": "afternoon"}})
    if "leave" in text or "sick" in text:
        plan.append({"tool": "prepare_leave_application", "args": {"start_date": "unspecified", "end_date": "unspecified", "reason": re.sub(r"\s+", " ", message)[:300]}})
    return plan
