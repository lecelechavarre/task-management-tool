from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

@dataclass
class Task:
    id: int
    title: str
    description: str
    status: str
    priority: str
    created_at: str
    due_date: Optional[str] = None
    duration_seconds: int = 0
    remaining_seconds: int = 0
    completed_at: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self):
        return asdict(self)

    @staticmethod
    def from_dict(d: dict):
        # Provide robust defaults if keys are missing
        return Task(
            id=int(d.get("id", 0)),
            title=d.get("title", ""),
            description=d.get("description", ""),
            status=d.get("status", "pending"),
            priority=d.get("priority", "low"),
            created_at=d.get("created_at"),
            due_date=d.get("due_date"),
            duration_seconds=int(d.get("duration_seconds", 0)),
            remaining_seconds=int(d.get("remaining_seconds", d.get("duration_seconds", 0))),
            completed_at=d.get("completed_at")  # THIS LINE WAS MISSING - THIS IS THE FIX!
        )
