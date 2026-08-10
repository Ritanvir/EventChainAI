from __future__ import annotations

import json
from datetime import date, timedelta
from pathlib import Path

import click
from flask import Flask, render_template

from .config import Config
from .extensions import csrf, db, login_manager
from .models import Event, User
from .services.ai_plan_guard import register_ai_plan_guard
from .services.ai_planner import (
    ensure_event_plan,
    generate_event_plan,
)


# =========================================================
# FLASK LOGIN USER LOADER
# =========================================================

@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(
        User,
        int(user_id),
    )


# =========================================================
# APPLICATION FACTORY
# =========================================================

def create_app(
    test_config: dict | None = None,
) -> Flask:

    app = Flask(
        __name__,
        instance_relative_config=True,
    )

    # -----------------------------------------------------
    # LOAD MAIN CONFIGURATION
    # -----------------------------------------------------

    app.config.from_object(Config)

    # Override config while testing
    if test_config:
        app.config.update(
            test_config
        )

    # -----------------------------------------------------
    # ENSURE INSTANCE FOLDER EXISTS
    # -----------------------------------------------------

    Path(
        app.instance_path
    ).mkdir(
        parents=True,
        exist_ok=True,
    )


    # =====================================================
    # INITIALISE EXTENSIONS
    # =====================================================

    db.init_app(app)

    # -----------------------------------------------------
    # AUTOMATIC AI PLAN GENERATION / RECOVERY
    # -----------------------------------------------------

    register_ai_plan_guard()

    # -----------------------------------------------------
    # LOGIN MANAGER
    # -----------------------------------------------------

    login_manager.init_app(app)

    login_manager.login_view = (
        "auth.login"
    )

    login_manager.login_message_category = (
        "warning"
    )

    # -----------------------------------------------------
    # CSRF PROTECTION
    # -----------------------------------------------------

    csrf.init_app(app)


    # =====================================================
    # IMPORT BLUEPRINTS
    # =====================================================

    # Admin
    from .admin.routes import admin_bp

    # Authentication
    from .auth.routes import auth_bp

    # Blockchain
    from .blockchain.routes import blockchain_bp

    # Events
    from .events.routes import events_bp

    # Main website
    from .main.routes import main_bp


    # =====================================================
    # REGISTER BLUEPRINTS
    # =====================================================

    app.register_blueprint(
        main_bp
    )

    app.register_blueprint(
        auth_bp
    )

    app.register_blueprint(
        events_bp
    )

    app.register_blueprint(
        blockchain_bp
    )

    # -----------------------------------------------------
    # ADMIN CONTROL PANEL
    # -----------------------------------------------------

    app.register_blueprint(
        admin_bp
    )


    # =====================================================
    # REGISTER CLI COMMANDS
    # =====================================================

    register_cli(app)


    # =====================================================
    # REGISTER ERROR HANDLERS
    # =====================================================

    register_error_handlers(app)


    return app


# =========================================================
# CLI COMMANDS
# =========================================================

