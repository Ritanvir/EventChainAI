from __future__ import annotations

import json
from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


# =========================================================
# LANGGRAPH STATE
# =========================================================

class PlannerState(TypedDict, total=False):
    title: str
    category: str
    description: str
    venue: str
    event_date: str
    capacity: int
    total_budget_bdt: float

    profile: dict
    budget: dict
    timeline: list
    risks: list
    resources: list

    final_plan: dict


# =========================================================
# CATEGORY BASED BUDGET WEIGHTS
# =========================================================

CATEGORY_WEIGHTS = {
    "university": {
        "Venue and permits": 0.16,
        "Catering": 0.20,
        "Audio-visual and technology": 0.15,
        "Marketing and communication": 0.12,
        "Guest and programme costs": 0.12,
        "Staff and volunteers": 0.10,
        "Security and safety": 0.07,
        "Contingency": 0.08,
    },

    "conference": {
        "Venue and permits": 0.24,
        "Catering": 0.20,
        "Audio-visual and technology": 0.14,
        "Speakers and programme": 0.13,
        "Marketing and registration": 0.09,
        "Staff and logistics": 0.08,
        "Security and safety": 0.04,
        "Contingency": 0.08,
    },

    "corporate": {
        "Venue and permits": 0.22,
        "Catering": 0.23,
        "Audio-visual and technology": 0.14,
        "Branding and communication": 0.10,
        "Programme and speakers": 0.11,
        "Staff and logistics": 0.09,
        "Security and safety": 0.04,
        "Contingency": 0.07,
    },

    "concert": {
        "Venue and permits": 0.19,
        "Artist and programme costs": 0.22,
        "Stage, sound, and lighting": 0.20,
        "Security and crowd control": 0.10,
        "Marketing and ticketing": 0.10,
        "Staff and logistics": 0.07,
        "Medical and emergency support": 0.04,
        "Contingency": 0.08,
    },

    "social": {
        "Venue and decoration": 0.23,
        "Catering": 0.30,
        "Entertainment": 0.12,
        "Photography and media": 0.08,
        "Invitations and communication": 0.07,
        "Staff and logistics": 0.08,
        "Security and safety": 0.04,
        "Contingency": 0.08,
    },

    "other": {
        "Venue and permits": 0.22,
        "Catering": 0.20,
        "Technology and equipment": 0.14,
        "Programme costs": 0.12,
        "Marketing": 0.10,
        "Staff and logistics": 0.10,
        "Security and safety": 0.05,
        "Contingency": 0.07,
    },
}


# =========================================================
# HELPER
# =========================================================

def _money(value: Decimal) -> float:
    return float(
        value.quantize(
            Decimal("0.01"),
            rounding=ROUND_HALF_UP,
        )
    )


# =========================================================
# STEP 1 - ANALYSE EVENT
# =========================================================

def analyse_event(state: PlannerState) -> dict:

    capacity = int(state["capacity"])

    event_day = datetime.strptime(
        state["event_date"],
        "%Y-%m-%d",
    ).date()

    lead_days = max(
        (event_day - date.today()).days,
        0,
    )

    # Event size
    if capacity <= 100:
        size = "small"

    elif capacity <= 500:
        size = "medium"

    else:
        size = "large"

    # Risk level
    if (
        capacity > 1000
        or state["category"] == "concert"
    ):
        risk_level = "high"

    elif capacity > 250:
        risk_level = "medium"

    else:
        risk_level = "standard"

    estimated_staff = max(
        4,
        round(capacity / 50),
    )

    check_in_points = max(
        1,
        round(capacity / 250),
    )

    return {
        "profile": {
            "event_size": size,
            "risk_level": risk_level,
            "lead_days": lead_days,
            "estimated_staff": estimated_staff,
            "recommended_check_in_points": check_in_points,
        }
    }


# =========================================================
# STEP 2 - BUDGET ALLOCATION
# =========================================================

