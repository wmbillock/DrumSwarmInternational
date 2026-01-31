"""Tests for task manifest context propagation."""

from backend.services.task_manifest import TaskManifest


class TestTaskManifest:
    def test_basic_creation(self):
        m = TaskManifest(coordinate_id="c1")
        assert m.coordinate_id == "c1"
        assert m.parent_decisions == []

    def test_add_decision(self):
        m = TaskManifest(coordinate_id="c1")
        m.add_decision("Split into 3 movements")
        assert len(m.parent_decisions) == 1

    def test_add_sibling(self):
        m = TaskManifest(coordinate_id="c1")
        m.add_sibling("c2", "Movement 2", "completed")
        assert len(m.sibling_context) == 1
        assert m.sibling_context[0]["title"] == "Movement 2"

    def test_add_constraint(self):
        m = TaskManifest(coordinate_id="c1")
        m.add_constraint("Must include unit tests")
        assert "Must include unit tests" in m.constraints

    def test_context_string(self):
        m = TaskManifest(coordinate_id="c1")
        m.add_decision("Use brass section")
        m.add_constraint("Keep under 100 lines")
        m.canary_phrase = "VERIFY42"
        ctx = m.to_context_string()
        assert "PARENT DECISIONS" in ctx
        assert "CONSTRAINTS" in ctx
        assert "VERIFY42" in ctx

    def test_empty_context_string(self):
        m = TaskManifest(coordinate_id="c1")
        assert m.to_context_string() == ""

    def test_serialization_roundtrip(self):
        m = TaskManifest(
            coordinate_id="c1",
            parent_decisions=["d1"],
            constraints=["con1"],
            canary_phrase="test",
            origin_role="ed",
        )
        d = m.to_dict()
        m2 = TaskManifest.from_dict(d)
        assert m2.coordinate_id == "c1"
        assert m2.parent_decisions == ["d1"]
        assert m2.canary_phrase == "test"

    def test_json_roundtrip(self):
        m = TaskManifest(coordinate_id="c1", constraints=["x"])
        j = m.to_json()
        m2 = TaskManifest.from_json(j)
        assert m2.coordinate_id == "c1"
        assert m2.constraints == ["x"]
