"""
 Procesador de video que utiliza el motor de vision.
 Maneja la lectura y escritura de archivos de video.
"""
# os: para operaciones con archivos y directorios
# uuid: para generar nombres unicos aleatorios
# cv2: OpenCV para procesar video
# pathlib: para trabajar con rutas de archivos
# typing: para definir tipos de datos
# dataclasses: para crear clases simples
# datetime: para obtener fecha y hora
import os
import uuid
import cv2
import structlog
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass
from datetime import datetime


# Obtener logger para este modulo
logger = structlog.get_logger(__name__)


# ===========================================
# CLASE ResultadoProcesamiento
# ===========================================

@dataclass
class ResultadoProcesamiento:
    """Resultado del procesamiento de un video."""
    exito: bool                   # True si salio bien, False si hubo error
    video_entrada: str            # Ruta del video original
    video_salida: str             # Ruta del video procesado
    repeticiones: int             # Numero de dominadas contadas
    duracion_segundos: float      # Duracion del video en segundos
    fps: float                    # Fotogramas por segundo del video
    resolucion: tuple             # Tuple (ancho, alto) de la resolucion
    mensaje_error: Optional[str] = None  # Mensaje de error si hubo


# ===========================================
# CLASE VideoProcessor
# ===========================================

class VideoProcessor:
    """
    Procesa videos de dominadas usando el VisionEngine.
    
    Maneja la lectura del video de entrada, procesamiento frame por frame,
    y escritura del video de salida con anotaciones.
    """
    
    def __init__(self, vision_engine, upload_dir: str = "uploads", 
                 processed_dir: str = "processed"):
        """
        Inicializa el procesador de video.
        
        Args:
            vision_engine: Instancia del VisionEngine que hara la deteccion
            upload_dir: Directorio donde se guardan videos subidos
            processed_dir: Directorio donde se guardan videos procesados
        """
        # Guardar la instancia del motor de vision
        self.engine = vision_engine
        
        # Convertir strings a objetos Path para manejo de rutas
        # Path es mas moderno y seguro que usar strings
        self.upload_dir = Path(upload_dir)
        self.processed_dir = Path(processed_dir)
        
        # Crear los directorios si no existen
        # exist_ok=True significa que no da error si ya existen
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.processed_dir.mkdir(parents=True, exist_ok=True)
        
        # Loguear que se inicio el procesador
        logger.info("VideoProcessor inicializado",
                   upload_dir=str(self.upload_dir),
                   processed_dir=str(self.processed_dir))
    
    # ===========================================
    # METODO: procesar_video
    # ===========================================
    
    def procesar_video(self, ruta_video: str, 
                       callback_progreso: Optional[Callable[[float], None]] = None,
                       mostrar_anotaciones: bool = True) -> ResultadoProcesamiento:
        """
        Procesa un video de dominadas completo.
        
        Este es el metodo principal que hace todo el trabajo:
        1. Lee el video frame por frame
        2. Envia cada frame al VisionEngine
        3. Escribe el video de salida con anotaciones
        
        Args:
            ruta_video: Ruta del video de entrada (archivo original)
            callback_progreso: Funcion opcional para reportar progreso (0-100)
            mostrar_anotaciones: Si True, dibuja el esqueleto y UI
            
        Returns:
            ResultadoProcesamiento con las estadisticas del video
        """
        # ===================================
        # Validaciones iniciales
        # ===================================
        
        # Validar que el archivo existe
        # Si no existe, retornar error
        if not os.path.exists(ruta_video):
            return ResultadoProcesamiento(
                exito=False,
                video_entrada=ruta_video,
                video_salida="",
                repeticiones=0,
                duracion_segundos=0,
                fps=0,
                resolucion=(0, 0),
                mensaje_error="El archivo de video no existe"
            )
        
        # Loguear que empezamos a procesar
        logger.info("Iniciando procesamiento", video=ruta_video)
        
        # Resetear el motor para empezar desde cero
        self.engine.reset()
        
        # ===================================
        # Abrir el video
        # ===================================
        
        # cv2.VideoCapture abre el video
        # Le pasamos la ruta del archivo
        cap = cv2.VideoCapture(ruta_video)
        
        # Si no se pudo abrir, retornar error
        if not cap.isOpened():
            return ResultadoProcesamiento(
                exito=False,
                video_entrada=ruta_video,
                video_salida="",
                repeticiones=0,
                duracion_segundos=0,
                fps=0,
                resolucion=(0, 0),
                mensaje_error="No se pudo abrir el video"
            )
        
        # ===================================
        # Obtener propiedades del video
        # ===================================
        
        # CAP_PROP_FPS: fotogramas por segundo del video
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # CAP_PROP_FRAME_WIDTH/HEIGHT: dimensiones del video
        ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # CAP_PROP_FRAME_COUNT: numero total de frames
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Duracion = frames / fps
        duracion = total_frames / fps if fps > 0 else 0
        
        # ===================================
        # Preparar video de salida
        # ===================================
        
        # Generar nombre unico para el video procesado
        # Usamos timestamp para que no se sobreescriban archivos
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        nombre_base = Path(ruta_video).stem  # Nombre sin extension
        nombre_salida = f"{nombre_base}_procesado_{timestamp}.mp4"
        ruta_salida = self.processed_dir / nombre_salida
        
        # Configurar el escritor de video
        # fourcc es el codec de video (mp4v es para MP4)
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        # VideoWriter graba el video procesado
        # Params: ruta_salida, codec, fps, resolucion
        writer = cv2.VideoWriter(str(ruta_salida), fourcc, fps, (ancho, alto))
        
        # Contador de frames procesados
        frame_actual = 0
        
        # ===================================
        # Bucle principal: procesar cada frame
        # ===================================
        
        try:
            # Mientras haya frames por leer
            while True:
                # Leer el siguiente frame
                # ret = True/False si se leyo bien
                # frame = la imagen en si
                ret, frame = cap.read()
                
                # Si no hay mas frames, salir del bucle
                if not ret:
                    break
                
                # Convertir de BGR a RGB
                # OpenCV lee en BGR, MediaPipe necesita RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Procesar el frame con el VisionEngine
                # Esto detecta la pose y actualiza el contador
                nueva_repeticion, fase = self.engine.procesar_frame(frame_rgb)
                
                # Si mostrar_anotaciones esta activo y hay deteccion
                # Dibujar las anotaciones en el frame
                if mostrar_anotaciones and fase != "SIN_DETECCION":
                    frame = self._dibujar_anotaciones(
                        frame, fase, self.engine.contador_repeticiones
                    )
                
                # Escribir el frame (con o sin anotaciones) en el video de salida
                writer.write(frame)
                
                # Reportar progreso cada 30 frames
                frame_actual += 1
                if callback_progreso and frame_actual % 30 == 0:
                    progreso = (frame_actual / total_frames) * 100
                    callback_progreso(progreso)
        
        # Si algo sale mal durante el procesamiento
        except Exception as e:
            # Loguear el error
            logger.error("Error durante procesamiento", error=str(e))
            # Retornar error
            return ResultadoProcesamiento(
                exito=False,
                video_entrada=ruta_video,
                video_salida="",
                repeticiones=0,
                duracion_segundos=0,
                fps=0,
                resolucion=(0, 0),
                mensaje_error=f"Error durante el procesamiento: {str(e)}"
            )
        
        # ===================================
        # Limpieza y retorno
        # ===================================
        
        finally:
            # Siempre cerrar los recursos, sin importar si hubo error o no
            cap.release()      # Cerrar el video de entrada
            writer.release()   # Cerrar el video de salida
        
        # Obtener las estadisticas finales del motor
        stats = self.engine.obtener_estadisticas()
        
        # Loguear que terminamos
        logger.info("Procesamiento completado",
                   repeticiones=stats["repeticiones"],
                   duracion=duracion,
                   video_salida=str(ruta_salida))
        
        # Retornar resultado exitoso
        return ResultadoProcesamiento(
            exito=True,
            video_entrada=ruta_video,
            video_salida=str(ruta_salida),
            repeticiones=stats["repeticiones"],
            duracion_segundos=duracion,
            fps=fps,
            resolucion=(ancho, alto)
        )
    
    # ===========================================
    # METODO: _dibujar_anotaciones (privado)
    # ===========================================
    
    def _dibujar_anotaciones(self, frame, fase: str, repeticiones: int):
        """
        Dibuja las anotaciones en el frame.
        
        Args:
            frame: Frame original donde dibujar
            fase: Fase actual detectada (ARRIBA/BAJO)
            repeticiones: Numero de repeticiones contadas
            
        Returns:
            Frame con anotaciones dibujadas
        """
        # Nota: En produccion, usamos el esqueleto del motor
        # Esta es una version simplificada
        
        # ===================================
        # Panel del contador (rectangulo negro)
        # ===================================
        
        # Posicion del panel (esquina superior izquierda)
        panel_x = 20
        panel_y = 20
        # Dibujar rectangulo negro relleno
        cv2.rectangle(frame, (panel_x, panel_y), 
                     (panel_x + 150, panel_y + 80), 
                     (0, 0, 0), -1)  # -1 = relleno
        
        # ===================================
        # Contador grande (numero de repeticiones)
        # ===================================
        
        # Color segun la fase
        # Verde si esta arriba, naranja si esta abajo
        color_contador = (0, 255, 0) if fase == "ALTO" else (0, 165, 255)
        
        # Escribir el numero de repeticiones
        # Params: imagen, texto, posicion, fuente, tamano, color, grosor
        cv2.putText(
            frame,
            f"{repeticiones}",
            (panel_x + 75, panel_y + 55),
            cv2.FONT_HERSHEY_SIMPLEX,  # Tipo de letra
            2.0,                        # Tamano de la letra
            color_contador,             # Color (B, G, R)
            3                           # Grosor de la linea
        )
        
        # ===================================
        # Texto de la fase
        # ===================================
        
        cv2.putText(
            frame,
            fase,
            (panel_x, panel_y + 75),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (200, 200, 200),  # Color gris
            1
        )
        
        return frame
    
    # ===========================================
    # METODO: limpiar_archivos_temporales
    # ===========================================
    
    def limpiar_archivos_temporales(self, edad_maxima_horas: int = 24):
        """
        Elimina archivos de video antiguos para liberar espacio.
        
        Args:
            edad_maxima_horas: Edad maxima de los archivos en horas
        """
        import time
        
        # Calcular el tiempo limite
        # Tiempo actual - (horas * segundos por hora)
        limite_tiempo = time.time() - (edad_maxima_horas * 3600)
        
        # ===================================
        # Limpiar directorio de uploads
        # ===================================
        
        # Iterar sobre todos los archivos en upload_dir
        for archivo in self.upload_dir.glob("*"):
            # Si es un archivo (no carpeta)
            if archivo.is_file():
                # Comparar fecha de modificacion con el limite
                if archivo.stat().st_mtime < limite_tiempo:
                    # Eliminar el archivo
                    archivo.unlink()
                    logger.info("Archivo temporal eliminado", archivo=str(archivo))
        
        # ===================================
        # Limpiar directorio de procesados
        # ===================================
        
        for archivo in self.processed_dir.glob("*"):
            if archivo.is_file():
                if archivo.stat().st_mtime < limite_tiempo:
                    archivo.unlink()
                    logger.info("Archivo procesado eliminado", archivo=str(archivo))


# ===========================================
# FUNCION AUXILIAR
# ===========================================

def tiempo_actual() -> float:
    """Obtiene el tiempo actual en segundos desde epoch."""
    # time.time() retorna segundos desde 1 de enero de 1970
    return __import__("time").time()