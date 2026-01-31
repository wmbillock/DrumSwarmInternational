"""Preservation smoke tests — assert core system invariants."""

from backend.services.message_service import ROLE_HIERARCHY


class TestRoleHierarchyInvariants:
    """Verify ROLE_HIERARCHY structure and boundary enforcement."""

    CANONICAL_LEADERSHIP = {
        "executive_director",
        "program_coordinator",
        "brass_caption_head",
        "percussion_caption_head",
        "guard_caption_head",
        "visual_caption_head",
    }

    def test_hierarchy_exists_and_nonempty(self):
        assert isinstance(ROLE_HIERARCHY, dict)
        assert len(ROLE_HIERARCHY) > 0

    def test_canonical_roles_present(self):
        for role in self.CANONICAL_LEADERSHIP:
            assert role in ROLE_HIERARCHY, f"Missing canonical role: {role}"

    def test_performer_can_only_reach_section_leader(self):
        targets = ROLE_HIERARCHY["performer"]
        assert targets == {"section_leader"}, (
            f"Performer should only message section_leader, got {targets}"
        )

    def test_performer_not_in_ed_targets(self):
        ed_targets = ROLE_HIERARCHY["executive_director"]
        assert "performer" not in ed_targets, (
            "ED should not directly message performers"
        )

    def test_brass_tech_cannot_reach_guard_caption_head(self):
        brass_tech_targets = ROLE_HIERARCHY["brass_tech"]
        assert "guard_caption_head" not in brass_tech_targets, (
            "Brass tech must not cross caption boundaries to guard caption head"
        )

    def test_hierarchy_enforces_boundaries(self):
        """Techs should only reach their own caption head, not other caption heads."""
        tech_caption_map = {
            "brass_tech": "brass_caption_head",
            "percussion_tech": "percussion_caption_head",
            "guard_tech": "guard_caption_head",
            "visual_tech": "visual_caption_head",
        }
        all_caption_heads = set(tech_caption_map.values())

        for tech, own_head in tech_caption_map.items():
            targets = ROLE_HIERARCHY[tech]
            foreign_heads = all_caption_heads - {own_head}
            for foreign in foreign_heads:
                assert foreign not in targets, (
                    f"{tech} should not reach {foreign}"
                )
