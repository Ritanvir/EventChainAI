from datetime import date

from flask_wtf import FlaskForm
from wtforms import (
    DateField,
    DecimalField,
    IntegerField,
    PasswordField,
    SelectField,
    StringField,
    SubmitField,
    TextAreaField,
)
from wtforms.validators import (
    DataRequired,
    Email,
    EqualTo,
    InputRequired,
    Length,
    NumberRange,
    ValidationError,
)

from .models import User


ROLE_CHOICES = [
    ("organizer", "Organizer"),
    ("attendee", "Attendee"),
    ("vendor", "Vendor"),
    ("sponsor", "Sponsor"),
]

CATEGORY_CHOICES = [
    ("university", "University event"),
    ("conference", "Conference / seminar"),
    ("corporate", "Corporate event"),
    ("concert", "Concert / cultural event"),
    ("social", "Social gathering"),
    ("other", "Other"),
]


class RegistrationForm(FlaskForm):
    name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email(), Length(max=255)])
    role = SelectField("Account type", choices=ROLE_CHOICES, validators=[DataRequired()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )
    submit = SubmitField("Create account")

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower().strip()).first():
            raise ValidationError("An account with this email already exists.")


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])
    submit = SubmitField("Log in")


class EventForm(FlaskForm):
    title = StringField("Event title", validators=[DataRequired(), Length(max=180)])
    category = SelectField("Category", choices=CATEGORY_CHOICES, validators=[DataRequired()])
    description = TextAreaField(
        "Description", validators=[DataRequired(), Length(min=20, max=4000)]
    )
    venue = StringField("Venue", validators=[DataRequired(), Length(max=200)])
    event_date = DateField("Event date", validators=[DataRequired()])
    attendee_capacity = IntegerField(
        "Expected attendees", validators=[DataRequired(), NumberRange(min=1, max=1000000)]
    )
    ticket_price_eth = DecimalField(
        "Ticket price (ETH)",
        validators=[InputRequired(), NumberRange(min=0, max=1000)],
        places=8,
    )
    budget_bdt = DecimalField(
        "Estimated total budget (BDT)",
        validators=[DataRequired(), NumberRange(min=1000, max=10000000000)],
        places=2,
    )
    submit = SubmitField("Save event and generate AI plan")

    def validate_event_date(self, field):
        if field.data < date.today():
            raise ValidationError("Event date cannot be in the past.")


class VerifyTicketForm(FlaskForm):
    token_id = IntegerField(
        "NFT token ID", validators=[DataRequired(), NumberRange(min=1)]
    )
    submit = SubmitField("Verify ticket")
