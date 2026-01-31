"""Failure fingerprinting — prevent agents from retrying identical broken approaches.

Hashes (tool_name, args, error) into stable keys. After repeated identical failures,
injects guidance to try a different approach instead of re-executing.
"""

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FailureFingerprint:
    """A stable hash of a failed tool invocation."""
    tool_name: str
    args: dict
    error: str
    _hash: str = ""

    def __post_init__(self):
        if not self._hash:
            self._hash = self._compute_hash()

    def _compute_hash(self) -> str:
        canonical = json.dumps({
            "tool": self.tool_name,
            "args": self.args,
            "error": self.error,
        }, sort_keys=True)
        return hashlib.sha256(canonical.encode()).hexdigest()[:16]

    @property
    def key(self) -> str:
        return self._hash


class FailureRegistry:
    """Per-session registry tracking repeated failures."""

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries
        self._counts: dict[str, int] = {}
        self._fingerprints: dict[str, FailureFingerprint] = {}

    def record_failure(self, fingerprint: FailureFingerprint) -> int:
        """Record a failure and return the current count for this fingerprint."""
        key = fingerprint.key
        self._counts[key] = self._counts.get(key, 0) + 1
        self._fingerprints[key] = fingerprint
        return self._counts[key]

    def should_block(self, fingerprint: FailureFingerprint) -> bool:
        """Check if this failure has been seen too many times."""
        return self._counts.get(fingerprint.key, 0) >= self.max_retries

    def get_guidance(self, fingerprint: FailureFingerprint) -> Optional[str]:
        """Return guidance message if this failure should be blocked."""
        if not self.should_block(fingerprint):
            return None
        count = self._counts.get(fingerprint.key, 0)
        return (
            f"FAILURE PATTERN DETECTED: The tool '{fingerprint.tool_name}' has failed "
            f"{count} times with the same error: {fingerprint.error}\n"
            f"You MUST try a different approach. Do NOT retry with the same arguments. "
            f"Consider: using different parameters, a different tool, or breaking the task differently."
        )

    def get_all_fingerprints(self) -> list[dict]:
        """Return all recorded fingerprints for persistence."""
        results = []
        for key, fp in self._fingerprints.items():
            results.append({
                "key": key,
                "tool_name": fp.tool_name,
                "args": fp.args,
                "error": fp.error,
                "count": self._counts.get(key, 0),
            })
        return results

    def load_fingerprints(self, data: list[dict]) -> None:
        """Load previously persisted fingerprints."""
        for entry in data:
            fp = FailureFingerprint(
                tool_name=entry["tool_name"],
                args=entry["args"],
                error=entry["error"],
            )
            self._fingerprints[fp.key] = fp
            self._counts[fp.key] = entry.get("count", 0)