def allocate_budget(state: PlannerState) -> dict:

    total = Decimal(
        str(state["total_budget_bdt"])
    )

    category = str(
        state["category"]
    ).strip().lower()

    weights = CATEGORY_WEIGHTS.get(
        category,
        CATEGORY_WEIGHTS["other"],
    )

    items = []

    for name, weight in weights.items():

        amount = total * Decimal(
            str(weight)
        )

        items.append(
            {
                "item": name,
                "percentage": int(weight * 100),
                "amount_bdt": _money(amount),
            }
        )

    per_attendee = total / Decimal(
        max(
            int(state["capacity"]),
            1,
        )
    )

    return {
        "budget": {
            "total_bdt": _money(total),
            "per_attendee_bdt": _money(
                per_attendee
            ),
            "items": items,
        }
    }


# =========================================================
# STEP 3 - EVENT TIMELINE
# =========================================================

def create_timeline(state: PlannerState) -> dict:

    event_day = datetime.strptime(
        state["event_date"],
        "%Y-%m-%d",
    ).date()

    lead_days = state["profile"]["lead_days"]

    phases = [
        (
            0.85,
            "Concept and approval",
            "Confirm objectives, audience, scope, and ownership.",
        ),

        (
            0.70,
            "Venue and vendor sourcing",
            "Obtain quotations and shortlist compliant vendors.",
        ),

        (
            0.55,
            "Programme and ticket launch",
            "Finalise programme and publish blockchain ticket sales.",
        ),

        (
            0.35,
            "Marketing and sponsor activation",
            "Run promotion and track sponsor commitments.",
        ),

        (
            0.18,
            "Operational confirmation",
            "Confirm staff, security, equipment, catering, and transport.",
        ),

        (
            0.07,
            "Final readiness review",
            "Complete risk review, rehearsals, and attendee communication.",
        ),

        (
            0.00,
            "Event delivery",
            "Operate check-in, monitor budget, and record incidents.",
        ),

        (
            -0.05,
            "Close-out",
            "Release approved escrows, reconcile funds, and review performance.",
        ),
    ]

    timeline = []

    for fraction, phase, actions in phases:

        if fraction >= 0:

            offset = max(
                0,
                round(
                    lead_days * fraction
                ),
            )

            deadline = (
                event_day
                - timedelta(days=offset)
            )

        else:

            deadline = (
                event_day
                + timedelta(
                    days=max(
                        1,
                        round(
                            lead_days
                            * abs(fraction)
                        ),
                    )
                )
            )

        timeline.append(
            {
                "phase": phase,
                "deadline": deadline.isoformat(),
                "actions": actions,
            }
        )

    return {
        "timeline": timeline
    }


# =========================================================
# STEP 4 - RISK IDENTIFICATION
# =========================================================

def identify_risks(state: PlannerState) -> dict:

    risks = [
        {
            "risk": "Budget overrun",
            "probability": "Medium",
            "impact": "High",
            "mitigation": (
                "Keep contingency ring-fenced and "
                "require approval before scope changes."
            ),
        },

        {
            "risk": "Vendor delay or non-performance",
            "probability": "Medium",
            "impact": "High",
            "mitigation": (
                "Use milestone confirmations and "
                "blockchain escrow before final release."
            ),
        },

        {
            "risk": "Ticket duplication or unauthorised entry",
            "probability": "Low",
            "impact": "High",
            "mitigation": (
                "Verify NFT ownership and mark each "
                "token checked-in only once."
            ),
        },

        {
            "risk": "Low attendance",
            "probability": "Medium",
            "impact": "Medium",
            "mitigation": (
                "Track weekly registrations and "
                "trigger targeted promotion early."
            ),
        },
    ]

    # Extra risk for high-risk event
    if state["profile"]["risk_level"] == "high":

        risks.append(
            {
                "risk": "Crowd safety incident",
                "probability": "Medium",
                "impact": "Critical",
                "mitigation": (
                    "Prepare crowd-flow, medical, emergency, "
                    "and evacuation plans with authorities."
                ),
            }
        )

    # Extra risk if preparation time is short
    if state["profile"]["lead_days"] < 21:

        risks.append(
            {
                "risk": "Insufficient preparation time",
                "probability": "High",
                "impact": "High",
                "mitigation": (
                    "Freeze non-essential scope and run "
                    "daily owner-based action tracking."
                ),
            }
        )

    return {
        "risks": risks
    }


