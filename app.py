"""Flask application for local financial fraud detection."""

from __future__ import annotations

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from flask_wtf.csrf import CSRFProtect

from auth.authentication import (
    authenticate,
    create_user,
    current_user,
    login_required,
    login_user_session,
    logout_user_session,
    roles_required,
    validate_password_strength,
    verify_password,
)
from config import Config, get_database_path
from database.db import execute, fetch_all, fetch_one, init_db
from forms import (
    FeedbackForm,
    InvestigationUpdateForm,
    LoginForm,
    OTPForm,
    ProfilePasswordForm,
    SignupForm,
    TransactionForm,
)
from investigation.investigator import add_feedback, assign_investigation, update_status
from pipeline import process_new_transaction, verify_otp
from reports.pdf_report import generate_investigation_pdf
from stats import admin_stats, investigator_stats, user_dashboard_stats

csrf = CSRFProtect()


def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)
    if test_config:
        app.config.update(test_config)
        if test_config.get("DATABASE_PATH"):
            import os

            os.environ["DATABASE_PATH"] = test_config["DATABASE_PATH"]
    csrf.init_app(app)
    init_db(app.config.get("DATABASE_PATH") or get_database_path())

    @app.context_processor
    def inject_globals():
        return {"current_user": current_user()}

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("error.html", code=404, message="Page not found."), 404

    @app.errorhandler(403)
    def forbidden(_e):
        return render_template("error.html", code=403, message="Access denied."), 403

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("error.html", code=500, message="Unexpected server error."), 500

    @app.route("/")
    def index():
        if session.get("user_id"):
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        form = LoginForm()
        if form.validate_on_submit():
            user = authenticate(form.email.data, form.password.data)
            if not user:
                flash("Invalid email or password.", "danger")
                return render_template("login.html", form=form)
            login_user_session(user)
            flash("Logged in successfully.", "success")
            if user["role"] == "ADMIN":
                return redirect(url_for("admin_dashboard"))
            if user["role"] == "INVESTIGATOR":
                return redirect(url_for("investigator_dashboard"))
            return redirect(url_for("dashboard"))
        return render_template("login.html", form=form)

    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        form = SignupForm()
        if form.validate_on_submit():
            ok, message = validate_password_strength(form.password.data)
            if not ok:
                flash(message, "danger")
                return render_template("signup.html", form=form)
            try:
                user = create_user(form.email.data, form.password.data, form.full_name.data)
            except ValueError as exc:
                flash(str(exc), "danger")
                return render_template("signup.html", form=form)
            login_user_session(user)
            flash("Account created.", "success")
            return redirect(url_for("dashboard"))
        return render_template("signup.html", form=form)

    @app.route("/logout")
    def logout():
        logout_user_session()
        flash("You have been logged out.", "info")
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        user = current_user()
        stats = user_dashboard_stats(user["id"], user["role"])
        recent = fetch_all(
            """
            SELECT * FROM transactions
            WHERE user_id = ?
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT 8
            """
            if user["role"] == "USER"
            else """
            SELECT * FROM transactions
            ORDER BY datetime(created_at) DESC, id DESC
            LIMIT 8
            """,
            (user["id"],) if user["role"] == "USER" else (),
        )
        return render_template("dashboard.html", stats=stats, recent=recent)

    @app.route("/admin")
    @roles_required("ADMIN")
    def admin_dashboard():
        return render_template("admin_dashboard.html", stats=admin_stats())

    @app.route("/investigator")
    @roles_required("INVESTIGATOR", "ADMIN")
    def investigator_dashboard():
        open_cases = fetch_all(
            """
            SELECT i.*, t.amount, t.risk_score, t.risk_level
            FROM investigations i
            LEFT JOIN transactions t ON t.transaction_id = i.transaction_id
            WHERE i.status IN ('OPEN','INVESTIGATING')
            ORDER BY datetime(i.created_at) DESC
            """
        )
        return render_template(
            "investigator_dashboard.html",
            stats=investigator_stats(),
            cases=open_cases,
        )

    @app.route("/transaction", methods=["GET", "POST"])
    @login_required
    def new_transaction():
        form = TransactionForm()
        if form.validate_on_submit():
            payload = {
                "transaction_id": form.transaction_id.data,
                "amount": form.amount.data,
                "transaction_type": form.transaction_type.data,
                "beneficiary": form.beneficiary.data,
                "location": form.location.data,
                "device_id": form.device_id.data,
                "ip_address": form.ip_address.data,
                "transaction_time": form.transaction_time.data,
                "is_international": form.is_international.data,
                "is_new_device": form.is_new_device.data,
                "is_new_beneficiary": form.is_new_beneficiary.data,
            }
            result = process_new_transaction(session["user_id"], payload)
            if not result["ok"]:
                for err in result["errors"]:
                    flash(err, "danger")
                return render_template("transaction.html", form=form)
            txn = result["transaction"]
            if txn["risk_level"] == "MEDIUM":
                session["demo_otp"] = result["otp_code"]
                session["otp_txn"] = txn["transaction_id"]
                flash("Additional verification required.", "warning")
                return redirect(url_for("verify_otp_route", transaction_id=txn["transaction_id"]))
            return redirect(url_for("transaction_detail", transaction_id=txn["transaction_id"]))
        return render_template("transaction.html", form=form)

    @app.route("/transaction/<transaction_id>")
    @login_required
    def transaction_detail(transaction_id):
        txn = fetch_one("SELECT * FROM transactions WHERE transaction_id = ?", (transaction_id,))
        if not txn:
            abort(404)
        user = current_user()
        if user["role"] == "USER" and txn["user_id"] != user["id"]:
            abort(403)
        investigation = fetch_one(
            "SELECT * FROM investigations WHERE transaction_id = ?", (transaction_id,)
        )
        reasons = [line[2:].strip() if line.startswith("- ") else line for line in (txn.get("explanation") or "").splitlines() if line.strip()]
        return render_template(
            "transaction_result.html",
            txn=txn,
            investigation=investigation,
            reasons=reasons,
        )

    @app.route("/verify-otp", methods=["GET", "POST"])
    @login_required
    def verify_otp_route():
        form = OTPForm()
        txn_id = request.args.get("transaction_id") or session.get("otp_txn") or form.transaction_id.data
        if request.method == "GET" and txn_id:
            form.transaction_id.data = txn_id
        demo_otp = session.get("demo_otp") if session.get("otp_txn") == (txn_id or session.get("otp_txn")) else None
        if form.validate_on_submit():
            ok, message = verify_otp(form.transaction_id.data, form.otp_code.data)
            flash(message, "success" if ok else "danger")
            if ok:
                session.pop("demo_otp", None)
                session.pop("otp_txn", None)
                return redirect(url_for("transaction_detail", transaction_id=form.transaction_id.data))
        return render_template("otp.html", form=form, demo_otp=demo_otp, transaction_id=txn_id)

    @app.route("/history")
    @login_required
    def history():
        user = current_user()
        risk = request.args.get("risk_level") or ""
        status = request.args.get("status") or ""
        txn_type = request.args.get("transaction_type") or ""
        search = request.args.get("q") or ""
        clauses = []
        params = []
        if user["role"] == "USER":
            clauses.append("user_id = ?")
            params.append(user["id"])
        if risk:
            clauses.append("risk_level = ?")
            params.append(risk)
        if status:
            clauses.append("status = ?")
            params.append(status)
        if txn_type:
            clauses.append("transaction_type = ?")
            params.append(txn_type)
        if search:
            clauses.append("(transaction_id LIKE ? OR beneficiary LIKE ? OR location LIKE ?)")
            like = f"%{search}%"
            params.extend([like, like, like])
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = fetch_all(
            f"SELECT * FROM transactions {where} ORDER BY datetime(created_at) DESC, id DESC",
            tuple(params),
        )
        return render_template(
            "history.html",
            rows=rows,
            risk=risk,
            status=status,
            txn_type=txn_type,
            search=search,
        )

    @app.route("/alerts")
    @login_required
    def alerts():
        user = current_user()
        severity = request.args.get("severity") or ""
        status = request.args.get("status") or ""
        if user["role"] == "USER":
            query = """
                SELECT a.* FROM alerts a
                JOIN transactions t ON t.transaction_id = a.transaction_id
                WHERE t.user_id = ?
            """
            params = [user["id"]]
            if severity:
                query += " AND a.severity = ?"
                params.append(severity)
            if status:
                query += " AND a.status = ?"
                params.append(status)
            query += " ORDER BY datetime(a.created_at) DESC, a.id DESC"
            rows = fetch_all(query, tuple(params))
        else:
            clauses = []
            params = []
            if severity:
                clauses.append("severity = ?")
                params.append(severity)
            if status:
                clauses.append("status = ?")
                params.append(status)
            where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
            rows = fetch_all(
                f"SELECT * FROM alerts {where} ORDER BY datetime(created_at) DESC, id DESC",
                tuple(params),
            )
        return render_template("alerts.html", rows=rows, severity=severity, status=status)

    @app.route("/investigations")
    @roles_required("INVESTIGATOR", "ADMIN")
    def investigations():
        status = request.args.get("status") or ""
        if status:
            rows = fetch_all(
                """
                SELECT i.*, t.amount, t.risk_score, t.risk_level
                FROM investigations i
                LEFT JOIN transactions t ON t.transaction_id = i.transaction_id
                WHERE i.status = ?
                ORDER BY datetime(i.created_at) DESC
                """,
                (status,),
            )
        else:
            rows = fetch_all(
                """
                SELECT i.*, t.amount, t.risk_score, t.risk_level
                FROM investigations i
                LEFT JOIN transactions t ON t.transaction_id = i.transaction_id
                ORDER BY datetime(i.created_at) DESC
                """
            )
        return render_template("investigations.html", rows=rows, status=status)

    @app.route("/investigation/<int:investigation_id>", methods=["GET", "POST"])
    @roles_required("INVESTIGATOR", "ADMIN")
    def investigation_detail(investigation_id):
        inv = fetch_one("SELECT * FROM investigations WHERE id = ?", (investigation_id,))
        if not inv:
            abort(404)
        form = InvestigationUpdateForm()
        if form.validate_on_submit():
            if form.assign_to_self.data:
                assign_investigation(investigation_id, session["user_id"], session.get("email"))
            update_status(investigation_id, form.status.data, session.get("email"))
            flash("Investigation updated.", "success")
            return redirect(url_for("investigation_detail", investigation_id=investigation_id))
        form.status.data = inv["status"]
        txn = fetch_one("SELECT * FROM transactions WHERE transaction_id = ?", (inv["transaction_id"],))
        evidence = fetch_all(
            "SELECT * FROM evidence WHERE investigation_id = ? ORDER BY id ASC",
            (investigation_id,),
        )
        timeline = fetch_all(
            "SELECT * FROM timeline_events WHERE investigation_id = ? ORDER BY datetime(created_at) ASC, id ASC",
            (investigation_id,),
        )
        comments = fetch_all(
            "SELECT f.*, u.email FROM feedback f JOIN users u ON u.id = f.user_id WHERE f.investigation_id = ? ORDER BY f.id ASC",
            (investigation_id,),
        )
        feedback_form = FeedbackForm()
        return render_template(
            "investigation_detail.html",
            inv=inv,
            txn=txn,
            evidence=evidence,
            timeline=timeline,
            comments=comments,
            form=form,
            feedback_form=feedback_form,
        )

    @app.route("/investigation/<int:investigation_id>/feedback", methods=["POST"])
    @roles_required("INVESTIGATOR", "ADMIN")
    def investigation_feedback(investigation_id):
        form = FeedbackForm()
        if form.validate_on_submit():
            add_feedback(investigation_id, session["user_id"], form.comment.data)
            flash("Feedback saved.", "success")
        else:
            flash("Feedback is required.", "danger")
        return redirect(url_for("investigation_detail", investigation_id=investigation_id))

    @app.route("/reports")
    @roles_required("INVESTIGATOR", "ADMIN")
    def reports():
        rows = fetch_all(
            """
            SELECT i.*, t.risk_level, t.risk_score
            FROM investigations i
            LEFT JOIN transactions t ON t.transaction_id = i.transaction_id
            ORDER BY datetime(i.created_at) DESC
            """
        )
        return render_template("reports.html", rows=rows)

    @app.route("/report/<int:investigation_id>/download")
    @roles_required("INVESTIGATOR", "ADMIN")
    def download_report(investigation_id):
        path = generate_investigation_pdf(investigation_id)
        return send_file(path, as_attachment=True, download_name=path.name)

    @app.route("/profile", methods=["GET", "POST"])
    @login_required
    def profile():
        user = fetch_one("SELECT * FROM users WHERE id = ?", (session["user_id"],))
        form = ProfilePasswordForm()
        if form.validate_on_submit():
            if not verify_password(user["password_hash"], form.current_password.data):
                flash("Current password is incorrect.", "danger")
                return render_template("profile.html", user=user, form=form)
            ok, message = validate_password_strength(form.new_password.data)
            if not ok:
                flash(message, "danger")
                return render_template("profile.html", user=user, form=form)
            from auth.authentication import hash_password

            execute(
                "UPDATE users SET password_hash = ? WHERE id = ?",
                (hash_password(form.new_password.data), user["id"]),
            )
            flash("Password updated.", "success")
            return redirect(url_for("profile"))
        return render_template("profile.html", user=user, form=form)

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
