from __future__ import annotations

import io
import json
from datetime import date, timedelta

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
from ..services.ai_planner import (
    ensure_event_plan,
    generate_event_plan,
)
from ..services.blockchain_service import (
    BlockchainError,
    BlockchainService,
)


# =========================================================
# BLUEPRINT
# =========================================================

events_bp = Blueprint(
    "events",
    __name__,
)


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def _organizer_owns(event: Event) -> bool:
    """
    Check whether the currently logged-in user
    owns this event or is an admin.
    """

    return (
        current_user.role == "admin"
        or event.organizer_id == current_user.id
    )


def _recover_ai_plan(event: Event) -> dict:
    """
    Automatically generate and save an AI plan
    when an event has no plan or has an incomplete plan.
    """

    plan, generated = ensure_event_plan(event)

    if generated:
        db.session.commit()

    return plan


# =========================================================
# EVENT LIST
# =========================================================

@events_bp.get("/events")
def event_list():

    events = (
        Event.query
        .order_by(Event.event_date.asc())
        .all()
    )

    return render_template(
        "events/list.html",
        events=events,
    )


# =========================================================
# CREATE EVENT
# =========================================================

@events_bp.route(
    "/events/create",
    methods=["GET", "POST"],
)
@login_required
@role_required("organizer", "admin")
def create_event():

    form = EventForm()

    if form.validate_on_submit():

        # -------------------------------------------------
        # GENERATE AI PLAN AUTOMATICALLY
        # -------------------------------------------------

        plan = generate_event_plan(
            title=form.title.data.strip(),

            category=form.category.data,

            description=(
                form.description.data.strip()
                if form.description.data
                else ""
            ),

            venue=(
                form.venue.data.strip()
                if form.venue.data
                else ""
            ),

            event_date=form.event_date.data,

            capacity=int(
                form.attendee_capacity.data
            ),

            total_budget_bdt=float(
                form.budget_bdt.data
            ),
        )

        # -------------------------------------------------
        # CREATE EVENT
        # -------------------------------------------------

        event = Event(
            organizer_id=current_user.id,

            title=form.title.data.strip(),

            category=form.category.data,

            description=(
                form.description.data.strip()
                if form.description.data
                else ""
            ),

            venue=(
                form.venue.data.strip()
                if form.venue.data
                else ""
            ),

            event_date=form.event_date.data,

            attendee_capacity=(
                form.attendee_capacity.data
            ),

            ticket_price_eth=(
                form.ticket_price_eth.data
            ),

            budget_bdt=(
                form.budget_bdt.data
            ),

            ai_plan_json=json.dumps(
                plan,
                ensure_ascii=False,
            ),
        )

        db.session.add(event)
        db.session.commit()

        flash(
            "Event created and AI plan generated successfully.",
            "success",
        )

        return redirect(
            url_for(
                "events.manage_event",
                event_id=event.id,
            )
        )

    return render_template(
        "events/form.html",
        form=form,
        heading="Create event",
    )


# =========================================================
# EDIT EVENT
# =========================================================

