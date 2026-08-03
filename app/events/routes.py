from __future__ import annotations

import io
import json

import qrcode
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    url_for,
)
from flask_login import current_user, login_required

from ..decorators import role_required
from ..extensions import db
from ..forms import EventForm, VerifyTicketForm
from ..models import Event, Ticket
from ..services.ai_planner import generate_event_plan
from ..services.blockchain_service import BlockchainError, BlockchainService


events_bp = Blueprint("events", __name__)


def _organizer_owns(event: Event) -> bool:
    return current_user.role == "admin" or event.organizer_id == current_user.id


@events_bp.get("/events")
def event_list():
    events = Event.query.order_by(Event.event_date.asc()).all()
    return render_template("events/list.html", events=events)


@events_bp.route("/events/create", methods=["GET", "POST"])
@login_required
@role_required("organizer", "admin")
def create_event():
    form = EventForm()
    if form.validate_on_submit():
        plan = generate_event_plan(
            title=form.title.data,
            category=form.category.data,
            description=form.description.data,
            venue=form.venue.data,
            event_date=form.event_date.data,
            capacity=form.attendee_capacity.data,
            total_budget_bdt=float(form.budget_bdt.data),
        )
        event = Event(
            organizer_id=current_user.id,
            title=form.title.data.strip(),
            category=form.category.data,
            description=form.description.data.strip(),
            venue=form.venue.data.strip(),
            event_date=form.event_date.data,
            attendee_capacity=form.attendee_capacity.data,
            ticket_price_eth=form.ticket_price_eth.data,
            budget_bdt=form.budget_bdt.data,
            ai_plan_json=json.dumps(plan),
        )
        db.session.add(event)
        db.session.commit()
        flash("Event created and AI plan generated.", "success")
        return redirect(url_for("events.manage_event", event_id=event.id))

    return render_template("events/form.html", form=form, heading="Create event")


@events_bp.route("/events/<int:event_id>/edit", methods=["GET", "POST"])
@login_required
def edit_event(event_id: int):
    event = db.get_or_404(Event, event_id)
    if not _organizer_owns(event):
        abort(403)
    if event.chain_status == "published":
        flash("Published blockchain event values cannot be edited in this MVP.", "warning")
        return redirect(url_for("events.manage_event", event_id=event.id))

    form = EventForm(obj=event)
    if form.validate_on_submit():
        plan = generate_event_plan(
            title=form.title.data,
            category=form.category.data,
            description=form.description.data,
            venue=form.venue.data,
            event_date=form.event_date.data,
            capacity=form.attendee_capacity.data,
            total_budget_bdt=float(form.budget_bdt.data),
        )
        form.populate_obj(event)
        event.ai_plan_json = json.dumps(plan)
        db.session.commit()
        flash("Event and AI plan updated.", "success")
        return redirect(url_for("events.manage_event", event_id=event.id))

    return render_template(
        "events/form.html", form=form, heading=f"Edit {event.title}", event=event
    )


@events_bp.get("/events/<int:event_id>")
def event_detail(event_id: int):
    event = db.get_or_404(Event, event_id)
    return render_template("events/detail.html", event=event)


@events_bp.get("/events/<int:event_id>/manage")
@login_required
def manage_event(event_id: int):
    event = db.get_or_404(Event, event_id)
    if not _organizer_owns(event):
        abort(403)
    return render_template("events/manage.html", event=event)


@events_bp.get("/events/<int:event_id>/ai-plan")
def ai_plan(event_id: int):
    event = db.get_or_404(Event, event_id)
    return render_template("events/ai_plan.html", event=event, plan=event.ai_plan)


@events_bp.route("/tickets/verify", methods=["GET", "POST"])
def verify_ticket():
    form = VerifyTicketForm()
    result = None
    token_from_query = request.args.get("token_id", type=int)
    if token_from_query and request.method == "GET":
        form.token_id.data = token_from_query

    if form.validate_on_submit() or token_from_query:
        token_id = form.token_id.data or token_from_query
        try:
            service = BlockchainService()
            chain_result = service.verify_ticket(token_id)
            local_ticket = Ticket.query.filter_by(token_id=token_id).first()
            chain_event = (
                db.session.get(Event, chain_result["event_id"])
                if chain_result["event_id"]
                else None
            )
            result = {
                **chain_result,
                "token_id": token_id,
                "ticket": local_ticket,
                "event": chain_event,
            }
        except BlockchainError as exc:
            flash(str(exc), "danger")

    return render_template("tickets/verify.html", form=form, result=result)


@events_bp.get("/tickets")
@login_required
def my_tickets():
    tickets = (
        Ticket.query.filter_by(user_id=current_user.id)
        .order_by(Ticket.purchased_at.desc())
        .all()
    )
    return render_template("tickets/list.html", tickets=tickets)


@events_bp.get("/tickets/<int:ticket_id>/qr.png")
@login_required
def ticket_qr(ticket_id: int):
    ticket = db.get_or_404(Ticket, ticket_id)
    if current_user.role != "admin" and ticket.user_id != current_user.id:
        abort(403)

    verification_url = url_for(
        "events.verify_ticket", token_id=ticket.token_id, _external=True
    )
    image = qrcode.make(verification_url)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return send_file(buffer, mimetype="image/png", max_age=0)
