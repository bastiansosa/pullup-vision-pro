"""
Endpoints de la API para el contador de dominadas.
 Maneja las solicitudes HTTP y la lógica de negocio.
"""

# Importamos las herramientas basicas que necesitamos para hacer el trabajo
import os              # Para manejar archivos y carpetas del sistema operativo
import uuid            # Para generar nombres unicos para los archivos subidos
import shutil          # Para copiar o mover archivos si es necesario
import structlog       # Para hacer logging estructurado (ver民生or lo que pasa en la app)

# FastAPI nos da las herramientas para crear la API REST
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse  # Para devolver respuestas
from typing import Optional  # Para indicar que algo puede ser None

# Importamos la configuracion que vive en otro archivo (core/config.py)
from app.core.config import settings

# Importamos los modelos Pydantic que definen la estructura de nuestras respuestas
# Estos los creamos en api/models.py para validar datos
from app.api.models import (
    ResultadoAnalisis,
    ErrorResponse,
    HealthResponse,
    InfoVideoResponse
)

# Importamos el motor de vision y el procesador de video
# Estos son los que hacen el trabajo pesado de analizar los videos
from app.services.vision_engine import VisionEngine
from app.services.video_processor import VideoProcessor, ResultadoProcesamiento


# Creamos un logger (registrador) para este modulo
# Esto nos permite ver en los logs cual endpoint esta siendo llamado
logger = structlog.get_logger(__name__)

# Creamos el router de la API
# Esto es como un contenedor que agrupa todos nuestros endpoints
router = APIRouter()

# Creamos una instancia global del motor de vision
# Le pasamos los umbrales que definimos en la configuracion
# Estos umbrales son para determinar cuando esta arriba o abajo en la barra
vision_engine = VisionEngine(
    umbral_alto=settings.umbral_alto,
    umbral_bajo=settings.umbral_bajo
)

# Creamos una instancia del procesador de video
# Le pasamos el motor de vision y las carpetas donde se guardan los archivos
video_processor = VideoProcessor(
    vision_engine=vision_engine,
    upload_dir=str(settings.get_upload_path()),      # Carpeta para videos subidos
    processed_dir=str(settings.get_processed_path())  # Carpeta para videos procesados
)


@router.get("/health", response_model=HealthResponse, tags=["Sistema"])
async def verificar_salud():
    """
    Endpoint de verificacion de salud.
    Usado por el balanceador de carga para verificar que el servicio esta activo.
    
    Cuando desplegamos en produccion, los balanceadores de carga (como Nginx o AWS ALB)
    hacen pings periodicos a este endpoint para saber si la aplicacion esta viva.
    Si este endpoint responde bien, saben que pueden enviar trafico aqui.
    """
    # Devolvemos un objeto HealthResponse con la informacion de salud
    return HealthResponse(
        version=settings.VERSION,  # Version de la app desde config
        status="ok",               # Indicamos que todo esta bien
        message="El servicio de analisis de dominadas esta funcionando"
    )


@router.post("/api/v1/analizar", response_model=ResultadoAnalisis, 
             responses={400: {"model": ErrorResponse}}, tags=["Analisis"])
