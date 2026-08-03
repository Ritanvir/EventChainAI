from __future__ import annotations

import json
from datetime import datetime, timezone

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from .extensions import db


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="attendee")
    wallet_address = db.Column(db.String(42), nullable=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    events = db.relationship("Event", back_populates="organizer", lazy=True)
    tickets = db.relationship("Ticket", back_populates="user", lazy=True)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)


class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    organizer_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    venue = db.Column(db.String(200), nullable=False)
    event_date = db.Column(db.Date, nullable=False)
    attendee_capacity = db.Column(db.Integer, nullable=False)
    ticket_price_eth = db.Column(db.Numeric(18, 8), nullable=False, default=0)
    budget_bdt = db.Column(db.Numeric(16, 2), nullable=False, default=0)
    status = db.Column(db.String(30), nullable=False, default="draft")
    chain_status = db.Column(db.String(30), nullable=False, default="not_published")
    blockchain_tx_hash = db.Column(db.String(66), nullable=True)
    ai_plan_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = db.Column(
        db.DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    organizer = db.relationship("User", back_populates="events")
    tickets = db.relationship("Ticket", back_populates="event", lazy=True)
    sponsorships = db.relationship("Sponsorship", back_populates="event", lazy=True)
    escrows = db.relationship("VendorEscrow", back_populates="event", lazy=True)

    @property
    def ai_plan(self) -> dict:
        if not self.ai_plan_json:
            return {}
        try:
            return json.loads(self.ai_plan_json)
        except json.JSONDecodeError:
            return {}

    @property
    def ticket_price_display(self) -> str:
        value = f"{self.ticket_price_eth:.8f}".rstrip("0").rstrip(".")
        return value or "0"


class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    buyer_wallet = db.Column(db.String(42), nullable=False, index=True)
    token_id = db.Column(db.Integer, nullable=False, unique=True, index=True)
    tx_hash = db.Column(db.String(66), nullable=False, unique=True)
    status = db.Column(db.String(20), nullable=False, default="valid")
    purchased_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    checked_in_at = db.Column(db.DateTime(timezone=True), nullable=True)

    event = db.relationship("Event", back_populates="tickets")
    user = db.relationship("User", back_populates="tickets")


class Sponsorship(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    sponsor_user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    sponsor_wallet = db.Column(db.String(42), nullable=False)
    amount_eth = db.Column(db.Numeric(18, 8), nullable=False)
    tx_hash = db.Column(db.String(66), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    event = db.relationship("Event", back_populates="sponsorships")
    sponsor = db.relationship("User")


class VendorEscrow(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=False)
    chain_escrow_id = db.Column(db.Integer, nullable=False, unique=True, index=True)
    vendor_name = db.Column(db.String(150), nullable=False)
    vendor_wallet = db.Column(db.String(42), nullable=False, index=True)
    description = db.Column(db.String(500), nullable=False)
    amount_eth = db.Column(db.Numeric(18, 8), nullable=False)
    create_tx_hash = db.Column(db.String(66), nullable=False, unique=True)
    release_tx_hash = db.Column(db.String(66), nullable=True, unique=True)
    refund_tx_hash = db.Column(db.String(66), nullable=True, unique=True)
    status = db.Column(db.String(20), nullable=False, default="locked")
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)
    released_at = db.Column(db.DateTime(timezone=True), nullable=True)
    refunded_at = db.Column(db.DateTime(timezone=True), nullable=True)

    event = db.relationship("Event", back_populates="escrows")


class BlockchainTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=True)
    event_id = db.Column(db.Integer, db.ForeignKey("event.id"), nullable=True)
    tx_type = db.Column(db.String(40), nullable=False)
    tx_hash = db.Column(db.String(66), nullable=False, unique=True, index=True)
    status = db.Column(db.String(20), nullable=False, default="confirmed")
    details_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), default=utcnow, nullable=False)

    user = db.relationship("User")
    event = db.relationship("Event")
