from datetime import date, timedelta

from app.services.ai_planner import generate_event_plan


def test_ai_plan_has_required_sections():
    plan = generate_event_plan(
        title="Campus Tech Fest",
        category="university",
        description="A technology event",
        venue="Main auditorium",
        event_date=date.today() + timedelta(days=60),
        capacity=300,
        total_budget_bdt=500000,
    )

    assert {"summary", "profile", "budget", "timeline", "risks", "resources"} <= set(plan)
    assert plan["profile"]["event_size"] == "medium"
    assert plan["budget"]["total_bdt"] == 500000.0
    assert round(sum(item["amount_bdt"] for item in plan["budget"]["items"]), 2) == 500000.0
    assert len(plan["timeline"]) >= 7
    assert len(plan["risks"]) >= 4


def test_concert_plan_adds_crowd_risk():
    plan = generate_event_plan(
        title="Music Night",
        category="concert",
        description="A live music programme",
        venue="Open field",
        event_date=date.today() + timedelta(days=30),
        capacity=1500,
        total_budget_bdt=2000000,
    )

    assert plan["profile"]["risk_level"] == "high"
    assert any(risk["risk"] == "Crowd safety incident" for risk in plan["risks"])
