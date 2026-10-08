"""Optional IBM service hooks with a local mock fallback."""

from config import Config
from utils.logger import get_logger

logger = get_logger(__name__)


def optional_ibm_score(feature_row):
    """Never required for local demos. Returns unused unless IBM_ENABLED=true."""
    if not Config.IBM_ENABLED:
        return {
            "used": False,
            "provider": "local_fallback",
            "probability": None,
            "note": "IBM integration disabled; local ML + rules are used.",
        }
    if not Config.IBM_API_KEY or not Config.IBM_SERVICE_URL:
        logger.warning("IBM_ENABLED is true but credentials are missing; using mock score")
        amount_dev = float(feature_row.get("amount_deviation") or 0)
        mock = min(0.99, 0.2 + amount_dev / 8)
        return {
            "used": True,
            "provider": "ibm_mock",
            "probability": round(mock, 4),
            "note": "Mock IBM score for demonstration only.",
        }
    # Real HTTP call is intentionally not made; keep demos offline-safe.
    return {
        "used": True,
        "provider": "ibm_configured_offline",
        "probability": min(0.99, float(feature_row.get("amount_deviation") or 0) / 6),
        "note": "Credentials present but live IBM call is skipped in this academic build.",
    }
