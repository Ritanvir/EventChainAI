from __future__ import annotations

import json

from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import current_user, login_required
from sqlalchemy import func

from ..decorators import role_required
from ..extensions import db
from ..models import (
    BlockchainTransaction,
    Event,
    Sponsorship,
    Ticket,
    User,
    VendorEscrow,
)
from ..services.ai_planner import generate_event_plan


# =========================================================
# ADMIN BLUEPRINT
# =========================================================

admin_bp = Blueprint(
    "admin",
    __name__,
    url_prefix="/admin",
)


# =========================================================
# ALLOWED VALUES
# =========================================================

ALLOWED_USER_ROLES = {
    "admin",
    "organizer",
    "attendee",
    "vendor",
    "sponsor",
}


ALLOWED_EVENT_STATUS = {
    "draft",
    "active",
    "cancelled",
    "completed",
}


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@admin_bp.get("/")
@login_required
@role_required("admin")
def dashboard():

    # -----------------------------------------------------
    # BASIC COUNTS
    # -----------------------------------------------------

    total_users = User.query.count()

    total_events = Event.query.count()

    total_tickets = Ticket.query.count()

    checked_in_tickets = (
        Ticket.query
        .filter_by(status="used")
        .count()
    )

    published_events = (
        Event.query
        .filter_by(chain_status="published")
        .count()
    )

    total_transactions = (
        BlockchainTransaction.query.count()
    )


    # -----------------------------------------------------
    # FINANCIAL STATISTICS
    # -----------------------------------------------------

    total_sponsorship = (
        db.session.query(
            func.coalesce(
                func.sum(
                    Sponsorship.amount_eth
                ),
                0,
            )
        )
        .scalar()
    )


    total_escrow = (
        db.session.query(
            func.coalesce(
                func.sum(
                    VendorEscrow.amount_eth
                ),
                0,
            )
        )
        .scalar()
    )


    locked_escrow = (
        db.session.query(
            func.coalesce(
                func.sum(
                    VendorEscrow.amount_eth
                ),
                0,
            )
        )
        .filter(
            VendorEscrow.status == "locked"
        )
        .scalar()
    )


    released_escrow = (
        db.session.query(
            func.coalesce(
                func.sum(
                    VendorEscrow.amount_eth
                ),
                0,
            )
        )
        .filter(
            VendorEscrow.status == "released"
        )
        .scalar()
    )


    refunded_escrow = (
        db.session.query(
            func.coalesce(
                func.sum(
                    VendorEscrow.amount_eth
                ),
                0,
            )
        )
        .filter(
            VendorEscrow.status == "refunded"
        )
        .scalar()
    )


    # -----------------------------------------------------
    # USERS
    # -----------------------------------------------------

    users = (
        User.query
        .order_by(
            User.created_at.desc()
        )
        .all()
    )


    # -----------------------------------------------------
    # EVENTS
    # -----------------------------------------------------

    events = (
        Event.query
        .order_by(
            Event.created_at.desc()
        )
        .all()
    )


    # -----------------------------------------------------
    # TICKETS
    # -----------------------------------------------------

    tickets = (
        Ticket.query
        .order_by(
            Ticket.purchased_at.desc()
        )
        .limit(50)
        .all()
    )


    # -----------------------------------------------------
    # SPONSORSHIPS
    # -----------------------------------------------------

    sponsorships = (
        Sponsorship.query
        .order_by(
            Sponsorship.created_at.desc()
        )
        .limit(50)
        .all()
    )


    # -----------------------------------------------------
    # ESCROWS
    # -----------------------------------------------------

    escrows = (
        VendorEscrow.query
        .order_by(
            VendorEscrow.created_at.desc()
        )
        .limit(50)
        .all()
    )


    # -----------------------------------------------------
    # BLOCKCHAIN TRANSACTIONS
    # -----------------------------------------------------

    transactions = (
        BlockchainTransaction.query
        .order_by(
            BlockchainTransaction.created_at.desc()
        )
        .limit(50)
        .all()
    )


    stats = {
        "users": total_users,
        "events": total_events,
        "tickets": total_tickets,
        "checked_in": checked_in_tickets,
        "published_events": published_events,
        "transactions": total_transactions,

        "sponsorship": total_sponsorship,
        "escrow": total_escrow,
        "locked_escrow": locked_escrow,
        "released_escrow": released_escrow,
        "refunded_escrow": refunded_escrow,
    }


    return render_template(
        "admin/dashboard.html",

        stats=stats,

        users=users,

        events=events,

        tickets=tickets,

        sponsorships=sponsorships,

        escrows=escrows,

        transactions=transactions,

        allowed_roles=sorted(
            ALLOWED_USER_ROLES
        ),

        allowed_event_status=sorted(
            ALLOWED_EVENT_STATUS
        ),
    )


