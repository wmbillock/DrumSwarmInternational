"""Tests for offseason proposals file persistence and round-tripping."""

import pytest
from pathlib import Path

from backend.services.offseason_proposals import (
    Proposal,
    create_proposals_file,
    load_proposals,
)
from backend.services.lifecycle_transitions import SeasonPhase, MutationBlockedError


@pytest.fixture
def temp_base(tmp_path: Path) -> Path:
    """Temporary base directory for seasons."""
    return tmp_path


def test_proposals_file_round_trip(temp_base: Path):
    """Create proposals file, read it back, content matches."""
    season_id = "test-season"
    proposals = [
        Proposal(
            proposal_type="state_change",
            corps_id="bluecoats",
            description="Promote to contending",
            changes={"new_state": "contending"},
        ),
        Proposal(
            proposal_type="retirement",
            corps_id="oldcorps",
            description="Retire corps",
            changes={},
        ),
    ]

    path = create_proposals_file(
        temp_base, season_id, proposals, phase=SeasonPhase.OFFSEASON
    )
    assert path.exists()

    loaded = load_proposals(temp_base, season_id)
    assert len(loaded) == 2

    assert loaded[0].proposal_type == "state_change"
    assert loaded[0].corps_id == "bluecoats"
    assert loaded[0].description == "Promote to contending"
    assert loaded[0].changes == {"new_state": "contending"}

    assert loaded[1].proposal_type == "retirement"
    assert loaded[1].corps_id == "oldcorps"
    assert loaded[1].description == "Retire corps"
    assert loaded[1].changes == {}


def test_proposals_file_location(temp_base: Path):
    """File created at seasons/<id>/offseason/proposals.md."""
    season_id = "s2025"
    proposals = [
        Proposal(
            proposal_type="state_change",
            corps_id="bluecoats",
            description="Test proposal",
            changes={"new_state": "active"},
        )
    ]

    path = create_proposals_file(
        temp_base, season_id, proposals, phase=SeasonPhase.OFFSEASON
    )

    expected = temp_base / "seasons" / season_id / "offseason" / "proposals.md"
    assert path == expected
    assert expected.exists()


def test_missing_proposals_raises(temp_base: Path):
    """Loading from nonexistent season raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_proposals(temp_base, "nonexistent-season")


def test_create_proposals_file_requires_offseason_phase(temp_base: Path):
    """Creating proposals file in non-offseason phase raises MutationBlockedError."""
    proposals = [
        Proposal(
            proposal_type="state_change",
            corps_id="bluecoats",
            description="Test",
            changes={"new_state": "active"},
        )
    ]

    with pytest.raises(MutationBlockedError):
        create_proposals_file(
            temp_base, "test-season", proposals, phase=SeasonPhase.SHOW
        )

    with pytest.raises(MutationBlockedError):
        create_proposals_file(
            temp_base, "test-season", proposals, phase=SeasonPhase.SCORING
        )


def test_proposals_file_markdown_format(temp_base: Path):
    """Verify proposals file is valid markdown with YAML code blocks."""
    season_id = "format-test"
    proposals = [
        Proposal(
            proposal_type="state_change",
            corps_id="cavaliers",
            description="Update state",
            changes={"new_state": "contending"},
        )
    ]

    path = create_proposals_file(
        temp_base, season_id, proposals, phase=SeasonPhase.OFFSEASON
    )
    content = path.read_text()

    # Check markdown structure
    assert "# Offseason Proposals" in content
    assert "## Proposal 1: Update state" in content
    assert "```yaml" in content
    assert "```" in content

    # Check YAML content is present
    assert "proposal_type: state_change" in content
    assert "corps_id: cavaliers" in content
    assert "description: Update state" in content


def test_empty_proposals_creates_valid_file(temp_base: Path):
    """Creating file with empty proposals list produces valid file."""
    season_id = "empty-test"
    proposals = []

    path = create_proposals_file(
        temp_base, season_id, proposals, phase=SeasonPhase.OFFSEASON
    )
    assert path.exists()

    content = path.read_text()
    assert "# Offseason Proposals" in content

    loaded = load_proposals(temp_base, season_id)
    assert loaded == []


def test_multiple_proposals_preserved(temp_base: Path):
    """Multiple proposals are all preserved in order."""
    season_id = "multi-test"
    proposals = [
        Proposal(
            proposal_type="state_change",
            corps_id="corps1",
            description="First proposal",
            changes={"new_state": "active"},
        ),
        Proposal(
            proposal_type="roster_change",
            corps_id="corps2",
            description="Second proposal",
            changes={"assignments": [{"agent_id": "a1", "role": "drum_major"}]},
        ),
        Proposal(
            proposal_type="retirement",
            corps_id="corps3",
            description="Third proposal",
            changes={},
        ),
    ]

    create_proposals_file(
        temp_base, season_id, proposals, phase=SeasonPhase.OFFSEASON
    )
    loaded = load_proposals(temp_base, season_id)

    assert len(loaded) == 3
    assert loaded[0].corps_id == "corps1"
    assert loaded[1].corps_id == "corps2"
    assert loaded[2].corps_id == "corps3"
    assert loaded[0].description == "First proposal"
    assert loaded[1].description == "Second proposal"
    assert loaded[2].description == "Third proposal"
