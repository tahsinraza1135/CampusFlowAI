from datetime import date

from langchain_core.tools import tool


@tool
def check_attendance(student_id: str) -> dict:
    """Get attendance percentage and shortage status for a student."""
    # Simulated data for the project prototype.
    records = {"S1001": (78.4, 75.0), "S1002": (68.0, 75.0), "S1003": (91.2, 75.0)}
    attended, required = records.get(student_id, (82.0, 75.0))
    return {"student_id": student_id, "percentage": attended, "required_percentage": required, "below_required": attended < required}


@tool
def check_lab_availability(date_text: str, time_slot: str = "afternoon", purpose: str = "general") -> dict:
    """Find an available lab for a date, time slot, and purpose."""
    available = ["LAB-204", "LAB-310"] if "unavailable" not in date_text.lower() else []
    return {"date": date_text or date.today().isoformat(), "time_slot": time_slot, "purpose": purpose, "available_labs": available}


@tool
def book_lab(student_id: str, lab_id: str, date_text: str, time_slot: str = "afternoon", confirmed: bool = False) -> dict:
    """Book an available lab. Requires explicit confirmation from the student."""
    if not confirmed:
        return {"status": "confirmation_required", "message": "Ask the student to confirm the proposed booking."}
    if lab_id not in {"LAB-204", "LAB-310"}:
        return {"status": "unavailable", "message": "That lab is not currently available."}
    return {"status": "confirmed", "booking_id": f"LB-{student_id}-{date_text}-{lab_id}", "lab_id": lab_id, "date": date_text, "time_slot": time_slot}


@tool
def prepare_leave_application(student_id: str, start_date: str, end_date: str, reason: str, confirmed: bool = False) -> dict:
    """Prepare or submit a leave application; submission requires student confirmation."""
    if not confirmed:
        return {"status": "confirmation_required", "draft": {"student_id": student_id, "start_date": start_date, "end_date": end_date, "reason": reason}, "message": "Review this draft and confirm before submission."}
    return {"status": "submitted_pending_approval", "application_id": f"LV-{student_id}-{start_date}", "message": "Application submitted. It is pending staff approval."}


TOOLS = [check_attendance, check_lab_availability, book_lab, prepare_leave_application]
