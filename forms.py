"""WTForms with CSRF protection."""

from flask_wtf import FlaskForm
from wtforms import (
    BooleanField,
    DecimalField,
    PasswordField,
    SelectField,
    StringField,
    TextAreaField,
)
from wtforms.validators import DataRequired, Email, EqualTo, Length, NumberRange


class LoginForm(FlaskForm):
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired()])


class SignupForm(FlaskForm):
    full_name = StringField("Full name", validators=[DataRequired(), Length(min=2, max=120)])
    email = StringField("Email", validators=[DataRequired(), Email()])
    password = PasswordField("Password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm password",
        validators=[DataRequired(), EqualTo("password", message="Passwords must match.")],
    )


class TransactionForm(FlaskForm):
    transaction_id = StringField("Transaction ID")
    amount = DecimalField("Amount", validators=[DataRequired(), NumberRange(min=0.01)])
    transaction_type = SelectField(
        "Transaction Type",
        choices=[
            ("TRANSFER", "TRANSFER"),
            ("WITHDRAWAL", "WITHDRAWAL"),
            ("DEPOSIT", "DEPOSIT"),
            ("PAYMENT", "PAYMENT"),
            ("UPI", "UPI"),
        ],
        validators=[DataRequired()],
    )
    beneficiary = StringField("Beneficiary", validators=[DataRequired(), Length(max=120)])
    location = StringField("Location", validators=[DataRequired(), Length(max=120)])
    device_id = StringField("Device ID", validators=[DataRequired(), Length(max=80)])
    ip_address = StringField("IP Address", validators=[DataRequired(), Length(max=64)])
    transaction_time = StringField("Transaction Time", validators=[DataRequired(), Length(max=40)])
    is_international = BooleanField("International Transaction")
    is_new_device = BooleanField("New Device")
    is_new_beneficiary = BooleanField("New Beneficiary")


class OTPForm(FlaskForm):
    transaction_id = StringField("Transaction ID", validators=[DataRequired()])
    otp_code = StringField("OTP", validators=[DataRequired(), Length(min=6, max=6)])


class ProfilePasswordForm(FlaskForm):
    current_password = PasswordField("Current password", validators=[DataRequired()])
    new_password = PasswordField("New password", validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField(
        "Confirm new password",
        validators=[DataRequired(), EqualTo("new_password")],
    )


class FeedbackForm(FlaskForm):
    comment = TextAreaField("Feedback", validators=[DataRequired(), Length(min=3, max=2000)])


class InvestigationUpdateForm(FlaskForm):
    status = SelectField(
        "Status",
        choices=[
            ("OPEN", "OPEN"),
            ("INVESTIGATING", "INVESTIGATING"),
            ("RESOLVED", "RESOLVED"),
            ("FALSE_POSITIVE", "FALSE_POSITIVE"),
            ("CONFIRMED_FRAUD", "CONFIRMED_FRAUD"),
        ],
        validators=[DataRequired()],
    )
    assign_to_self = BooleanField("Assign to me")
