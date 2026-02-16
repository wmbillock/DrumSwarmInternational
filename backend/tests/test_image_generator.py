"""Tests for image_generator (ComfyUI connector)."""

import json
from unittest.mock import patch, MagicMock

import pytest

from backend.tools.image_generator import (
    ComfyUIConnector,
    load_workflow_template,
    get_connector,
)


class TestComfyUIConnectorAvailability:
    def test_not_available_when_server_down(self):
        connector = ComfyUIConnector(server_url="http://localhost:19999")
        assert connector.is_available() is False

    def test_availability_cached(self):
        connector = ComfyUIConnector()
        connector._available = True
        assert connector.is_available() is True

    @patch("urllib.request.urlopen")
    def test_available_when_server_responds(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        connector = ComfyUIConnector()
        connector._available = None  # Reset cache
        assert connector.is_available() is True


class TestComfyUIConnectorGenerate:
    def test_generate_returns_error_when_unavailable(self):
        connector = ComfyUIConnector()
        connector._available = False
        result = connector.generate("a beautiful sunset")
        assert result["success"] is False
        assert "not available" in result["error"]
        assert result["output_path"] is None

    def test_generate_native_returns_error_when_unavailable(self):
        connector = ComfyUIConnector()
        connector._available = False
        result = connector.generate_native({}, "a beautiful sunset")
        assert result["success"] is False
        assert "not available" in result["error"]


class TestBuildWorkflow:
    def test_workflow_structure(self):
        connector = ComfyUIConnector()
        connector._model_name = "test_model.safetensors"
        workflow = connector._build_workflow(
            prompt="a drum corps on field",
            negative_prompt="blurry",
            width=512,
            height=512,
            steps=20,
            cfg_scale=7.0,
            seed=42,
        )
        # KSampler node
        assert "3" in workflow
        assert workflow["3"]["class_type"] == "KSampler"
        assert workflow["3"]["inputs"]["seed"] == 42
        assert workflow["3"]["inputs"]["steps"] == 20

        # Checkpoint loader
        assert "4" in workflow
        assert workflow["4"]["inputs"]["ckpt_name"] == "test_model.safetensors"

        # Latent image dimensions
        assert "5" in workflow
        assert workflow["5"]["inputs"]["width"] == 512
        assert workflow["5"]["inputs"]["height"] == 512

        # Positive prompt
        assert "6" in workflow
        assert workflow["6"]["inputs"]["text"] == "a drum corps on field"

        # Negative prompt
        assert "7" in workflow
        assert workflow["7"]["inputs"]["text"] == "blurry"

        # VAE decoder and save
        assert "8" in workflow
        assert "9" in workflow

    def test_default_negative_prompt(self):
        connector = ComfyUIConnector()
        connector._model_name = "test.safetensors"
        workflow = connector._build_workflow("test", "", 512, 512, 20, 7.0, 1)
        assert "low quality" in workflow["7"]["inputs"]["text"]


class TestGenerateNative:
    def test_prompt_substitution(self):
        connector = ComfyUIConnector()
        connector._available = True

        workflow = {
            "1": {
                "class_type": "CLIPTextEncode",
                "inputs": {"text": "<PROMPT GOES HERE>"},
            },
            "2": {
                "class_type": "KSampler",
                "inputs": {"seed": 0, "steps": 20},
            },
        }

        with patch.object(connector, "_queue_and_wait", return_value={"success": True}) as mock_q:
            connector.generate_native(workflow, "my custom prompt", seed=42)
            called_workflow = mock_q.call_args[0][0]
            assert called_workflow["1"]["inputs"]["text"] == "my custom prompt"
            assert called_workflow["2"]["inputs"]["seed"] == 42


class TestLoadWorkflowTemplate:
    def test_load_existing_template(self, tmp_path, monkeypatch):
        workflows_dir = tmp_path / "comfyui_workflows"
        workflows_dir.mkdir()
        template = {"1": {"class_type": "TestNode", "inputs": {}}}
        (workflows_dir / "test_workflow.json").write_text(json.dumps(template))

        monkeypatch.setattr(
            "backend.tools.image_generator.CONFIG_DIR", tmp_path
        )
        result = load_workflow_template("test_workflow")
        assert result is not None
        assert result["1"]["class_type"] == "TestNode"

    def test_load_missing_template(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "backend.tools.image_generator.CONFIG_DIR", tmp_path
        )
        result = load_workflow_template("nonexistent")
        assert result is None

    def test_load_invalid_json(self, tmp_path, monkeypatch):
        workflows_dir = tmp_path / "comfyui_workflows"
        workflows_dir.mkdir()
        (workflows_dir / "bad.json").write_text("not json!!!")

        monkeypatch.setattr(
            "backend.tools.image_generator.CONFIG_DIR", tmp_path
        )
        result = load_workflow_template("bad")
        assert result is None


class TestGetConnector:
    def test_default_connector(self):
        connector = get_connector()
        assert isinstance(connector, ComfyUIConnector)
        assert "8188" in connector.server_url

    def test_custom_url_from_env(self, monkeypatch):
        monkeypatch.setenv("COMFYUI_URL", "http://gpu-server:9999")
        connector = get_connector()
        assert "gpu-server:9999" in connector.server_url


class TestGetModelName:
    @patch("urllib.request.urlopen")
    def test_auto_detect_sdxl(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "CheckpointLoaderSimple": {
                "input": {
                    "required": {
                        "ckpt_name": [
                            ["v1-5-pruned.safetensors", "sd_xl_base_1.0.safetensors"]
                        ]
                    }
                }
            }
        }).encode()
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        connector = ComfyUIConnector()
        name = connector._get_model_name()
        assert "sd_xl_base_1.0" in name

    def test_fallback_model_name(self):
        connector = ComfyUIConnector(server_url="http://localhost:19999")
        name = connector._get_model_name()
        assert "sd_xl_base_1.0" in name

    def test_model_name_cached(self):
        connector = ComfyUIConnector()
        connector._model_name = "cached_model.safetensors"
        assert connector._get_model_name() == "cached_model.safetensors"
