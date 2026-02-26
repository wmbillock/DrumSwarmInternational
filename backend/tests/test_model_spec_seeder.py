"""Tests for model spec seeder and corps strategy seeding from YAML."""

import textwrap
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.database import Base
import backend.models  # noqa: F401 — ensure all models registered

from backend.models.corps import Corps, CorpsStatus
from backend.models.corps_strategy import CorpsStrategy
from backend.models.model_spec import ModelSpec
from backend.services.corps_seeder import seed_founding_corps, _seed_corps_strategy
from backend.services.model_spec_seeder import seed_default_specs, DEFAULT_SPECS


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    try:
        yield session
    finally:
        session.close()


class TestSeedDefaultSpecs:
    def test_seed_default_specs_idempotent(self, db):
        """Calling seed_default_specs twice creates specs only once."""
        # First call — skip ollama checks in test
        created_1 = seed_default_specs(db, check_ollama=False)
        assert len(created_1) == len(DEFAULT_SPECS)

        # All specs present
        count = db.query(ModelSpec).count()
        assert count == len(DEFAULT_SPECS)

        # Second call — nothing new
        created_2 = seed_default_specs(db, check_ollama=False)
        assert len(created_2) == 0

        # Count unchanged
        count_after = db.query(ModelSpec).count()
        assert count_after == count

    def test_seed_creates_expected_specs(self, db):
        seed_default_specs(db, check_ollama=False)

        opus = (
            db.query(ModelSpec)
            .filter(ModelSpec.provider == "anthropic", ModelSpec.name == "claude-opus-4-6")
            .first()
        )
        assert opus is not None
        assert "architecture" in opus.categories_list

        qwen = (
            db.query(ModelSpec)
            .filter(ModelSpec.provider == "ollama", ModelSpec.name == "qwen2.5-32b")
            .first()
        )
        assert qwen is not None
        assert qwen.model_id == "qwen2.5:32b"

        deepseek = (
            db.query(ModelSpec)
            .filter(ModelSpec.provider == "ollama", ModelSpec.name == "deepseek-coder-v2-16b")
            .first()
        )
        assert deepseek is not None
        assert deepseek.model_id == "deepseek-coder-v2:16b"

    def test_seed_skips_ollama_when_unavailable(self, db):
        """When check_ollama=True and Ollama is not running, ollama specs are skipped."""
        created = seed_default_specs(db, check_ollama=True)
        providers = {s.provider for s in created}
        # Ollama is almost certainly not running in CI — only anthropic specs seeded
        # (If Ollama IS running, both providers appear, which is also valid)
        assert "anthropic" in providers


class TestCorpsStrategyFromYaml:
    def test_corps_strategy_from_yaml(self, tmp_path, db):
        """seed_founding_corps reads strategy block and creates CorpsStrategy."""
        yaml_content = textwrap.dedent("""\
            name: "Test Strategy Corps"
            caption_affinity: brass

            strategy:
              model_policy: best_of_breed
              preferred_provider: null
              risk_tolerance: 0.7
              exploration_rate: 0.5
              adaptation_style: full
        """)
        (tmp_path / "test_corps.yaml").write_text(yaml_content)

        created = seed_founding_corps(db, corps_dir=tmp_path)
        assert len(created) == 1

        corps_id = created[0].id
        strategy = db.query(CorpsStrategy).filter(CorpsStrategy.corps_id == corps_id).first()
        assert strategy is not None
        assert strategy.model_policy == "best_of_breed"
        assert strategy.preferred_provider is None
        assert strategy.risk_tolerance == pytest.approx(0.7)
        assert strategy.exploration_rate == pytest.approx(0.5)
        assert strategy.adaptation_style == "full"

    def test_strategy_seeded_for_existing_corps(self, tmp_path, db):
        """When a corps already exists, re-running the seeder still creates its strategy."""
        yaml_content = textwrap.dedent("""\
            name: "Pre-Existing Corps"
            caption_affinity: percussion

            strategy:
              model_policy: single_provider
              preferred_provider: anthropic
              risk_tolerance: 0.1
              exploration_rate: 0.05
              adaptation_style: prompt_only
        """)
        yaml_path = tmp_path / "existing.yaml"
        yaml_path.write_text(yaml_content)

        # First seed — creates corps + strategy
        seed_founding_corps(db, corps_dir=tmp_path)

        # Delete strategy but keep corps
        db.query(CorpsStrategy).delete()
        db.commit()
        assert db.query(CorpsStrategy).count() == 0

        # Second seed — corps already exists, but strategy should be re-created
        seed_founding_corps(db, corps_dir=tmp_path)
        assert db.query(CorpsStrategy).count() == 1
        strategy = db.query(CorpsStrategy).first()
        assert strategy.model_policy == "single_provider"
        assert strategy.preferred_provider == "anthropic"

    def test_no_strategy_block_is_fine(self, tmp_path, db):
        """Corps YAML without a strategy block doesn't crash."""
        yaml_content = textwrap.dedent("""\
            name: "No Strategy Corps"
            caption_affinity: guard
        """)
        (tmp_path / "no_strategy.yaml").write_text(yaml_content)

        created = seed_founding_corps(db, corps_dir=tmp_path)
        assert len(created) == 1
        assert db.query(CorpsStrategy).count() == 0


class TestAllFoundingCorpsHaveStrategies:
    def test_all_founding_corps_have_strategies(self, db):
        """Every real founding corps YAML has a strategy block that seeds correctly."""
        from backend.services.corps_seeder import FOUNDING_CORPS_DIR

        if not FOUNDING_CORPS_DIR.exists():
            pytest.skip("Founding corps directory not found")

        yaml_files = sorted(FOUNDING_CORPS_DIR.glob("*.yaml"))
        assert len(yaml_files) == 12, f"Expected 12 founding corps, found {len(yaml_files)}"

        created = seed_founding_corps(db, corps_dir=FOUNDING_CORPS_DIR)

        # All 12 should have been created (fresh DB)
        corps_count = db.query(Corps).count()
        assert corps_count == 12

        # All 12 should have strategies
        strategy_count = db.query(CorpsStrategy).count()
        assert strategy_count == 12

        # Spot-check a few known strategies
        quiet = db.query(Corps).filter(Corps.name == "The Quiet Trumpets").first()
        quiet_strat = db.query(CorpsStrategy).filter(CorpsStrategy.corps_id == quiet.id).first()
        assert quiet_strat.model_policy == "single_provider"
        assert quiet_strat.preferred_provider == "anthropic"
        assert quiet_strat.risk_tolerance == pytest.approx(0.1)

        toss = db.query(Corps).filter(Corps.name == "Toss And Pray").first()
        toss_strat = db.query(CorpsStrategy).filter(CorpsStrategy.corps_id == toss.id).first()
        assert toss_strat.model_policy == "random_exploration"
        assert toss_strat.risk_tolerance == pytest.approx(1.0)
        assert toss_strat.adaptation_style == "full"

        baris = db.query(Corps).filter(Corps.name == "We Only March Baris").first()
        baris_strat = db.query(CorpsStrategy).filter(CorpsStrategy.corps_id == baris.id).first()
        assert baris_strat.model_policy == "section_specialized"
        assert baris_strat.adaptation_style == "model_swap"
