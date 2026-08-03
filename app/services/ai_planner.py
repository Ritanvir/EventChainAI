from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import TypedDict

from langgraph.graph import END, START, StateGraph


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


def _money(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def analyse_event(state: PlannerState) -> dict:
    capacity = int(state["capacity"])
    event_day = datetime.strptime(state["event_date"], "%Y-%m-%d").date()
    lead_days = max((event_day - date.today()).days, 0)

    size = "small" if capacity <= 100 else "medium" if capacity <= 500 else "large"
    risk_level = (
        "high"
        if capacity > 1000 or state["category"] == "concert"
        else ("medium" if capacity > 250 else "standard")
    )

    return {
        "profile": {
            "event_size": size,
            "risk_level": risk_level,
            "lead_days": lead_days,
            "estimated_staff": max(4, round(capacity / 50)),
            "recommended_check_in_points": max(1, round(capacity / 250)),
        }
    }


def allocate_budget(state: PlannerState) -> dict:
    total = Decimal(str(state["total_budget_bdt"]))
    weights = CATEGORY_WEIGHTS.get(state["category"], CATEGORY_WEIGHTS["other"])
    items = [
        {
            "item": name,
            "percentage": int(weight * 100),
            "amount_bdt": _money(total * Decimal(str(weight))),
        }
        for name, weight in weights.items()
    ]

    per_attendee = total / Decimal(max(state["capacity"], 1))
    return {
        "budget": {
            "total_bdt": _money(total),
            "per_attendee_bdt": _money(per_attendee),
            "items": items,
        }
    }


def create_timeline(state: PlannerState) -> dict:
    event_day = datetime.strptime(state["event_date"], "%Y-%m-%d").date()
    lead_days = state["profile"]["lead_days"]

    phases = [
        (0.85, "Concept and approval", "Confirm objectives, audience, scope, and ownership."),
        (0.70, "Venue and vendor sourcing", "Obtain quotations and shortlist compliant vendors."),
        (0.55, "Programme and ticket launch", "Finalise programme and publish blockchain ticket sales."),
        (0.35, "Marketing and sponsor activation", "Run promotion and track sponsor commitments."),
        (0.18, "Operational confirmation", "Confirm staff, security, equipment, catering, and transport."),
        (0.07, "Final readiness review", "Complete risk review, rehearsals, and attendee communication."),
        (0.00, "Event delivery", "Operate check-in, monitor budget, and record incidents."),
        (-0.05, "Close-out", "Release approved escrows, reconcile funds, and review performance."),
    ]

    timeline = []
    for fraction, phase, actions in phases:
        if fraction >= 0:
            offset = max(0, round(lead_days * fraction))
            deadline = event_day - timedelta(days=offset)
        else:
            deadline = event_day + timedelta(
                days=max(1, round(lead_days * abs(fraction)))
            )
        timeline.append(
            {"phase": phase, "deadline": deadline.isoformat(), "actions": actions}
        )

    return {"timeline": timeline}


def identify_risks(state: PlannerState) -> dict:
    risks = [
        {
            "risk": "Budget overrun",
            "probability": "Medium",
            "impact": "High",
            "mitigation": "Keep contingency ring-fenced and require approval before scope changes.",
        },
        {
            "risk": "Vendor delay or non-performance",
            "probability": "Medium",
            "impact": "High",
            "mitigation": "Use milestone confirmations and blockchain escrow before final release.",
        },
        {
            "risk": "Ticket duplication or unauthorised entry",
            "probability": "Low",
            "impact": "High",
            "mitigation": "Verify NFT ownership and mark each token checked-in only once.",
        },
        {
            "risk": "Low attendance",
            "probability": "Medium",
            "impact": "Medium",
            "mitigation": "Track weekly registrations and trigger targeted promotion early.",
        },
    ]

    if state["profile"]["risk_level"] == "high":
        risks.append(
            {
                "risk": "Crowd safety incident",
                "probability": "Medium",
                "impact": "Critical",
                "mitigation": "Prepare crowd-flow, medical, emergency, and evacuation plans with authorities.",
            }
        )

    if state["profile"]["lead_days"] < 21:
        risks.append(
            {
                "risk": "Insufficient preparation time",
                "probability": "High",
                "impact": "High",
                "mitigation": "Freeze non-essential scope and run daily owner-based action tracking.",
            }
        )

    return {"risks": risks}


def recommend_resources(state: PlannerState) -> dict:
    capacity = state["capacity"]
    resources = [
        f"Assign approximately {state['profile']['estimated_staff']} operational staff or volunteers.",
        f"Prepare at least {state['profile']['recommended_check_in_points']} digital check-in point(s).",
        "Keep organizer, finance, logistics, safety, and communications responsibilities separate.",
        "Collect at least two comparable vendor quotations for major budget items.",
        "Confirm an incident-response contact list before ticket sales close.",
    ]
    if capacity > 500:
        resources.append(
            "Use queue barriers, zoned entry, and a dedicated crowd-control supervisor."
        )
    return {"resources": resources}


def finalise_plan(state: PlannerState) -> dict:
    summary = (
        f"The recommended plan treats '{state['title']}' as a "
        f"{state['profile']['event_size']} {state['category']} event with "
        f"{state['profile']['risk_level']} operational risk."
    )
    return {
        "final_plan": {
            "summary": summary,
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "profile": state["profile"],
            "budget": state["budget"],
            "timeline": state["timeline"],
            "risks": state["risks"],
            "resources": state["resources"],
            "assumptions": [
                "The entered total budget is the current approved planning ceiling.",
                "Blockchain values are denominated in ETH and do not include fiat exchange-rate risk.",
                "Local permits, tax, and insurance requirements must be confirmed separately.",
            ],
        }
    }


def _build_graph():
    graph = StateGraph(PlannerState)
    graph.add_node("analyse_event", analyse_event)
    graph.add_node("allocate_budget", allocate_budget)
    graph.add_node("create_timeline", create_timeline)
    graph.add_node("identify_risks", identify_risks)
    graph.add_node("recommend_resources", recommend_resources)
    graph.add_node("finalise_plan", finalise_plan)

    graph.add_edge(START, "analyse_event")
    graph.add_edge("analyse_event", "allocate_budget")
    graph.add_edge("allocate_budget", "create_timeline")
    graph.add_edge("create_timeline", "identify_risks")
    graph.add_edge("identify_risks", "recommend_resources")
    graph.add_edge("recommend_resources", "finalise_plan")
    graph.add_edge("finalise_plan", END)
    return graph.compile()


PLANNER_GRAPH = _build_graph()


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
    result = PLANNER_GRAPH.invoke(
        {
            "title": title,
            "category": category,
            "description": description,
            "venue": venue,
            "event_date": event_date.isoformat(),
            "capacity": capacity,
            "total_budget_bdt": total_budget_bdt,
        }
    )
    return result["final_plan"]