# =========================================================
# STEP 5 - RESOURCE RECOMMENDATION
# =========================================================

def recommend_resources(state: PlannerState) -> dict:

    capacity = int(
        state["capacity"]
    )

    estimated_staff = (
        state["profile"]["estimated_staff"]
    )

    check_in_points = (
        state["profile"][
            "recommended_check_in_points"
        ]
    )

    resources = [
        (
            f"Assign approximately "
            f"{estimated_staff} "
            f"operational staff or volunteers."
        ),

        (
            f"Prepare at least "
            f"{check_in_points} "
            f"digital check-in point(s)."
        ),

        (
            "Keep organizer, finance, logistics, "
            "safety, and communications "
            "responsibilities separate."
        ),

        (
            "Collect at least two comparable "
            "vendor quotations for major budget items."
        ),

        (
            "Confirm an incident-response contact list "
            "before ticket sales close."
        ),
    ]

    if capacity > 500:

        resources.append(
            (
                "Use queue barriers, zoned entry, "
                "and a dedicated crowd-control supervisor."
            )
        )

    return {
        "resources": resources
    }


# =========================================================
# STEP 6 - FINAL AI PLAN
# =========================================================

def finalise_plan(state: PlannerState) -> dict:

    category = str(
        state["category"]
    ).strip().lower()

    summary = (
        f"The recommended plan treats "
        f"'{state['title']}' as a "
        f"{state['profile']['event_size']} "
        f"{category} event with "
        f"{state['profile']['risk_level']} "
        f"operational risk."
    )

    final_plan = {
        "summary": summary,

        "generated_at": (
            datetime.now().isoformat(
                timespec="seconds"
            )
        ),

        "profile": state["profile"],

        "budget": state["budget"],

        "timeline": state["timeline"],

        "risks": state["risks"],

        "resources": state["resources"],

        "assumptions": [
            (
                "The entered total budget is the "
                "current approved planning ceiling."
            ),

            (
                "Blockchain values are denominated "
                "in ETH and do not include fiat "
                "exchange-rate risk."
            ),

            (
                "Local permits, tax, and insurance "
                "requirements must be confirmed separately."
            ),
        ],
    }

    return {
        "final_plan": final_plan
    }


# =========================================================
# BUILD LANGGRAPH WORKFLOW
# =========================================================

def _build_graph():

    graph = StateGraph(
        PlannerState
    )

    graph.add_node(
        "analyse_event",
        analyse_event,
    )

    graph.add_node(
        "allocate_budget",
        allocate_budget,
    )

    graph.add_node(
        "create_timeline",
        create_timeline,
    )

    graph.add_node(
        "identify_risks",
        identify_risks,
    )

    graph.add_node(
        "recommend_resources",
        recommend_resources,
    )

    graph.add_node(
        "finalise_plan",
        finalise_plan,
    )

    # Graph flow

    graph.add_edge(
        START,
        "analyse_event",
    )

    graph.add_edge(
        "analyse_event",
        "allocate_budget",
    )

    graph.add_edge(
        "allocate_budget",
        "create_timeline",
    )

    graph.add_edge(
        "create_timeline",
        "identify_risks",
    )

    graph.add_edge(
        "identify_risks",
        "recommend_resources",
    )

    graph.add_edge(
        "recommend_resources",
        "finalise_plan",
    )

    graph.add_edge(
        "finalise_plan",
        END,
    )

    return graph.compile()


# Compile graph once when application starts

PLANNER_GRAPH = _build_graph()


# =========================================================
# MAIN AI PLAN GENERATOR
# =========================================================

