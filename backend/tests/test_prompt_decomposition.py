"""Tests that ED and PC prompts enforce minimal decomposition guidance.

These are string-based tests against ROLE_PROMPTS — they verify the prompt
text contains the right guidance to prevent over-decomposition by LLMs.
"""

import pytest
from backend.services.corps_service import ROLE_PROMPTS


class TestEDPromptDecomposition:
    """Executive Director prompt must guide toward minimal decomposition."""

    @property
    def prompt(self):
        return ROLE_PROMPTS["executive_director"]

    def test_no_fixed_minimum_movements(self):
        """ED should NOT prescribe a fixed minimum like 'typically 2-5'."""
        assert "typically 2-5" not in self.prompt

    def test_trivial_one_movement_allowed(self):
        """ED prompt must explicitly allow 1 movement for trivial tasks."""
        assert "1" in self.prompt
        # Should mention trivial/simple tasks can be 1 movement
        lower = self.prompt.lower()
        assert "trivial" in lower or "simple" in lower

    def test_do_not_over_decompose(self):
        """ED prompt must contain anti-over-decomposition guidance."""
        lower = self.prompt.lower()
        assert "over-decompose" in lower or "over decompose" in lower

    def test_moderate_two_to_three(self):
        """ED prompt should suggest 2-3 for moderate tasks."""
        assert "2-3" in self.prompt or "2–3" in self.prompt


class TestPCPromptDecomposition:
    """Program Coordinator prompt must allow minimal segment hierarchy."""

    @property
    def prompt(self):
        return ROLE_PROMPTS["program_coordinator"]

    def test_small_movements_one_leaf(self):
        """PC prompt must allow small movements to have just 1 leaf segment."""
        lower = self.prompt.lower()
        assert "1 leaf" in lower or "single leaf" in lower or "just 1" in lower

    def test_do_not_over_decompose(self):
        """PC prompt must contain anti-over-decomposition guidance."""
        lower = self.prompt.lower()
        assert "over-decompose" in lower or "over decompose" in lower or "minimum" in lower

    def test_no_mandatory_set_per_movement(self):
        """PC should NOT force creating a SET for every movement unconditionally."""
        # The old prompt said "For each movement, create SET segments"
        # New prompt should allow skipping the set layer for simple movements
        assert "For each movement, create SET" not in self.prompt
