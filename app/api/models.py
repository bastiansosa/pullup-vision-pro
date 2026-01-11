"""
Modelos de datos para la API usando Pydantic.
 Define la estructura de las solicitudes y respuestas.
"""
# Pydantic es una libreria que valida datos automaticamente
# Cuando definimos una clase que hereda de BaseModel
# Pydantic se encarga de validar que los datos sean correctos
# Si algo esta mal, lanza un error antes de que llegue a nuestro codigo
from pydantic import BaseModel, Field
# Optional significa que un campo puede ser None (nulo)
# List significa que es una lista de algo
from typing import Optional, List
# datetime nos permite manejar fechas y horas
from datetime import datetime


# ===========================================
# CLASE: HealthResponse
# ===========================================

class HealthResponse(BaseModel):
    """Respuesta del endpoint de salud."""
    # Este modelo define la respuesta cuando alguien
    # consulta si la API esta funcionando
    
    # status: "ok" si esta funcionando, otro valor si no
    # El "= ok" significa que si no nos mandan nada, usa "ok" por defecto
    status: str = "ok"
    
    # version: la version de nuestra app
    # Este campo es obligatorio, si no lo mandan, Pydantic da error
    version: str
    
    # message: mensaje adicional explicando el estado
    # Por defecto dice que el servicio esta funcionando correctamente
    message: str = "El servicio esta funcionando correctamente"


# ===========================================
# CLASE: ErrorResponse
# ===========================================

class ErrorResponse(BaseModel):
    """Respuesta de error."""
    # Este modelo define como se ve un error
    
    # error: titulo corto del error (obligatorio)
    error: str
    
    # detalle: descripcion detallada (opcional, puede ser None)
    # Optional[str] significa que puede ser string o None
    detalle: Optional[str] = None
    
    # timestamp: cuando ocurrio el error (opcional)
    # Field(default_factory=datetime.now.isoformat) significa:
    # Si no nos mandan timestamp, genera uno automaticamente
    # con la fecha y hora actual en formato ISO
    timestamp: str = Field(default_factory=datetime.now().isoformat)


# ===========================================
# CLASE: StatsResponse
# ===========================================

class StatsResponse(BaseModel):
    """Estadisticas de una repeticion."""
    # Este modelo define las estadisticas de cada dominada
    
    # repeticion: numero de la repeticion (1, 2, 3...)
    repeticion: int
    
    # angulo_maximo: el angulo mas abierto que tuvo el codo
    # durante esa repeticion (ej: 165 grados)
    angulo_maximo: float
    
    # angulo_minimo: el angulo mas cerrado que tuvo el codo
    # durante esa repeticion (ej: 40 grados)
    angulo_minimo: float


# ===========================================
# CLASE: ProgresoResponse
# ===========================================

class ProgresoResponse(BaseModel):
    """Respuesta del progreso de procesamiento."""
    # Este modelo define el porcentaje de progreso
    
    # progreso: numero entre 0 y 100
    # Field(...) significa que es obligatorio
    # ge=0 significa "greater or equal" (mayor o igual a 0)
    # le=100 significa "less or equal" (menor o igual a 100)
    # Esto valida automaticamente que el valor este entre 0 y 100
    progreso: float = Field(..., ge=0, le=100, description="Porcentaje de progreso (0-100)")


# ===========================================
# CLASE: ResultadoAnalisis
# ===========================================

class ResultadoAnalisis(BaseModel):
    """Resultado completo del analisis de un video."""
    # Este modelo define la respuesta completa del analisis
    
    # exito: True si todo salio bien, False si hubo error
    exito: bool
    
    # video_entrada: nombre del archivo que subio el usuario
    video_entrada: str
    
    # video_salida: nombre del archivo procesado (opcional)
    # Si hubo error, esto sera None
    video_salida: Optional[str] = None
    
    # repeticiones: numero de dominadas contadas
    repeticiones: int
    
    # duracion_segundos: cuanto dura el video en segundos
    duracion_segundos: float
    
    # fps: fotogramas por segundo del video
    fps: float
    
    # resolucion_ancho: ancho del video en pixeles
    resolucion_ancho: int
    
    # resolucion_alto: alto del video en pixeles
    resolucion_alto: int
    
    # tiempo_procesamiento: cuanto tardo en procesar el video
    tiempo_procesamiento: float
    
    # historial_repeticiones: lista con estadisticas de cada repeticion
    # List[StatsResponse] significa una lista de objetos StatsResponse
    historial_repeticiones: List[StatsResponse] = []
    
    # mensaje_error: si hubo un error, aqui esta el mensaje
    mensaje_error: Optional[str] = None
    
    # timestamp: cuando se hizo el analisis
    timestamp: str = Field(default_factory=datetime.now().isoformat)


# ===========================================
# CLASE: InfoVideoResponse
# ===========================================

class InfoVideoResponse(BaseModel):
    """Informacion sobre el video procesado."""
    # Este modelo define info basica del video
    
    # nombre_archivo: nombre del archivo
    nombre_archivo: str
    
    # repeticiones: numero de dominadas
    repeticiones: int
    
    # duracion_formato: duracion en formato legible
    # ejemplo: "0:30" para 30 segundos, "2:15" para 2 minutos 15 segundos
    duracion_formato: str
    
    # calidad: descripcion de la resolucion
    # ejemplo: "1920x1080 (Full HD)"
    calidad: str