def generate_event_plan(
    *,
    title: str,
    category: str,
    description: str,
    venue: str,
    event_date: date,
    capacity: int,
    total_budget_bdt: float,
) -> dict:

    # Input cleaning
    clean_title = (
        title.strip()
        if title
        else "Untitled Event"
    )

    clean_category = (
        category.strip().lower()
        if category
        else "other"
    )

    clean_description = (
        description.strip()
        if description
        else ""
    )

    clean_venue = (
        venue.strip()
        if venue
        else ""
    )

    clean_capacity = max(
        int(capacity or 1),
        1,
    )

    clean_budget = max(
        float(total_budget_bdt or 0),
        0,
    )

    result = PLANNER_GRAPH.invoke(
        {
            "title": clean_title,
            "category": clean_category,
            "description": clean_description,
            "venue": clean_venue,
            "event_date": event_date.isoformat(),
            "capacity": clean_capacity,
            "total_budget_bdt": clean_budget,
        }
    )

    return result["final_plan"]


# =========================================================
# NEW: AI PLAN VALIDATION
# =========================================================

REQUIRED_PLAN_SECTIONS = {
    "summary",
    "generated_at",
    "profile",
    "budget",
    "timeline",
    "risks",
    "resources",
    "assumptions",
}


def is_complete_plan(
    plan: object,
) -> bool:
    """
    Check whether an AI plan exists and contains
    all required sections.
    """

    if not isinstance(plan, dict):
        return False

    # Main sections
    if not REQUIRED_PLAN_SECTIONS.issubset(
        plan.keys()
    ):
        return False

    profile = plan.get(
        "profile"
    )

    budget = plan.get(
        "budget"
    )

    if not isinstance(
        profile,
        dict,
    ):
        return False

    if not isinstance(
        budget,
        dict,
    ):
        return False

    required_profile_fields = {
        "event_size",
        "risk_level",
        "lead_days",
        "estimated_staff",
        "recommended_check_in_points",
    }

    required_budget_fields = {
        "total_bdt",
        "per_attendee_bdt",
        "items",
    }

    if not required_profile_fields.issubset(
        profile.keys()
    ):
        return False

    if not required_budget_fields.issubset(
        budget.keys()
    ):
        return False

    if not isinstance(
        budget.get("items"),
        list,
    ):
        return False

    if not isinstance(
        plan.get("timeline"),
        list,
    ):
        return False

    if not isinstance(
        plan.get("risks"),
        list,
    ):
        return False

    if not isinstance(
        plan.get("resources"),
        list,
    ):
        return False

    if not isinstance(
        plan.get("assumptions"),
        list,
    ):
        return False

    return True


# =========================================================
# NEW: GENERATE / RECOVER EVENT AI PLAN
# =========================================================

def ensure_event_plan(
    event_record,
    force: bool = False,
) -> tuple[dict, bool]:
    """
    Ensures that an Event has a complete AI plan.

    If the plan is missing, empty, broken, or force=True,
    a new AI plan is generated automatically.

    Returns:
        plan:
            Existing or generated AI plan.

        generated:
            True if a new plan was generated.
            False if existing plan was already valid.
    """

    existing_plan = None

    # Safely read existing AI plan
    try:
        existing_plan = (
            event_record.ai_plan
        )

    except (
        TypeError,
        ValueError,
        json.JSONDecodeError,
    ):
        existing_plan = None

    # If plan already valid, use it
    if (
        not force
        and is_complete_plan(
            existing_plan
        )
    ):
        return (
            existing_plan,
            False,
        )

    # Generate new plan
    new_plan = generate_event_plan(
        title=event_record.title,
        category=event_record.category,
        description=(
            event_record.description
            or ""
        ),
        venue=(
            event_record.venue
            or ""
        ),
        event_date=event_record.event_date,
        capacity=int(
            event_record.attendee_capacity
            or 1
        ),
        total_budget_bdt=float(
            event_record.budget_bdt
            or 0
        ),
    )

    # Save plan into database column
    event_record.ai_plan_json = (
        json.dumps(
            new_plan,
            ensure_ascii=False,
        )
    )

    return (
        new_plan,
        True,
    )