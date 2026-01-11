"""
Configuracion de la aplicacion usando Pydantic Settings.
 Maneja variables de entorno de forma segura.
"""
# Estas son importaciones basicas de Python
# os: para manejar rutas de archivos
# functools.lru_cache: para guardar en cache y no crear varias veces lo mismo
# typing: para definir tipos de datos
# pydantic_settings: libreria que facilita manejar configuraciones
# pathlib: para trabajar con rutas de archivos de forma moderna
import os
from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings
from pathlib import Path


# Esta clase va a contener toda la configuracion de nuestra app
# Extiende de BaseSettings que es de pydantic
# Esto nos permite leer variables de entorno facilmente
class Settings(BaseSettings):
    """
    Configuracion global de la aplicacion.
    Lee las variables de entorno automaticamente.
    """
    # Informacion del proyecto
    # Estos son los valores por defecto si no hay variables de entorno
    PROJECT_NAME: str = "PullUp Vision Pro"
    VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Configuracion del servidor
    HOST: str = "0.0.0.0"  # 0.0.0.0 significa que se puede acceder desde cualquier IP
    PORT: int = 8000       # Puerto donde correra el servidor
    
    # Limites
    MAX_VIDEO_SIZE_MB: int = 50  # Tamaño maximo de video en MB
    ALLOWED_VIDEO_TYPES: List[str] = ["mp4", "mov", "avi"]  # Tipos permitidos
    
    # CORS - esto es para seguridad, define quienes pueden acceder a nuestra API
    ALLOWED_ORIGINS: List[str] = ["http://localhost:8000"]
    
    # Logging - nivel de logs que queremos ver
    LOG_LEVEL: str = "INFO"
    
    # Rutas donde se guardaran los archivos
    UPLOAD_DIR: str = "uploads"
    PROCESSED_DIR: str = "processed"
    
    # Esta es una propiedad, como un metodo pero se usa como variable
    # Convierte MB a bytes porque Python trabaja con bytes
    @property
    def max_video_size_bytes(self) -> int:
        """Convierte MB a bytes para uso interno."""
        return self.MAX_VIDEO_SIZE_MB * 1024 * 1024
    
    # Metodo para obtener la ruta absoluta del directorio de uploads
    # Path(__file__) -> ruta de este archivo (config.py)
    # .parent.parent.parent -> sube 3 niveles: core/ -> app/ -> carpeta raiz
    def get_upload_path(self) -> Path:
        """Obtiene la ruta absoluta del directorio de uploads."""
        return Path(__file__).parent.parent.parent / self.UPLOAD_DIR
    
    # Lo mismo pero para el directorio de videos procesados
    def get_processed_path(self) -> Path:
        """Obtiene la ruta absoluta del directorio de procesados."""
        return Path(__file__).parent.parent.parent / self.PROCESSED_DIR
    
    # Configuracion interna de Pydantic
    # Le dice que el archivo .env tiene las variables
    class Config:
        # Busca el archivo .env en la misma carpeta que este
        env_file = ".env"
        # Los nombres de las variables son case insensitive
        case_sensitive = False


# Esto es un patron de diseño singleton
# lru_cache guarda en memoria el resultado para no crear varias veces
# get_settings() siempre retorna la misma instancia de Settings
@lru_cache()
def get_settings() -> Settings:
    """Singleton para acceder a la configuracion."""
    return Settings()


# Creamos una instancia global que se puede importar desde cualquier lugar
settings = get_settings()