"""
Configuración de logging para la aplicación FastAPI.
Utiliza structlog para logging estructurado.
"""

import logging
import sys

import structlog


def setup_logging() -> None:
    """
    Configura el logging estructurado para la aplicación.
    
    Esta configuración es compatible con structlog>=24.1.0.
    """
    # Configurar processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]
    
    # Configurar structlog sin wrapper_class especial
    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    
    # Configurar el logger estándar de Python
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # Crear handler con el formatter de structlog
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(
            processor=structlog.dev.ConsoleRenderer()
        )
    )
    
    # Agregar el handler al logger raíz
    root_logger.addHandler(handler)


# Inicializar logging al importar el módulo
setup_logging()

# Logger específico para usar en toda la aplicación
logger = structlog.get_logger()