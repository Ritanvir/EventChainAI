from __future__ import annotations

from sqlalchemy import event, inspect
from sqlalchemy.orm import Session

from ..models import Event
from .ai_planner import ensure_event_plan, is_complete_plan


PLAN_INPUT_FIELDS = (
    "title",
    "category",
    "description",
    "venue",
    "event_date",
    "attendee_capacity",
    "budget_bdt",
)

_guard_registered = False


def _planning_inputs_changed(event_record: Event) -> bool:
    state = inspect(event_record)

    return any(
        state.attrs[field].history.has_changes()
        for field in PLAN_INPUT_FIELDS
    )


def register_ai_plan_guard() -> None:
    """
    Automatically generate an AI plan before an Event is saved.

    This also regenerates the plan when planning information changes.
    """

    global _guard_registered

    if _guard_registered:
        return

    @event.listens_for(Session, "before_flush")
    def generate_missing_ai_plans(
        session: Session,
        _flush_context,
        _instances,
    ) -> None:
        records = set(session.new).union(session.dirty)

        for record in records:
            if not isinstance(record, Event):
                continue

            is_new_event = record in session.new

            inputs_changed = (
                False
                if is_new_event
                else _planning_inputs_changed(record)
            )

            plan_is_missing = not is_complete_plan(record.ai_plan)

            if is_new_event or inputs_changed or plan_is_missing:
                ensure_event_plan(record, force=True)

    _guard_registered = True