@events_bp.route(
    "/events/<int:event_id>/edit",
    methods=["GET", "POST"],
)
@login_required
def edit_event(event_id: int):

    event = db.get_or_404(
        Event,
        event_id,
    )

    # -------------------------------------------------
    # CHECK OWNERSHIP
    # -------------------------------------------------

    if not _organizer_owns(event):
        abort(403)

    # -------------------------------------------------
    # BLOCKCHAIN-PUBLISHED EVENTS CANNOT BE EDITED
    # -------------------------------------------------

    if event.chain_status == "published":

        flash(
            (
                "Published blockchain event values "
                "cannot be edited in this MVP."
            ),
            "warning",
        )

        return redirect(
            url_for(
                "events.manage_event",
                event_id=event.id,
            )
        )

    form = EventForm(
        obj=event
    )

    if form.validate_on_submit():

        # -------------------------------------------------
        # GENERATE NEW AI PLAN
        # -------------------------------------------------

        plan = generate_event_plan(
            title=form.title.data.strip(),

            category=form.category.data,

            description=(
                form.description.data.strip()
                if form.description.data
                else ""
            ),

            venue=(
                form.venue.data.strip()
                if form.venue.data
                else ""
            ),

            event_date=form.event_date.data,

            capacity=int(
                form.attendee_capacity.data
            ),

            total_budget_bdt=float(
                form.budget_bdt.data
            ),
        )

        # -------------------------------------------------
        # UPDATE EVENT
        # -------------------------------------------------

        form.populate_obj(event)

        event.title = (
            form.title.data.strip()
        )

        event.description = (
            form.description.data.strip()
            if form.description.data
            else ""
        )

        event.venue = (
            form.venue.data.strip()
            if form.venue.data
            else ""
        )

        # -------------------------------------------------
        # UPDATE AI PLAN
        # -------------------------------------------------

        event.ai_plan_json = json.dumps(
            plan,
            ensure_ascii=False,
        )

        db.session.commit()

        flash(
            "Event updated and AI plan regenerated successfully.",
            "success",
        )

        return redirect(
            url_for(
                "events.manage_event",
                event_id=event.id,
            )
        )

    return render_template(
        "events/form.html",
        form=form,
        heading=f"Edit {event.title}",
        event=event,
    )


# =========================================================
# EVENT DETAILS
# =========================================================

@events_bp.get(
    "/events/<int:event_id>"
)
def event_detail(event_id: int):

    event = db.get_or_404(
        Event,
        event_id,
    )

    # Automatically repair missing AI plan
    _recover_ai_plan(event)

    return render_template(
        "events/detail.html",
        event=event,
    )


# =========================================================
# ORGANIZER EVENT MANAGEMENT
# =========================================================

@events_bp.get(
    "/events/<int:event_id>/manage"
)
@login_required
def manage_event(event_id: int):

    event = db.get_or_404(
        Event,
        event_id,
    )

    if not _organizer_owns(event):
        abort(403)

    # Automatically repair missing AI plan
    _recover_ai_plan(event)

    return render_template(
        "events/manage.html",
        event=event,
    )


# =========================================================
# FULL AI PLAN PAGE
# =========================================================

@events_bp.get(
    "/events/<int:event_id>/ai-plan"
)
def ai_plan(event_id: int):

    event = db.get_or_404(
        Event,
        event_id,
    )

    # Existing plan or automatically recovered plan
    plan = _recover_ai_plan(event)

    return render_template(
        "events/ai_plan.html",
        event=event,
        plan=plan,
    )


# =========================================================
# SEPARATE LOCAL AI EVENT PLANNER
#
# NO GEMINI
# NO OPENAI
# NO EXTERNAL API
#
# Uses existing LangGraph-based generate_event_plan()
# =========================================================

