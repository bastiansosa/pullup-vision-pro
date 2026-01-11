"""
Configuracion de la aplicacion usando Pydantic Settings.
 Maneja variables de entorno de forma segura.
"""
import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    PROJECT_NAME: str = "PullUp Vision Pro"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    MAX_VIDEO_SIZE_MB: int = 50
    ALLOWED_VIDEO_TYPES: List[str] = ["mp4", "mov", "avi"]
    ALLOWED_ORIGINS: List[str] = ["*"]
    LOG_LEVEL: str = "INFO"
    UPLOAD_DIR: str = "uploads"
    PROCESSED_DIR: str = "processed"
    UMBRAL_ALTO: float = 0.20
    UMBRAL_BAJO: float = 0.30

    @property
    def max_video_size_bytes(self) -> int:
        return self.MAX_VIDEO_SIZE_MB * 1024 * 1024
    
    def get_upload_path(self) -> Path:
        return Path(__file__).parent.parent.parent / self.UPLOAD_DIR
    
    def get_processed_path(self) -> Path:
        return Path(__file__).parent.parent.parent / self.PROCESSED_DIR
    
    class Config:
        env_file = ".env"
        case_sensitive = False

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()