async def analisar_video(file: UploadFile = File(...)):
    """
    Analiza un video de dominadas.
    
    Este es el endpoint principal que hace toda la magia.
    El usuario nos manda un video y nosotros le devolvemos el conteo de repeticiones.
    
    Args:
        file: Video a analizar (mp4, mov, avi, max 50MB)
    
    Returns:
        ResultadoAnalisis con el conteo y estadisticas
    """
    # Registramos en los logs que alguien hizo una peticion de analisis
    logger.info("Nueva solicitud de analisis", filename=file.filename)
    
    # --- VALIDACIONES ---
    # Primero validamos que el archivo sea de un tipo permitido
    # Obtenemos la extension del archivo (lo que esta despues del ultimo punto)
    tipo_archivo = file.filename.split(".")[-1].lower()
    
    # Comparamos con los tipos permitidos que definimos en config
    if tipo_archivo not in settings.ALLOWED_VIDEO_TYPES:
        # Si no es valido, lanzamos un error HTTP 400 (Bad Request)
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Tipo de archivo no permitido",
                "detalle": f"Tipos permitidos: {settings.ALLOWED_VIDEO_TYPES}",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    # Validamos el tamaño del archivo
    # Leemos el contenido del archivo (esto puede ser pesado para archivos grandes)
    contenido = await file.read()
    if len(contenido) > settings.max_video_size_bytes:
        raise HTTPException(
            status_code=400,
            detail={
                "error": "Archivo demasiado grande",
                "detalle": f"Tamano maximo: {settings.MAX_VIDEO_SIZE_MB}MB",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    # --- GUARDADO DEL ARCHIVO ---
    # Generamos un nombre unico para el archivo usando UUID
    # Esto evita que si dos usuarios suben "video.mp4", no se sobrescriban
    nombre_archivo = f"{uuid.uuid4()}_{file.filename}"
    
    # Construimos la ruta completa donde guardaremos el archivo
    ruta_archivo = settings.get_upload_path() / nombre_archivo
    
    try:
        # Escribimos el contenido del archivo en disco
        with open(ruta_archivo, "wb") as buffer:
            buffer.write(contenido)
        
        logger.info("Archivo guardado", ruta=str(ruta_archivo))
        
        # --- PROCESAMIENTO DEL VIDEO ---
        # Medimos cuanto tiempo tarda el procesamiento (para estadisticas)
        import time
        inicio = time.time()
        
        # Creamos un callback para ir viendo el progreso
        # Esto podria conectarse con WebSockets para dar feedback en tiempo real
        def callback_progreso(progreso: float):
            logger.debug("Procesando", progreso=progreso)
        
        # Llamamos al procesador de video que hace todo el trabajo
        # Le pasamos la ruta del archivo y configuramos que queremos anotaciones
        resultado = video_processor.procesar_video(
            str(ruta_archivo),
            callback_progreso=callback_progreso,
            mostrar_anotaciones=True  # Dibujara el conteo en el video
        )
        
        # Calculamos cuanto tiempo duro el procesamiento
        tiempo_procesamiento = time.time() - inicio
        
        # --- CONSTRUCCION DE LA RESPUESTA ---
        # Creamos el objeto de respuesta usando el modelo Pydantic
        # Esto asegura que la respuesta tenga el formato correcto
        respuesta = ResultadoAnalisis(
            exito=resultado.exito,
            video_entrada=resultado.video_entrada,
            # Extraemos solo el nombre del archivo de la ruta completa
            video_salida=resultado.video_salida.split("/")[-1] if resultado.video_salida else None,
            repeticiones=resultado.repeticiones,
            duracion_segundos=resultado.duracion_segundos,
            fps=resultado.fps,
            resolucion_ancho=resultado.resolucion[0],
            resolucion_alto=resultado.resolucion[1],
            tiempo_procesamiento=tiempo_procesamiento,
            # Convertimos el historial de repeticiones a un formato serializable (dict)
            historial_repeticiones=[
                {"repeticion": r.repeticion, 
                 "angulo_maximo": r.angulo_maximo, 
                 "angulo_minimo": r.angulo_minimo}
                for r in vision_engine.historial_repeticiones
            ],
            mensaje_error=resultado.mensaje_error
        )
        
        # Logueamos que el analisis termino correctamente
        logger.info("Analisis completado", 
                   repeticiones=resultado.repeticiones,
                   tiempo=tiempo_procesamiento)
        
        # Devolvemos la respuesta al cliente
        return respuesta
        
    except Exception as e:
        # Si algo sale mal, logueamos el error y devolvemos un 500
        logger.error("Error durante analisis", error=str(e))
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Error interno del servidor",
                "detalle": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )
    
    finally:
        # --- LIMPIEZA ---
        # Este bloque siempre se ejecuta, tanto si hubo error como si no
        # Borramos el archivo original que subio el usuario para no acumular basura
        if os.path.exists(ruta_archivo):
            os.remove(ruta_archivo)
            logger.info("Archivo temporal eliminado", ruta=str(ruta_archivo))


@router.get("/api/v1/video/{nombre_archivo}", tags=["Archivos"])
async def obtener_video(nombre_archivo: str):
    """
    Obtiene un video procesado.
    
    Este endpoint permite al usuario descargar el video con las anotaciones
    (el video donde se ve el conteo de repeticiones dibujado en pantalla).
    
    Args:
        nombre_archivo: Nombre del archivo de video que quiere descargar
    
    Returns:
        Video como archivo descargable
    """
    # Construimos la ruta completa del video
    ruta_video = settings.get_processed_path() / nombre_archivo
    
    # Verificamos que el archivo exista en disco
    if not os.path.exists(ruta_video):
        # Si no existe, devolvemos un 404 (Not Found)
        raise HTTPException(
            status_code=404,
            detail={
                "error": "Archivo no encontrado",
                "timestamp": datetime.now().isoformat()
            }
        )
    
    # Si existe, devolvemos el archivo usando FileResponse
    # Esto le dice al navegador que es un video y lo descarga o reproduce
    return FileResponse(
        path=str(ruta_video),
        media_type="video/mp4",  # Tipo MIME del video
        filename=nombre_archivo  # Nombre con el que se descargara
    )


@router.post("/api/v1/limpiar", tags=["Mantenimiento"])
async def limpiar_archivos_temporales(background_tasks: BackgroundTasks):
    """
    Limpia archivos temporales antiguos.
    
    Endpoint de mantenimiento para borrar archivos que ya no se necesitan.
    Los videos procesados y los temporales se van acumulando con el tiempo,
    asi que es buena idea borrarlos periodicamente.
    
    Args:
        background_tasks: FastAPI permite ejecutar tareas en segundo plano
                          sin bloquear la respuesta al cliente
    """
    # Agregamos la tarea de limpieza para que se ejecute despues de responder
    # Esto significa que el cliente no tiene que esperar a que termine la limpieza
    background_tasks.add_task(
        video_processor.limpiar_archivos_temporales,
        edad_maxima_horas=24  # Borramos archivos mayores a 24 horas
    )
    
    # Respondemos inmediatamente mientras la limpieza corre en segundo plano
    return {
        "mensaje": "Limpieza programada",
        "timestamp": datetime.now().isoformat()
    }


# Importamos datetime al final para evitar problemas de imports circulares
# (A veces Python se confunde si importas algo que todavia no se ha leido)
from datetime import datetime