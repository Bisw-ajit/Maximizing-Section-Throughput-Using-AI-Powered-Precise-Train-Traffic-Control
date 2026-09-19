"""
RAILOPTIX — Sequential Dispatch Audit Log Inspector
===================================================
Maintains a sequential, chronological audit trail of all train movements,
signal transitions, conflict detections, and controller actions.

Fulfills: JIRA RAIL-18.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any
from threading import Lock


class AuditCategory:
    CONTROLLER_ACTION = "CONTROLLER_ACTION"
    CONFLICT_ALERT = "CONFLICT_ALERT"
    SIGNAL_ASPECT = "SIGNAL_ASPECT"
    SIDING_ALLOCATION = "SIDING_ALLOCATION"
    TRAIN_MOVEMENT = "TRAIN_MOVEMENT"


@dataclass
class AuditLogEntry:
    entry_id: str
    timestamp: str
    category: str       # "CONTROLLER_ACTION" | "CONFLICT_ALERT" | "SIGNAL_ASPECT" | "SIDING_ALLOCATION" | "TRAIN_MOVEMENT"
    event_type: str     # e.g. "ACTION_APPLIED", "CONFLICT_DETECTED", "SIGNAL_CLEARED", "HOLD_INITIATED"
    train_id: Optional[str]
    location: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "entry_id": self.entry_id,
            "timestamp": self.timestamp,
            "category": self.category,
            "event_type": self.event_type,
            "train_id": self.train_id,
            "location": self.location,
            "message": self.message,
            "details": self.details,
        }


class AuditLogger:
    """
    Central chronological audit logging engine for controller actions and network state changes.
    """

    def __init__(self, max_entries: int = 500):
        self.max_entries = max_entries
        self._lock = Lock()
        self._entries: List[AuditLogEntry] = []
        self._counter = 0
        self._seed_default_audit_entries()

    def _seed_default_audit_entries(self):
        """Pre-seeds realistic corridor startup audit entries for demonstration."""
        now_iso = datetime.now(timezone.utc).isoformat()
        self.log_event(
            category="TRAIN_MOVEMENT",
            event_type="CORRIDOR_INIT",
            train_id=None,
            location="KUR",
            message="ECoR Khurda Road Division CTC Signalling Board initialised. 11 nodes online.",
        )
        self.log_event(
            category="TRAIN_MOVEMENT",
            event_type="DEPARTURE",
            train_id="T001",
            location="CTK",
            message="Train T001 Puri Express departed Cuttack Platform 1.",
        )
        self.log_event(
            category="TRAIN_MOVEMENT",
            event_type="DEPARTURE",
            train_id="T003",
            location="BAM",
            message="Train T003 New Delhi Rajdhani Express departed Brahmapur Platform 1 on-time.",
        )
        self.log_event(
            category="CONFLICT_ALERT",
            event_type="CONFLICT_DETECTED",
            train_id="T001",
            location="KUR",
            message="Bottleneck contention CONF_001 detected: T001 and T003 converging at Khurda Road.",
            details={"conflict_type": "JUNCTION_CONFLICT", "severity": "HIGH"},
        )
        self.log_event(
            category="CONTROLLER_ACTION",
            event_type="RECOMMENDATION_GENERATED",
            train_id="T003",
            location="KUR",
            message="AI Engine recommended CONF_001_ACT_PRIO_HIGH: Green corridor right-of-way for Rajdhani.",
            details={"composite_score": 92.4, "priority": 1},
        )

    def log_event(
        self,
        category: str,
        event_type: str,
        location: str,
        message: str,
        train_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> AuditLogEntry:
        """Appends a new chronological entry to the audit log."""
        with self._lock:
            self._counter += 1
            entry_id = f"AUD_{self._counter:05d}"
            entry = AuditLogEntry(
                entry_id=entry_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
                category=category,
                event_type=event_type,
                train_id=train_id,
                location=location,
                message=message,
                details=details or {},
            )
            self._entries.insert(0, entry)  # Most recent first
            if len(self._entries) > self.max_entries:
                self._entries.pop()
            return entry

    def get_entries(
        self,
        limit: int = 50,
        category: Optional[str] = None,
        train_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieves filtered chronological audit entries."""
        with self._lock:
            filtered = self._entries
            if category:
                filtered = [e for e in filtered if e.category.upper() == category.upper()]
            if train_id:
                filtered = [e for e in filtered if e.train_id == train_id]
            return [e.to_dict() for e in filtered[:limit]]

    def clear(self) -> None:
        """Resets the audit log buffer."""
        with self._lock:
            self._entries.clear()
            self._counter = 0


audit_logger = AuditLogger()
