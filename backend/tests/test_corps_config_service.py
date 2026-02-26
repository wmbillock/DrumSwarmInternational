"""Tests for corps_config_service."""

from backend.services.corps_config_service import (
    get_config,
    get_or_create_config,
    update_config,
    list_configs,
    config_to_dict,
)
from backend.models.corps import Corps


def _seed_corps(db, corps_id="test-corps"):
    corps = Corps(id=corps_id, name="Test Corps")
    db.add(corps)
    db.commit()
    return corps_id


def test_get_config_returns_none_when_missing(db):
    _seed_corps(db)
    assert get_config(db, "test-corps") is None


def test_get_or_create_config_creates_default(db):
    _seed_corps(db)
    config = get_or_create_config(db, "test-corps")
    assert config.corps_id == "test-corps"
    assert config.llm_provider is None
    assert config.methodology is None


def test_get_or_create_config_returns_existing(db):
    _seed_corps(db)
    c1 = get_or_create_config(db, "test-corps")
    c1.llm_provider = "claude"
    db.commit()
    c2 = get_or_create_config(db, "test-corps")
    assert c2.llm_provider == "claude"


def test_update_config_sets_fields(db):
    _seed_corps(db)
    config = update_config(
        db,
        "test-corps",
        llm_provider="openai",
        methodology="tdd",
        architecture_style="microservices",
    )
    assert config.llm_provider == "openai"
    assert config.methodology == "tdd"
    assert config.architecture_style == "microservices"


def test_update_config_partial_update(db):
    _seed_corps(db)
    update_config(db, "test-corps", llm_provider="claude", methodology="xp")
    config = update_config(db, "test-corps", methodology="scrum")
    assert config.llm_provider == "claude"
    assert config.methodology == "scrum"


def test_update_config_with_extra_json(db):
    _seed_corps(db)
    config = update_config(
        db,
        "test-corps",
        extra={"temperature": 0.7, "max_tokens": 4096},
    )
    assert config.extra["temperature"] == 0.7
    assert config.extra["max_tokens"] == 4096


def test_list_configs_empty(db):
    assert list_configs(db) == []


def test_list_configs_returns_all(db):
    _seed_corps(db, "corps-a")
    _seed_corps(db, "corps-b")
    get_or_create_config(db, "corps-a")
    get_or_create_config(db, "corps-b")
    configs = list_configs(db)
    assert len(configs) == 2


def test_config_to_dict(db):
    _seed_corps(db)
    config = update_config(
        db,
        "test-corps",
        llm_provider="ollama",
        methodology="kanban",
    )
    d = config_to_dict(config)
    assert d["corps_id"] == "test-corps"
    assert d["llm_provider"] == "ollama"
    assert d["methodology"] == "kanban"
    assert d["architecture_style"] is None
    assert d["coding_style"] is None
    assert d["extra"] is None
