"""
Audit Routes — receives events from n8n Workflow 03 (Error Alert & Audit Logger).
Stores everything in MongoDB audit_events and audit_alerts collections.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db.mongo import get_database

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/audit", tags=["audit"])


# ── Pydantic models ────────────────────────────────────────────────────────────

class AuditLogRequest(BaseModel):
    event: str
    severity: str = "info"          # info | warning | critical
    username: str = "system"
    details: Optional[Any] = None
    source: str = "n8n-workflow-03"
    enriched_at: Optional[str] = None


class AuditAlertRequest(BaseModel):
    alert_type: str
    message: str
    event: str
    severity: str
    username: str = "system"
    timestamp: Optional[str] = None


# ── Helper ─────────────────────────────────────────────────────────────────────

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Routes ────────────────────────────────────────────────────────────────────

@router.post("/log", summary="Write an audit event to MongoDB")
async def audit_log(payload: AuditLogRequest):
    """
    Called by n8n Workflow 03 for EVERY incoming RAG event.
    Stores the enriched event in the audit_events collection.
    """
    try:
        db = get_database()  # sync call
        doc = {
            "event": payload.event,
            "severity": payload.severity,
            "username": payload.username,
            "details": payload.details,
            "source": payload.source,
            "enriched_at": payload.enriched_at or _now_iso(),
            "logged_at": _now_iso(),
        }
        result = await db["audit_events"].insert_one(doc)
        logger.info(
            "Audit event logged: %s [%s] by %s",
            payload.event, payload.severity, payload.username
        )
        return {
            "status": "logged",
            "id": str(result.inserted_id),
            "event": payload.event,
            "severity": payload.severity,
        }
    except Exception as exc:
        logger.error("Failed to write audit log: %s", exc)
        raise HTTPException(status_code=500, detail=f"Audit log failed: {exc}")


@router.post("/alert", summary="Write a critical/warning alert to MongoDB")
async def audit_alert(payload: AuditAlertRequest):
    """
    Called by n8n Workflow 03 only when severity >= warning.
    Stores the formatted alert in the audit_alerts collection.
    """
    try:
        db = get_database()  # sync call
        doc = {
            "alert_type": payload.alert_type,
            "message": payload.message,
            "event": payload.event,
            "severity": payload.severity,
            "username": payload.username,
            "timestamp": payload.timestamp or _now_iso(),
            "logged_at": _now_iso(),
        }
        result = await db["audit_alerts"].insert_one(doc)
        logger.warning(
            "AUDIT ALERT: %s [%s] — %s",
            payload.event, payload.severity, payload.message[:100]
        )
        return {
            "status": "alert_logged",
            "id": str(result.inserted_id),
            "alert_type": payload.alert_type,
            "severity": payload.severity,
        }
    except Exception as exc:
        logger.error("Failed to write audit alert: %s", exc)
        raise HTTPException(status_code=500, detail=f"Audit alert failed: {exc}")


@router.get("/events", summary="List recent audit events")
async def list_audit_events(limit: int = 50):
    """Returns the most recent audit events from MongoDB."""
    try:
        db = get_database()  # sync call
        cursor = db["audit_events"].find(
            {}, {"_id": 0}
        ).sort("logged_at", -1).limit(limit)
        events = await cursor.to_list(length=limit)
        return {"count": len(events), "events": events}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/alerts", summary="List recent critical/warning alerts")
async def list_audit_alerts(limit: int = 20):
    """Returns the most recent critical/warning alerts from MongoDB."""
    try:
        db = get_database()  # sync call
        cursor = db["audit_alerts"].find(
            {}, {"_id": 0}
        ).sort("logged_at", -1).limit(limit)
        alerts = await cursor.to_list(length=limit)
        return {"count": len(alerts), "alerts": alerts}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
