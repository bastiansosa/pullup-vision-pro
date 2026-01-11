"""
Configuracion de logging estructurado para produccion.
 Usa JSON format para facilitar el analisis en la nube.
"""
# structlog es una libreria que mejora el logging de Python
# hace que los logs sean mas legibles y en formato JSON
# esto es util cuando se suba la app a produccion porque
# los servicios de la nube pueden leer los logs JSON facilmente
import structlog
import logging


# Esta funcion se llama al inicio de la app para configurar los logs
def setup_logging():
    """
    Configura el sistema de logging estructurado.
    Esto permite mejor trazabilidad en produccion.
    """
    # Logging basico de Python
    # Esto configura el logger por defecto que viene con Python
    # basicConfig solo se puede llamar una vez
    logging.basicConfig(
        # Nivel INFO significa que vamos a ver info, warnings y errores
        # pero no debug (mensajes de desarrollo)
        level=logging.INFO,
        # Formato de los mensajes de log
        # %(asctime)s -> fecha y hora
        # %(name)s -> nombre del logger
        # %(levelname)s -> INFO, WARNING, ERROR
        # %(message)s -> el mensaje que escribimos
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    
    # Ahora configuramos structlog que es mas avanzado
    # structlog.configure cambia como se ven y estructuran los logs
    structlog.configure(
        # processors es una lista de transformaciones que se aplican
        # a cada mensaje de log antes de mostrarlo
        processors=[
            # Filtra por nivel (INFO, ERROR, etc)
            structlog.stdlib.filter_by_level,
            # Agrega el nombre del logger
            structlog.stdlib.add_logger_name,
            # Agrega el nivel (INFO, WARNING, etc)
            structlog.stdlib.add_log_level,
            # Formatea los argumentos posicionales
            structlog.stdlib.PositionalArgumentsFormatter(),
            # Agrega timestamp en formato ISO
            structlog.processors.TimeStamper(fmt="iso"),
            # Muestra info del stack si hay un error
            structlog.processors.StackInfoRenderer(),
            # Formatea las excepciones para que se lean mejor
            structlog.processors.format_exc_info,
            # Decodifica caracteres unicode
            structlog.processors.UnicodeDecoder(),
            # Convierte todo a formato legible
            structlog.stdlib.ProcessorRenderer.wrap_with_formatter,
        ],
        # context_class define que tipo de datos usamos para el contexto
        context_class=dict,
        # LoggerFactory crea los loggers
        logger_factory=structlog.stdlib.LoggerFactory(),
        # Wrapper es una capa extra sobre el logger
        wrapper_class=structlog.stdlib.BoundLogger,
        # Cache para no crear el mismo logger varias veces
        cache_logger_on_first_use=True,
    )


# Esta funcion nos ayuda a crear loggers en cualquier parte del codigo
def get_logger(name: str):
    """
    Obtiene un logger con el nombre especificado.
    
    Args:
        name: Nombre del logger (usualmente __name__)
            __name__ es una variable especial de Python que tiene
            el nombre del modulo actual
        
    Returns:
        Logger configurado
    """
    # structlog.get_logger crea un nuevo logger
    # le pasamos un nombre para identificar de donde viene el log
    return structlog.get_logger(name)