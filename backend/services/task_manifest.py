"""Task manifest — context propagation through the agent hierarchy.

A TaskManifest dataclass travels with handoffs, carrying parent decisions,
sibling context, and constraints to receiving agents.
"""

import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TaskManifest:
    """Context bundle that propagates through the agent hierarchy."""
    segment_id: str
    parent_decisions: list[str] = field(default_factory=list)
    sibling_context: list[dict] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    verification_requirements: list[str] = field(default_factory=list)
    canary_phrase: str = ""
    origin_role: str = ""
    origin_session_id: str = ""

    def add_decision(self, decision: str) -> None:
        """Record a decision made by the parent agent."""
        self.parent_decisions.append(decision)

    def add_sibling(self, sibling_id: str, title: str, status: str) -> None:
        """Add context about a sibling segment."""
        self.sibling_context.append({
            "segment_id": sibling_id,
            "title": title,
            "status": status,
        })

    def add_constraint(self, constraint: str) -> None:
        """Add a constraint for the receiving agent."""
        self.constraints.append(constraint)

    def to_context_string(self) -> str:
        """Render manifest as a context string for injection into agent prompts."""
        sections = []

        if self.parent_decisions:
            sections.append("PARENT DECISIONS:\n" + "\n".join(f"- {d}" for d in self.parent_decisions))

        if self.sibling_context:
            lines = []
            for s in self.sibling_context:
                lines.append(f"- {s['title']} [{s['status']}] (id={s['segment_id']})")
            sections.append("SIBLING CONTEXT:\n" + "\n".join(lines))

        if self.constraints:
            sections.append("CONSTRAINTS:\n" + "\n".join(f"- {c}" for c in self.constraints))

        if self.verification_requirements:
            sections.append("VERIFICATION REQUIREMENTS:\n" + "\n".join(f"- {v}" for v in self.verification_requirements))

        if self.canary_phrase:
            sections.append(f"VERIFICATION CANARY: Include the phrase '{self.canary_phrase}' in your output.")

        return "\n\n".join(sections) if sections else ""

    def to_dict(self) -> dict:
        """Serialize for storage/transmission."""
        return {
            "segment_id": self.segment_id,
            "parent_decisions": self.parent_decisions,
            "sibling_context": self.sibling_context,
            "constraints": self.constraints,
            "verification_requirements": self.verification_requirements,
            "canary_phrase": self.canary_phrase,
            "origin_role": self.origin_role,
            "origin_session_id": self.origin_session_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TaskManifest":
        """Deserialize from storage."""
        return cls(
            segment_id=data.get("segment_id", ""),
            parent_decisions=data.get("parent_decisions", []),
            sibling_context=data.get("sibling_context", []),
            constraints=data.get("constraints", []),
            verification_requirements=data.get("verification_requirements", []),
            canary_phrase=data.get("canary_phrase", ""),
            origin_role=data.get("origin_role", ""),
            origin_session_id=data.get("origin_session_id", ""),
        )

    @classmethod
    def from_json(cls, json_str: str) -> "TaskManifest":
        """Deserialize from JSON string."""
        return cls.from_dict(json.loads(json_str))

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict())
