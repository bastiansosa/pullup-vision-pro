"""
Configuración de logging para la aplicación FastAPI.
Utiliza structlog para logging estructurado.
"""

import logging
import sys

import structlog
from structlog.stdlib import add_log_level, filter_by_level


def setup_logging() -> None:
    """
    Configura el logging estructurado para la aplicación.
    
    Esta configuración utiliza ProcessorFormatter en lugar del obsoleto ProcessorRenderer,
    compatible con structlog>=24.1.0.
    """
    # Configuración de processors para structlog
    processors = [
        filter_by_level,
        add_log_level,
        structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
    ]
    
    # Configurar structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.ProcessorFormatter,
        context_class=dict,
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