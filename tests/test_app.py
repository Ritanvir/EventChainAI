from datetime import date, timedelta

from app.extensions import db
from app.models import Event, User


def create_user(*, name="Test User", email="user@example.com", role="organizer"):
    user = User(name=name, email=email, role=role)
    user.set_password("Password123!")
    db.session.add(user)
    db.session.commit()
    return user


def login(client, email="user@example.com", password="Password123!"):
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def test_home_page_loads(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"EventChain AI" in response.data


def test_registration_and_login(client, app):
    response = client.post(
        "/auth/register",
        data={
            "name": "New Organizer",
            "email": "new@example.com",
            "role": "organizer",
            "password": "Secure123!",
            "confirm_password": "Secure123!",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Dashboard" in response.data

    with app.app_context():
        assert User.query.filter_by(email="new@example.com").first() is not None


def test_organizer_can_create_event(client, app):
    with app.app_context():
        create_user()

    login(client)
    response = client.post(
        "/events/create",
        data={
            "title": "Software Engineering Expo",
            "category": "university",
            "description": "Student software project demonstration and judging.",
            "venue": "University auditorium",
            "event_date": (date.today() + timedelta(days=40)).isoformat(),
            "attendee_capacity": 250,
            "ticket_price_eth": "0.01",
            "budget_bdt": "400000",
        },
        follow_redirects=True,
    )

    assert response.status_code == 200
    assert b"Software Engineering Expo" in response.data
    assert b"AI Event Plan" in response.data

    with app.app_context():
        event = Event.query.filter_by(title="Software Engineering Expo").first()
        assert event is not None
        assert event.ai_plan["budget"]["total_bdt"] == 400000.0


def test_attendee_cannot_create_event(client, app):
    with app.app_context():
        create_user(email="attendee@example.com", role="attendee")

    login(client, email="attendee@example.com")
    response = client.get("/events/create")
    assert response.status_code == 403
