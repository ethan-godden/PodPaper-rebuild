"""Runtime settings. Values come from PODPAPER_* environment variables or defaults."""

from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="PODPAPER_", extra="ignore")

    data_dir: Path = Path("data")

    render_dpi: int = 200
    max_pages: int = 60

    layout_model: str = "PaddlePaddle/PP-DocLayoutV3_safetensors"
    layout_threshold: float = 0.5
    device: str = "mps"

    ollama_url: str = "http://127.0.0.1:11434"
    ocr_model: str = "glm-ocr"
    llm_model: str = "qwen3.8:27b-q4_K_M"
    ollama_num_ctx: int = 8192

    tts_model: str = "hexgrad/Kokoro-82M"
    tts_voice: str = "af_heart"
    tts_device: str = "cpu"
    tts_speed: float = 1.0

    @property
    def blob_dir(self) -> Path:
        return self.data_dir / "blobs"

    @property
    def docs_dir(self) -> Path:
        return self.data_dir / "docs"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "podpaper.sqlite"
