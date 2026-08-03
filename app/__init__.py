from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import click
from flask import Flask, render_template

from .config import Config
from .extensions import csrf, db, login_manager
from .models import Event, User
from .services.ai_planner import generate_event_plan


@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))


def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "warning"

    from .auth.routes import auth_bp
    from .blockchain.routes import blockchain_bp
    from .events.routes import events_bp
    from .main.routes import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(events_bp)
    app.register_blueprint(blockchain_bp)

    register_cli(app)
    register_error_handlers(app)
    return app


def register_cli(app: Flask) -> None:
    @app.cli.command("init-db")
    @click.option("--drop", is_flag=True, help="Drop all existing tables first.")
    def init_db(drop: bool):
        """Create the local SQLite tables."""
        if drop:
            db.drop_all()
        db.create_all()
        click.echo("Database initialised.")

    @app.cli.command("seed-demo")
    def seed_demo():
        """Create demonstration users and one event."""
        db.create_all()
        users = [
            ("System Admin", "admin@example.com", "admin", "Admin123!"),
            ("Demo Organizer", "organizer@example.com", "organizer", "Organizer123!"),
            ("Demo Attendee", "attendee@example.com", "attendee", "Attendee123!"),
            ("Demo Vendor", "vendor@example.com", "vendor", "Vendor123!"),
            ("Demo Sponsor", "sponsor@example.com", "sponsor", "Sponsor123!"),
        ]
        created = {}
        for name, email, role, password in users:
            user = User.query.filter_by(email=email).first()
            if not user:
                user = User(name=name, email=email, role=role)
                user.set_password(password)
                db.session.add(user)
            created[email] = user
        db.session.flush()

        if Event.query.count() == 0:
            organizer = created["organizer@example.com"]
            event_day = date.today() + timedelta(days=45)
            plan = generate_event_plan(
                title="EventChain University Tech Fest",
                category="university",
                description=(
                    "A university technology festival with project showcases, "
                    "guest sessions, workshops, and secure NFT ticket entry."
                ),
                venue="University auditorium and innovation lab",
                event_date=event_day,
                capacity=350,
                total_budget_bdt=600000,
            )
            db.session.add(
                Event(
                    organizer_id=organizer.id,
                    title="EventChain University Tech Fest",
                    category="university",
                    description=(
                        "A university technology festival with project showcases, "
                        "guest sessions, workshops, and secure NFT ticket entry."
                    ),
                    venue="University auditorium and innovation lab",
                    event_date=event_day,
                    attendee_capacity=350,
                    ticket_price_eth=0.01,
                    budget_bdt=600000,
                    ai_plan_json=json.dumps(plan),
                )
            )
        db.session.commit()
        click.echo("Demo data created.")


def register_error_handlers(app: Flask) -> None:
    @app.errorhandler(403)
    def forbidden(_error):
        return render_template(
            "errors/error.html",
            code=403,
            title="Access denied",
            message="You do not have permission to open this page.",
        ), 403

    @app.errorhandler(404)
    def not_found(_error):
        return render_template(
            "errors/error.html",
            code=404,
            title="Page not found",
            message="The requested page does not exist.",
        ), 404

    @app.errorhandler(500)
    def server_error(_error):
        db.session.rollback()
        return render_template(
            "errors/error.html",
            code=500,
            title="Server error",
            message="An unexpected error occurred.",
        ), 500