# =========================================================
# CHANGE USER ROLE
# =========================================================

@admin_bp.post(
    "/users/<int:user_id>/role"
)
@login_required
@role_required("admin")
def change_user_role(
    user_id: int,
):

    user = db.get_or_404(
        User,
        user_id,
    )

    new_role = (
        request.form.get(
            "role",
            "",
        )
        .strip()
        .lower()
    )


    # -----------------------------------------------------
    # VALIDATE ROLE
    # -----------------------------------------------------

    if new_role not in ALLOWED_USER_ROLES:

        flash(
            "Invalid user role.",
            "danger",
        )

        return redirect(
            url_for(
                "admin.dashboard"
            )
        )


    # -----------------------------------------------------
    # PREVENT ADMIN FROM REMOVING OWN ADMIN ROLE
    # -----------------------------------------------------

    if (
        user.id == current_user.id
        and new_role != "admin"
    ):

        flash(
            (
                "You cannot remove your own "
                "administrator role."
            ),
            "danger",
        )

        return redirect(
            url_for(
                "admin.dashboard"
            )
        )


    old_role = user.role

    user.role = new_role

    db.session.commit()


    flash(
        (
            f"{user.name}'s role changed "
            f"from {old_role} to {new_role}."
        ),
        "success",
    )


    return redirect(
        url_for(
            "admin.dashboard"
        )
    )


# =========================================================
# CHANGE EVENT STATUS
# =========================================================

@admin_bp.post(
    "/events/<int:event_id>/status"
)
@login_required
@role_required("admin")
def change_event_status(
    event_id: int,
):

    event = db.get_or_404(
        Event,
        event_id,
    )


    new_status = (
        request.form.get(
            "status",
            "",
        )
        .strip()
        .lower()
    )


    if (
        new_status
        not in ALLOWED_EVENT_STATUS
    ):

        flash(
            "Invalid event status.",
            "danger",
        )

        return redirect(
            url_for(
                "admin.dashboard"
            )
        )


    old_status = event.status

    event.status = new_status

    db.session.commit()


    flash(
        (
            f"Event '{event.title}' status "
            f"changed from {old_status} "
            f"to {new_status}."
        ),
        "success",
    )


    return redirect(
        url_for(
            "admin.dashboard"
        )
    )


# =========================================================
# REGENERATE EVENT AI PLAN
# =========================================================

@admin_bp.post(
    "/events/<int:event_id>/regenerate-ai"
)
@login_required
@role_required("admin")
def regenerate_ai_plan(
    event_id: int,
):

    event = db.get_or_404(
        Event,
        event_id,
    )


    try:

        plan = generate_event_plan(
            title=event.title,

            category=event.category,

            description=(
                event.description
                or ""
            ),

            venue=(
                event.venue
                or ""
            ),

            event_date=event.event_date,

            capacity=int(
                event.attendee_capacity
            ),

            total_budget_bdt=float(
                event.budget_bdt
            ),
        )


        event.ai_plan_json = json.dumps(
            plan,
            ensure_ascii=False,
        )


        db.session.commit()


        flash(
            (
                f"AI plan regenerated "
                f"for '{event.title}'."
            ),
            "success",
        )


    except Exception as exc:

        db.session.rollback()

        flash(
            (
                "AI plan regeneration failed: "
                f"{exc}"
            ),
            "danger",
        )


    return redirect(
        url_for(
            "admin.dashboard"
        )
    )