@events_bp.route(
    "/ai-event-planner",
    methods=["GET", "POST"],
)
@login_required
def local_ai_event_planner():

    generated_plan = None

    description = ""
    budget_bdt = ""
    audience = ""

    detected_category = None
    suggested_title = None

    if request.method == "POST":

        # =================================================
        # GET USER INPUT
        # =================================================

        description = request.form.get(
            "description",
            "",
        ).strip()

        budget_bdt = request.form.get(
            "budget_bdt",
            "",
        ).strip()

        audience = request.form.get(
            "audience",
            "",
        ).strip()

        # =================================================
        # VALIDATE DESCRIPTION
        # =================================================

        if not description:

            flash(
                "Please enter an event description.",
                "danger",
            )

            return render_template(
                "events/local_ai_planner.html",

                generated_plan=None,

                description=description,

                budget_bdt=budget_bdt,

                audience=audience,

                detected_category=None,

                suggested_title=None,
            )

        # =================================================
        # VALIDATE BUDGET / AUDIENCE
        # =================================================

        try:

            budget_value = float(
                budget_bdt
            )

            audience_value = int(
                audience
            )

        except (
            ValueError,
            TypeError,
        ):

            flash(
                "Budget and audience must be valid numbers.",
                "danger",
            )

            return render_template(
                "events/local_ai_planner.html",

                generated_plan=None,

                description=description,

                budget_bdt=budget_bdt,

                audience=audience,

                detected_category=None,

                suggested_title=None,
            )

        if budget_value <= 0:

            flash(
                "Budget must be greater than zero.",
                "danger",
            )

            return render_template(
                "events/local_ai_planner.html",

                generated_plan=None,

                description=description,

                budget_bdt=budget_bdt,

                audience=audience,

                detected_category=None,

                suggested_title=None,
            )

        if audience_value <= 0:

            flash(
                "Expected audience must be greater than zero.",
                "danger",
            )

            return render_template(
                "events/local_ai_planner.html",

                generated_plan=None,

                description=description,

                budget_bdt=budget_bdt,

                audience=audience,

                detected_category=None,

                suggested_title=None,
            )

        # =================================================
        # AUTOMATIC EVENT CATEGORY DETECTION
        # =================================================

        text = description.lower()

        # -------------------------------------------------
        # SOCIAL EVENT
        # -------------------------------------------------

        if any(
            keyword in text
            for keyword in [
                "wedding",
                "marriage",
                "birthday",
                "ceremony",
                "reception",
                "party",
                "social event",
                "anniversary",
                "engagement",
            ]
        ):

            detected_category = "social"

        # -------------------------------------------------
        # CONCERT
        # -------------------------------------------------

        elif any(
            keyword in text
            for keyword in [
                "concert",
                "music",
                "musical",
                "singer",
                "band",
                "artist",
                "live performance",
                "music festival",
            ]
        ):

            detected_category = "concert"

        # -------------------------------------------------
        # CONFERENCE
        # -------------------------------------------------

        elif any(
            keyword in text
            for keyword in [
                "conference",
                "seminar",
                "summit",
                "workshop",
                "symposium",
                "training",
                "forum",
            ]
        ):

            detected_category = "conference"

        # -------------------------------------------------
        # CORPORATE EVENT
        # -------------------------------------------------

        elif any(
            keyword in text
            for keyword in [
                "corporate",
                "company",
                "business",
                "office",
                "product launch",
                "annual meeting",
                "business meeting",
                "corporate event",
            ]
        ):

            detected_category = "corporate"

        # -------------------------------------------------
        # UNIVERSITY / ACADEMIC EVENT
        # -------------------------------------------------

        elif any(
            keyword in text
            for keyword in [
                "university",
                "college",
                "student",
                "students",
                "hackathon",
                "coding competition",
                "campus",
                "academic",
                "cse",
                "project showcase",
                "tech fest",
                "technology festival",
            ]
        ):

            detected_category = "university"

        # -------------------------------------------------
        # OTHER
        # -------------------------------------------------

        else:

            detected_category = "other"

        # =================================================
        # AUTOMATIC EVENT TITLE
        # =================================================

        title_words = (
            description.split()
        )

        if len(title_words) <= 8:

            suggested_title = (
                description
            )

        else:

            suggested_title = (
                " ".join(
                    title_words[:8]
                )
                + "..."
            )

        # =================================================
        # AUTOMATIC PLANNING DATE
        #
        # Since the separate AI planner asks only:
        #
        # description
        # budget
        # audience
        #
        # We assume 45 days of preparation.
        # =================================================

        planned_event_date = (
            date.today()
            + timedelta(days=45)
        )

        # =================================================
        # GENERATE EVENT PLAN
        #
        # Existing LangGraph planner is used here.
        # =================================================

        try:

            generated_plan = generate_event_plan(
                title=suggested_title,

                category=detected_category,

                description=description,

                venue="To be confirmed",

                event_date=planned_event_date,

                capacity=audience_value,

                total_budget_bdt=budget_value,
            )

            flash(
                "AI event plan generated successfully.",
                "success",
            )

        except Exception as exc:

            generated_plan = None

            flash(
                (
                    "AI plan generation failed: "
                    f"{exc}"
                ),
                "danger",
            )

    # =====================================================
    # DISPLAY AI PLANNER PAGE
    # =====================================================

    return render_template(
        "events/local_ai_planner.html",

        generated_plan=generated_plan,

        description=description,

        budget_bdt=budget_bdt,

        audience=audience,

        detected_category=detected_category,

        suggested_title=suggested_title,
    )


