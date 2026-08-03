from flask import Blueprint, render_template
from flask_login import current_user, login_required
from sqlalchemy import func

from ..models import (
    BlockchainTransaction,
    Event,
    Sponsorship,
    Ticket,
    User,
    VendorEscrow,
)


main_bp = Blueprint("main", __name__)


@main_bp.get("/")
def home():
    events = (
        Event.query.filter(Event.event_date >= func.current_date())
        .order_by(Event.event_date.asc())
        .limit(9)
        .all()
    )
    return render_template("home.html", events=events)


@main_bp.get("/dashboard")
@login_required
def dashboard():
    context = {}

    if current_user.role in {"organizer", "admin"}:
        context["organized_events"] = (
            Event.query.filter_by(organizer_id=current_user.id)
            .order_by(Event.created_at.desc())
            .all()
        )

    context["my_tickets"] = (
        Ticket.query.filter_by(user_id=current_user.id)
        .order_by(Ticket.purchased_at.desc())
        .all()
    )

    if current_user.wallet_address:
        context["vendor_escrows"] = (
            VendorEscrow.query.filter(
                func.lower(VendorEscrow.vendor_wallet)
                == current_user.wallet_address.lower()
            )
            .order_by(VendorEscrow.created_at.desc())
            .all()
        )
    else:
        context["vendor_escrows"] = []

    context["my_sponsorships"] = (
        Sponsorship.query.filter_by(sponsor_user_id=current_user.id)
        .order_by(Sponsorship.created_at.desc())
        .all()
    )

    if current_user.role == "admin":
        context["admin_stats"] = {
            "users": User.query.count(),
            "events": Event.query.count(),
            "tickets": Ticket.query.count(),
            "transactions": BlockchainTransaction.query.count(),
        }
        context["recent_transactions"] = (
            BlockchainTransaction.query.order_by(
                BlockchainTransaction.created_at.desc()
            )
            .limit(15)
            .all()
        )

    return render_template("dashboard.html", **context)
