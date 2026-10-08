from flask import Blueprint, request, session

from services.investigation_service import apply_update, investigation_detail, list_investigations
from utils.helpers import json_error, json_ok, login_required, role_required

bp = Blueprint("investigations_api", __name__, url_prefix="/api/investigations")


@bp.get("")
@login_required
def list_cases():
    status = request.args.get("status")
    return json_ok(list_investigations(status))


@bp.get("/<investigation_id>")
@login_required
def get_case(investigation_id):
    case = investigation_detail(investigation_id)
    if not case:
        return json_error("Investigation not found", 404)
    return json_ok(case)


@bp.post("/<investigation_id>/update")
@role_required("ADMIN", "INVESTIGATOR")
def update(investigation_id):
    payload = request.get_json(silent=True) or {}
    try:
        case = apply_update(
            investigation_id,
            payload,
            user_id=session.get("user_id"),
            username=session.get("username"),
        )
    except ValueError as exc:
        return json_error(str(exc), 400)
    if not case:
        return json_error("Investigation not found", 404)
    return json_ok(case)
