"""Tests for the art director service."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.services.art_director import (
    WORKFLOWS_DIR,
    classify,
    generate,
    list_categories,
    _DEFAULT_CATEGORY,
)


# ── classify() tests ──────────────────────────────────────────────────

class TestClassify:
    """Test keyword-based category classification."""

    def test_web_icons_keywords(self):
        assert classify("a settings icon for the toolbar") == "web_icons"
        assert classify("create a nav button") == "web_icons"
        assert classify("UI element for the menu") == "web_icons"

    def test_pixel_art_8bit(self):
        assert classify("retro spaceship NES-style") == "pixel_art_8bit"
        assert classify("8-bit warrior") == "pixel_art_8bit"
        assert classify("pixel knight") == "pixel_art_8bit"

    def test_pixel_art_16bit(self):
        assert classify("16-bit castle scene") == "pixel_art_16bit"
        assert classify("SNES warrior") == "pixel_art_16bit"
        assert classify("genesis style background") == "pixel_art_16bit"

    def test_game_art_2d(self):
        assert classify("2d game forest level") == "game_art_2d"
        assert classify("platformer character") == "game_art_2d"
        assert classify("sprite sheet for enemies") == "game_art_2d"

    def test_photo_realistic(self):
        assert classify("realistic portrait of a CEO") == "photo_realistic"
        assert classify("photo of a mountain landscape") == "photo_realistic"
        assert classify("human face closeup") == "photo_realistic"

    def test_stylized_icon(self):
        assert classify("heraldry shield with eagle") == "stylized_icon"
        assert classify("military crest") == "stylized_icon"
        assert classify("emblem for the team") == "stylized_icon"
        assert classify("badge design") == "stylized_icon"

    def test_corporate_logo(self):
        assert classify("corporate logo for tech startup") == "corporate_logo"
        assert classify("brand identity mark") == "corporate_logo"
        assert classify("wordmark design") == "corporate_logo"

    def test_cartoon_animation(self):
        assert classify("cartoon cat character") == "cartoon_animation"
        assert classify("anime warrior girl") == "cartoon_animation"
        assert classify("animated explosion effect") == "cartoon_animation"

    def test_show_poster(self):
        assert classify("concert poster for summer tour") == "show_poster"
        assert classify("event banner image") == "show_poster"
        assert classify("promotional flyer") == "show_poster"

    def test_character_portrait(self):
        assert classify("character design for the hero") == "character_portrait"
        assert classify("avatar for user profile") == "character_portrait"
        assert classify("agent portrait illustration") == "character_portrait"

    def test_default_fallback(self):
        assert classify("a dragon breathing fire") == _DEFAULT_CATEGORY
        assert classify("something abstract and weird") == _DEFAULT_CATEGORY

    def test_case_insensitive(self):
        assert classify("PIXEL ART of a KNIGHT") == "pixel_art_8bit"
        assert classify("CARTOON explosion") == "cartoon_animation"

    def test_first_match_wins(self):
        # "pixel" matches 8bit before "sprite" matches game_art_2d
        assert classify("pixel sprite character") == "pixel_art_8bit"
        # "16-bit" matches 16bit before "pixel" matches 8bit
        assert classify("16-bit pixel landscape") == "pixel_art_16bit"


# ── Workflow template loading ──────────────────────────────────────────

EXPECTED_CATEGORIES = [
    "cartoon_animation",
    "character_portrait",
    "corporate_logo",
    "game_art_2d",
    "photo_realistic",
    "pixel_art_16bit",
    "pixel_art_8bit",
    "show_poster",
    "stylized_icon",
    "web_icons",
]


class TestWorkflowTemplates:
    """Test that all workflow JSON files load and parse correctly."""

    def test_all_expected_templates_exist(self):
        for cat in EXPECTED_CATEGORIES:
            path = WORKFLOWS_DIR / f"{cat}.json"
            assert path.exists(), f"Missing workflow template: {cat}.json"

    @pytest.mark.parametrize("category", EXPECTED_CATEGORIES)
    def test_template_has_required_fields(self, category):
        path = WORKFLOWS_DIR / f"{category}.json"
        data = json.loads(path.read_text())
        assert "description" in data
        assert "prompt_template" in data
        assert "negative_prompt" in data
        assert "width" in data
        assert "height" in data
        assert "steps" in data
        assert "cfg_scale" in data

    @pytest.mark.parametrize("category", EXPECTED_CATEGORIES)
    def test_template_prompt_has_description_placeholder(self, category):
        path = WORKFLOWS_DIR / f"{category}.json"
        data = json.loads(path.read_text())
        assert "{description}" in data["prompt_template"]

    @pytest.mark.parametrize("category", EXPECTED_CATEGORIES)
    def test_template_dimensions_are_reasonable(self, category):
        path = WORKFLOWS_DIR / f"{category}.json"
        data = json.loads(path.read_text())
        assert 256 <= data["width"] <= 2048
        assert 256 <= data["height"] <= 2048

    @pytest.mark.parametrize("category", EXPECTED_CATEGORIES)
    def test_template_steps_and_cfg_are_reasonable(self, category):
        path = WORKFLOWS_DIR / f"{category}.json"
        data = json.loads(path.read_text())
        assert 1 <= data["steps"] <= 100
        assert 1.0 <= data["cfg_scale"] <= 30.0


# ── list_categories() ──────────────────────────────────────────────────

class TestListCategories:
    """Test the list_categories function."""

    def test_returns_all_categories(self):
        # Reset the cached list
        import backend.services.art_director as ad
        ad._ALL_CATEGORIES = None

        cats = list_categories()
        cat_names = [c["category"] for c in cats]
        for expected in EXPECTED_CATEGORIES:
            assert expected in cat_names, f"Missing category: {expected}"

    def test_category_entries_have_description(self):
        import backend.services.art_director as ad
        ad._ALL_CATEGORIES = None

        cats = list_categories()
        for cat in cats:
            if cat["category"] in EXPECTED_CATEGORIES:
                assert cat["description"], f"Empty description for {cat['category']}"


# ── generate() ─────────────────────────────────────────────────────────

class TestGenerate:
    """Test the generate() function."""

    @patch("backend.services.image_service.generate_from_workflow")
    def test_generate_with_explicit_category(self, mock_gen):
        mock_gen.return_value = {
            "success": True,
            "output_path": "/tmp/test.png",
            "workflow_used": "pixel_art_8bit",
        }
        result = generate("a knight", category="pixel_art_8bit", seed=42)

        assert result["success"] is True
        assert result["category"] == "pixel_art_8bit"
        assert result["prompt_used"] is not None
        assert "knight" in result["prompt_used"]

        mock_gen.assert_called_once()
        call_kwargs = mock_gen.call_args[1]
        assert call_kwargs["workflow_name"] == "pixel_art_8bit"
        assert call_kwargs["seed"] == 42

    @patch("backend.services.image_service.generate_from_workflow")
    def test_generate_auto_classifies(self, mock_gen):
        mock_gen.return_value = {
            "success": True,
            "output_path": "/tmp/test.png",
            "workflow_used": "cartoon_animation",
        }
        result = generate("cartoon cat playing drums")

        assert result["category"] == "cartoon_animation"
        assert "cartoon" in result["prompt_used"].lower()

    def test_generate_unknown_category_returns_error(self):
        result = generate("test", category="nonexistent_style")
        assert result["success"] is False
        assert "Unknown category" in result["error"]
        assert result["category"] == "nonexistent_style"

    @patch("backend.services.image_service.generate_from_workflow")
    def test_generate_comfyui_offline_returns_error(self, mock_gen):
        mock_gen.return_value = {
            "success": False,
            "output_path": None,
            "error": "ComfyUI not available",
            "workflow_used": "game_art_2d",
        }
        result = generate("a dragon")
        assert result["success"] is False
        assert result["category"] == _DEFAULT_CATEGORY

    @patch("backend.services.image_service.generate_from_workflow")
    def test_generate_prompt_substitution(self, mock_gen):
        mock_gen.return_value = {
            "success": True,
            "output_path": "/tmp/test.png",
            "workflow_used": "web_icons",
        }
        result = generate("settings gear icon", category="web_icons")

        # The prompt_used should contain both the style prefix and description
        assert "settings gear icon" in result["prompt_used"]
        assert "web icon" in result["prompt_used"].lower() or "icon" in result["prompt_used"].lower()


# ── API endpoint tests ─────────────────────────────────────────────────

class TestImagesAPI:
    """Test the images API endpoints."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from backend.api.v1.images import router
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    def test_get_categories(self, client):
        import backend.services.art_director as ad
        ad._ALL_CATEGORIES = None

        resp = client.get("/api/v1/images/categories")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 10
        cat_names = [c["category"] for c in data]
        assert "pixel_art_8bit" in cat_names
        assert "web_icons" in cat_names

    @patch("backend.services.image_service.generate_from_workflow")
    def test_post_generate_art(self, mock_gen, client):
        mock_gen.return_value = {
            "success": True,
            "output_path": "/tmp/test.png",
            "workflow_used": "pixel_art_8bit",
        }
        resp = client.post(
            "/api/v1/images/generate/art",
            json={"description": "a pixel knight", "category": "pixel_art_8bit"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert data["category"] == "pixel_art_8bit"

    @patch("backend.services.image_service.generate_from_workflow")
    def test_post_generate_art_auto_classify(self, mock_gen, client):
        mock_gen.return_value = {
            "success": True,
            "output_path": "/tmp/test.png",
            "workflow_used": "cartoon_animation",
        }
        resp = client.post(
            "/api/v1/images/generate/art",
            json={"description": "cartoon dragon"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["category"] == "cartoon_animation"

    def test_post_generate_art_unknown_category(self, client):
        resp = client.post(
            "/api/v1/images/generate/art",
            json={"description": "test", "category": "does_not_exist"},
        )
        assert resp.status_code == 503