def register_cli(
    app: Flask,
) -> None:


    # =====================================================
    # DATABASE INITIALISATION
    # =====================================================

    @app.cli.command(
        "init-db"
    )
    @click.option(
        "--drop",
        is_flag=True,
        help="Drop all existing tables first.",
    )
    def init_db(
        drop: bool,
    ):
        """
        Create the local SQLite database tables.
        """

        if drop:
            db.drop_all()

        db.create_all()

        click.echo(
            "Database initialised."
        )


    # =====================================================
    # AI PLAN RECOVERY COMMAND
    # =====================================================

    @app.cli.command(
        "repair-ai-plans"
    )
    @click.option(
        "--force",
        is_flag=True,
        help=(
            "Regenerate every event plan, "
            "including already valid plans."
        ),
    )
    def repair_ai_plans(
        force: bool,
    ):
        """
        Generate missing AI plans and repair
        incomplete AI plans for all Event records.
        """

        db.create_all()

        events = (
            Event.query
            .order_by(
                Event.id.asc()
            )
            .all()
        )

        generated = 0
        unchanged = 0


        for event_record in events:

            plan, changed = (
                ensure_event_plan(
                    event_record,
                    force=force,
                )
            )

            if changed:

                generated += 1

                click.echo(
                    (
                        f"Generated: "
                        f"#{event_record.id} "
                        f"{event_record.title}"
                    )
                )

            else:

                unchanged += 1

                click.echo(
                    (
                        f"Already valid: "
                        f"#{event_record.id} "
                        f"{event_record.title}"
                    )
                )


        db.session.commit()


        click.echo(
            (
                "AI-plan recovery completed. "
                f"Generated: {generated}; "
                f"unchanged: {unchanged}."
            )
        )


    # =====================================================
    # DEMO DATA
    # =====================================================

    @app.cli.command(
        "seed-demo"
    )
    def seed_demo():
        """
        Create demo users and one sample event.
        """

        db.create_all()


        # -------------------------------------------------
        # DEMO USERS
        # -------------------------------------------------

        users = [

            (
                "System Admin",
                "admin@example.com",
                "admin",
                "Admin123!",
            ),

            (
                "Demo Organizer",
                "organizer@example.com",
                "organizer",
                "Organizer123!",
            ),

            (
                "Demo Attendee",
                "attendee@example.com",
                "attendee",
                "Attendee123!",
            ),

            (
                "Demo Vendor",
                "vendor@example.com",
                "vendor",
                "Vendor123!",
            ),

            (
                "Demo Sponsor",
                "sponsor@example.com",
                "sponsor",
                "Sponsor123!",
            ),

        ]


        created = {}


        # -------------------------------------------------
        # CREATE USERS IF THEY DO NOT EXIST
        # -------------------------------------------------

        for (
            name,
            email,
            role,
            password,
        ) in users:

            user = (
                User.query
                .filter_by(
                    email=email
                )
                .first()
            )


            if not user:

                user = User(
                    name=name,
                    email=email,
                    role=role,
                )

                user.set_password(
                    password
                )

                db.session.add(
                    user
                )


            created[email] = user


        # -------------------------------------------------
        # ASSIGN USER IDs
        # -------------------------------------------------

        db.session.flush()


        # =================================================
        # CREATE DEMO EVENT ONLY WHEN NO EVENT EXISTS
        # =================================================

        if Event.query.count() == 0:

            organizer = created[
                "organizer@example.com"
            ]


            event_day = (
                date.today()
                + timedelta(days=45)
            )


            # ---------------------------------------------
            # GENERATE DEMO AI PLAN
            # ---------------------------------------------

            plan = generate_event_plan(

                title=(
                    "EventChain University Tech Fest"
                ),

                category=(
                    "university"
                ),

                description=(
                    "A university technology festival "
                    "with project showcases, guest "
                    "sessions, workshops, and secure "
                    "NFT ticket entry."
                ),

                venue=(
                    "University auditorium "
                    "and innovation lab"
                ),

                event_date=event_day,

                capacity=350,

                total_budget_bdt=600000,

            )


            # ---------------------------------------------
            # CREATE DEMO EVENT
            # ---------------------------------------------

            event = Event(

                organizer_id=(
                    organizer.id
                ),

                title=(
                    "EventChain University Tech Fest"
                ),

                category=(
                    "university"
                ),

                description=(
                    "A university technology festival "
                    "with project showcases, guest "
                    "sessions, workshops, and secure "
                    "NFT ticket entry."
                ),

                venue=(
                    "University auditorium "
                    "and innovation lab"
                ),

                event_date=(
                    event_day
                ),

                attendee_capacity=350,

                ticket_price_eth=0.01,

                budget_bdt=600000,

                ai_plan_json=json.dumps(
                    plan,
                    ensure_ascii=False,
                ),

            )


            db.session.add(
                event
            )


        db.session.commit()


        click.echo(
            "Demo data created."
        )


# =========================================================
# ERROR HANDLERS
# =========================================================

def register_error_handlers(
    app: Flask,
) -> None:


    # =====================================================
    # 403 - ACCESS DENIED
    # =====================================================

    @app.errorhandler(
        403
    )
    def forbidden(
        _error,
    ):

        return (
            render_template(
                "errors/error.html",

                code=403,

                title="Access denied",

                message=(
                    "You do not have permission "
                    "to open this page."
                ),

            ),
            403,
        )


    # =====================================================
    # 404 - PAGE NOT FOUND
    # =====================================================

    @app.errorhandler(
        404
    )
    def not_found(
        _error,
    ):

        return (
            render_template(
                "errors/error.html",

                code=404,

                title="Page not found",

                message=(
                    "The requested page "
                    "does not exist."
                ),

            ),
            404,
        )


    # =====================================================
    # 500 - SERVER ERROR
    # =====================================================

    @app.errorhandler(
        500
    )
    def server_error(
        _error,
    ):

        # Rollback failed database transaction
        db.session.rollback()


        return (
            render_template(
                "errors/error.html",

                code=500,

                title="Server error",

                message=(
                    "An unexpected error occurred."
                ),

            ),
            500,
        )