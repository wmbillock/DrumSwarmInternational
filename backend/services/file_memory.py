"""File-based memory — human-inspectable, version-controlled agent state.

Stores agent profiles, decision logs, and session summaries as plain files.
This complements the SQL-based memory with easily browsable/editable records.
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_MEMORY_PATH = "memory_store"


class FileMemory:
    """File-based memory for human-inspectable agent state."""

    def __init__(self, base_path: str = DEFAULT_MEMORY_PATH):
        self.base_path = Path(base_path)

    def _agent_dir(self, agent_identity: str) -> Path:
        # Sanitize identity for filesystem
        safe_name = agent_identity.replace(" ", "_").replace("/", "_")[:80]
        return self.base_path / "agents" / safe_name

    def save_profile(self, agent_identity: str, profile: dict[str, Any]) -> Path:
        """Save agent profile to JSON."""
        path = self._agent_dir(agent_identity) / "profile.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(profile, f, indent=2)
        return path

    def load_profile(self, agent_identity: str) -> dict[str, Any]:
        """Load agent profile from JSON."""
        path = self._agent_dir(agent_identity) / "profile.json"
        if not path.exists():
            return {}
        with open(path) as f:
            return json.load(f)

    def save_session_summary(
        self, agent_identity: str, session_id: str, summary: str
    ) -> Path:
        """Save human-readable session summary as markdown."""
        path = self._agent_dir(agent_identity) / "summaries" / f"{session_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            f.write(summary)
        return path

    def save_decision(
        self, agent_identity: str, decision_id: str, decision: dict[str, Any]
    ) -> Path:
        """Save a decision record as JSON."""
        path = self._agent_dir(agent_identity) / "decisions" / f"{decision_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(decision, f, indent=2)
        return path

    def list_summaries(self, agent_identity: str) -> list[str]:
        """List all session summary files for an agent."""
        summaries_dir = self._agent_dir(agent_identity) / "summaries"
        if not summaries_dir.exists():
            return []
        return sorted(p.stem for p in summaries_dir.glob("*.md"))

    def list_decisions(self, agent_identity: str) -> list[str]:
        """List all decision files for an agent."""
        decisions_dir = self._agent_dir(agent_identity) / "decisions"
        if not decisions_dir.exists():
            return []
        return sorted(p.stem for p in decisions_dir.glob("*.json"))