# =========================================================
# VERIFY BLOCKCHAIN / NFT TICKET
# =========================================================

@events_bp.route(
    "/tickets/verify",
    methods=["GET", "POST"],
)
def verify_ticket():

    form = VerifyTicketForm()

    result = None

    token_from_query = request.args.get(
        "token_id",
        type=int,
    )

    # -------------------------------------------------
    # TOKEN FROM QR CODE
    # -------------------------------------------------

    if (
        token_from_query
        and request.method == "GET"
    ):

        form.token_id.data = (
            token_from_query
        )

    # -------------------------------------------------
    # VERIFY
    # -------------------------------------------------

    if (
        form.validate_on_submit()
        or token_from_query
    ):

        token_id = (
            form.token_id.data
            or token_from_query
        )

        try:

            # -----------------------------------------
            # CONNECT BLOCKCHAIN SERVICE
            # -----------------------------------------

            service = (
                BlockchainService()
            )

            # -----------------------------------------
            # VERIFY NFT FROM BLOCKCHAIN
            # -----------------------------------------

            chain_result = (
                service.verify_ticket(
                    token_id
                )
            )

            # -----------------------------------------
            # LOCAL DATABASE TICKET
            # -----------------------------------------

            local_ticket = (
                Ticket.query
                .filter_by(
                    token_id=token_id
                )
                .first()
            )

            # -----------------------------------------
            # LOCAL EVENT
            # -----------------------------------------

            chain_event = None

            if chain_result.get(
                "event_id"
            ):

                chain_event = (
                    db.session.get(
                        Event,

                        chain_result[
                            "event_id"
                        ],
                    )
                )

            # -----------------------------------------
            # FINAL RESULT
            # -----------------------------------------

            result = {
                **chain_result,

                "token_id": token_id,

                "ticket": local_ticket,

                "event": chain_event,
            }

        except BlockchainError as exc:

            flash(
                str(exc),
                "danger",
            )

    return render_template(
        "tickets/verify.html",

        form=form,

        result=result,
    )


# =========================================================
# MY NFT TICKETS
# =========================================================

@events_bp.get(
    "/tickets"
)
@login_required
def my_tickets():

    tickets = (
        Ticket.query
        .filter_by(
            user_id=current_user.id
        )
        .order_by(
            Ticket.purchased_at.desc()
        )
        .all()
    )

    return render_template(
        "tickets/list.html",
        tickets=tickets,
    )


# =========================================================
# NFT TICKET QR CODE
# =========================================================

@events_bp.get(
    "/tickets/<int:ticket_id>/qr.png"
)
@login_required
def ticket_qr(ticket_id: int):

    ticket = db.get_or_404(
        Ticket,
        ticket_id,
    )

    # -------------------------------------------------
    # SECURITY CHECK
    # -------------------------------------------------

    if (
        current_user.role != "admin"
        and ticket.user_id
        != current_user.id
    ):

        abort(403)

    # -------------------------------------------------
    # VERIFICATION URL
    # -------------------------------------------------

    verification_url = url_for(
        "events.verify_ticket",

        token_id=ticket.token_id,

        _external=True,
    )

    # -------------------------------------------------
    # GENERATE QR CODE
    # -------------------------------------------------

    image = qrcode.make(
        verification_url
    )

    buffer = io.BytesIO()

    image.save(
        buffer,
        format="PNG",
    )

    buffer.seek(0)

    # -------------------------------------------------
    # RETURN PNG
    # -------------------------------------------------

    return send_file(
        buffer,

        mimetype="image/png",

        max_age=0,
    )