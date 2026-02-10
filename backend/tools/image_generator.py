"""ComfyUI connector — local image generation via GPU.

Connects to a locally running ComfyUI server to generate images
using Stable Diffusion models. Falls back gracefully if ComfyUI
is not running.
"""

import json
import logging
import os
import uuid
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

COMFYUI_URL = os.environ.get("COMFYUI_URL", "http://localhost:8188")
PROJECT_ROOT = Path(__file__).parent.parent.parent
CONFIG_DIR = Path(__file__).parent.parent / "config"
OUTPUT_DIR = PROJECT_ROOT / "generated_images"


class ComfyUIConnector:
    """Connector to a locally running ComfyUI server."""

    def __init__(self, server_url: str = COMFYUI_URL, timeout: int = 120):
        self.server_url = server_url.rstrip("/")
        self.timeout = timeout
        self._available: Optional[bool] = None

    def is_available(self) -> bool:
        """Check if ComfyUI server is reachable."""
        if self._available is not None:
            return self._available
        try:
            import urllib.request
            req = urllib.request.Request(f"{self.server_url}/system_stats", method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                self._available = resp.status == 200
        except Exception:
            self._available = False
            logger.debug("ComfyUI not available at %s", self.server_url)
        return self._available

    def generate(
        self,
        prompt: str,
        negative_prompt: str = "",
        width: int = 1024,
        height: int = 1024,
        steps: int = 20,
        cfg_scale: float = 7.0,
        seed: Optional[int] = None,
        output_filename: Optional[str] = None,
    ) -> dict:
        """Generate an image using ComfyUI's API.

        Returns dict with {success, output_path, error}.
        """
        if not self.is_available():
            return {
                "success": False,
                "output_path": None,
                "error": f"ComfyUI not available at {self.server_url}",
            }

        import urllib.request

        if seed is None:
            import random
            seed = random.randint(0, 2**32 - 1)

        # Build a minimal txt2img workflow
        workflow = self._build_workflow(
            prompt, negative_prompt, width, height, steps, cfg_scale, seed
        )

        try:
            # Queue the prompt
            payload = json.dumps({"prompt": workflow}).encode("utf-8")
            req = urllib.request.Request(
                f"{self.server_url}/prompt",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                result = json.loads(resp.read())
                prompt_id = result.get("prompt_id")

            if not prompt_id:
                return {
                    "success": False,
                    "output_path": None,
                    "error": "No prompt_id returned from ComfyUI",
                }

            # Poll for completion
            output_path = self._wait_for_result(prompt_id, output_filename)

            return {
                "success": True,
                "output_path": str(output_path) if output_path else None,
                "prompt_id": prompt_id,
                "error": None,
            }

        except Exception as e:
            return {
                "success": False,
                "output_path": None,
                "error": str(e),
            }

    def _build_workflow(
        self,
        prompt: str,
        negative_prompt: str,
        width: int,
        height: int,
        steps: int,
        cfg_scale: float,
        seed: int,
    ) -> dict:
        """Build a minimal ComfyUI workflow for txt2img."""
        return {
            "3": {
                "class_type": "KSampler",
                "inputs": {
                    "seed": seed,
                    "steps": steps,
                    "cfg": cfg_scale,
                    "sampler_name": "euler",
                    "scheduler": "normal",
                    "denoise": 1.0,
                    "model": ["4", 0],
                    "positive": ["6", 0],
                    "negative": ["7", 0],
                    "latent_image": ["5", 0],
                },
            },
            "4": {
                "class_type": "CheckpointLoaderSimple",
                "inputs": {
                    "ckpt_name": "sd_xl_base_1.0.safetensors",
                },
            },
            "5": {
                "class_type": "EmptyLatentImage",
                "inputs": {
                    "width": width,
                    "height": height,
                    "batch_size": 1,
                },
            },
            "6": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": prompt,
                    "clip": ["4", 1],
                },
            },
            "7": {
                "class_type": "CLIPTextEncode",
                "inputs": {
                    "text": negative_prompt or "low quality, blurry, watermark",
                    "clip": ["4", 1],
                },
            },
            "8": {
                "class_type": "VAEDecode",
                "inputs": {
                    "samples": ["3", 0],
                    "vae": ["4", 2],
                },
            },
            "9": {
                "class_type": "SaveImage",
                "inputs": {
                    "filename_prefix": "dci_swarm",
                    "images": ["8", 0],
                },
            },
        }

    def _wait_for_result(
        self,
        prompt_id: str,
        output_filename: Optional[str] = None,
    ) -> Optional[Path]:
        """Poll ComfyUI for completion and download the result."""
        import time
        import urllib.request

        deadline = time.time() + self.timeout

        while time.time() < deadline:
            try:
                req = urllib.request.Request(
                    f"{self.server_url}/history/{prompt_id}",
                    method="GET",
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    history = json.loads(resp.read())

                if prompt_id in history:
                    outputs = history[prompt_id].get("outputs", {})
                    for node_id, node_output in outputs.items():
                        images = node_output.get("images", [])
                        if images:
                            return self._download_image(
                                images[0], output_filename
                            )
            except Exception:
                pass

            time.sleep(2)

        return None

    def _download_image(
        self,
        image_info: dict,
        output_filename: Optional[str] = None,
    ) -> Optional[Path]:
        """Download a generated image from ComfyUI."""
        import urllib.request

        filename = image_info.get("filename", "output.png")
        subfolder = image_info.get("subfolder", "")
        img_type = image_info.get("type", "output")

        url = f"{self.server_url}/view?filename={filename}&subfolder={subfolder}&type={img_type}"

        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = OUTPUT_DIR / (output_filename or f"dci_{uuid.uuid4().hex[:8]}.png")

        try:
            urllib.request.urlretrieve(url, str(output_path))
            return output_path
        except Exception:
            logger.debug("Failed to download image", exc_info=True)
            return None


def load_workflow_template(workflow_name: str) -> Optional[dict]:
    """Load a workflow template from the config directory."""
    workflow_path = CONFIG_DIR / "comfyui_workflows" / f"{workflow_name}.json"
    if not workflow_path.exists():
        return None
    try:
        return json.loads(workflow_path.read_text())
    except Exception:
        logger.debug("Failed to load workflow template %s", workflow_name, exc_info=True)
        return None


def get_connector() -> ComfyUIConnector:
    """Get a ComfyUI connector instance."""
    return ComfyUIConnector(
        server_url=os.environ.get("COMFYUI_URL", COMFYUI_URL),
    )
