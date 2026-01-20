import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, Optional, Tuple
from dataclasses import dataclass
import os
import uuid
from pathlib import Path

# Clase para guardar la configuracion de los hombros
# Esto nos permite cambiarla despues si el usuario lo necesita
@dataclass
class ShoulderConfig:
    """Configuracion de altura de hombros para adaptacion a diferentes usuarios."""
    # Valores por defecto que funcionaron con mi video
    # Se pueden cambiar desde el endpoint de la API
    alt_max_y: float = 0.35  # Posicion Y maxima de hombros (arriba)
    alt_min_y: float = 0.55  # Posicion Y minima de hombros (abajo)
    confianza_minima: float = 0.5  # Confianza minima para considerar el landmark

class VisionEngine:
    """
    Motor de vision para analisis de ejercicio de dominadas.
    
    Esta version permite configurar la altura de hombros para adaptarse
    a diferentes usuarios y genera videos con el analisis aplicado.
    """
    
    def __init__(self, output_dir: str = "static/videos"):
        """
        Inicializa el motor de vision.
        
        Args:
            output_dir: Directorio donde se guardan los videos procesados.
        """
        # Guardo el directorio donde voy a guardar los videos
        self.output_dir = Path(output_dir)
        # Creo el directorio si no existe
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuracion de hombros (valores por defecto)
        # Estos valores los puse porque me funcionaron con mi video
        self.shoulder_config = ShoulderConfig()
        
        # Inicializar MediaPipe Pose
        # Esto es lo que detecta el cuerpo en el video
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Utilidades de dibujo para poner el esqueleto en el video
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Contadores para las repeticiones
        self.rep_count = 0
        self.state = "up"  # Estados posibles: "up" (arriba), "down" (abajo)
        self.frame_count = 0
        
    def set_shoulder_config(self, alt_max_y: float, alt_min_y: float):
        """
        Configura los parametros de altura de hombros.
        Esto es importante porque cada persona tiene una altura diferente.
        
        Args:
            alt_max_y: Valor Y maximo de hombros (posicion arriba, ej: 0.35)
            alt_min_y: Valor Y minimo de hombros (posicion abajo, ej: 0.55)
            
        Nota: En MediaPipe, Y=0 es arriba e Y=1 es abajo de la imagen.
        """
        self.shoulder_config.alt_max_y = alt_max_y
        self.shoulder_config.alt_min_y = alt_min_y
        # Imprimo para saber que valores se usaron
        print(f"Configuracion actualizada: alt_max_y={alt_max_y}, alt_min_y={alt_min_y}")
        
    def reset_counters(self):
        """Reinicia los contadores. Lo uso cuando empiezo a procesar un video nuevo."""
        self.rep_count = 0
        self.state = "up"
        self.frame_count = 0
        
    def _extraer_landmarks(self, pose_landmarks) -> list:
        """Extrae landmarks del resultado de MediaPipe."""
        landmarks = []
        # Recorro todos los puntos que detecta MediaPipe
        for landmark in pose_landmarks.landmark:
            landmarks.append({
                'x': landmark.x,
                'y': landmark.y,
                'z': landmark.z,
                'visibility': landmark.visibility
            })
        return landmarks
    
    def _calcular_angulo(self, p1: dict, p2: dict, p3: dict) -> float:
        """Calcula el angulo en punto2 (p2 es el vertice)."""
        import math
        
        # Calculo las diferencias entre los puntos
        dx1 = p1['x'] - p2['x']
        dy1 = p1['y'] - p2['y']
        dx2 = p3['x'] - p2['x']
        dy2 = p3['y'] - p2['y']
        
        # Calculo los angulos con atan2
        angulo1 = math.atan2(dy1, dx1)
        angulo2 = math.atan2(dy2, dx2)
        
        # Calculo la diferencia entre los angulos
        diferencia = angulo2 - angulo1
        
        # Normalizo el angulo para que este entre -pi y pi
        while diferencia > math.pi:
            diferencia -= 2 * math.pi
        while diferencia < -math.pi:
            diferencia += 2 * math.pi
        
        # Devuelvo el angulo en grados
        return abs(math.degrees(diferencia))
    
    def _detectar_repeticion(self, landmarks: list) -> Optional[str]:
        """
        Detecta si se ha completado una repeticion.
        
        Returns:
            "up" si subio, "down" si bajo, None si no hay cambio.
        """
        # Verifico que tengamos suficientes landmarks
        if not landmarks or len(landmarks) < 33:
            return None
        
        # Obtener hombros (landmarks 11 y 12 en MediaPipe)
        # El 11 es el hombro izquierdo y el 12 el derecho
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        
        # Verificar confianza minima
        # Si no se ve bien el hombro, no lo uso
        if left_shoulder['visibility'] < self.shoulder_config.confianza_minima:
            return None
        if right_shoulder['visibility'] < self.shoulder_config.confianza_minima:
            return None
        
        # Usar el hombro con mejor visibilidad
        shoulder = left_shoulder if left_shoulder['visibility'] > right_shoulder['visibility'] else right_shoulder
        
        # Verificar posicion de hombros segun configuracion
        # En MediaPipe, Y=0 es arriba y Y=1 es abajo
        if shoulder['y'] <= self.shoulder_config.alt_max_y:
            # Hombro arriba - esto significa que subio
            if self.state == "down":
                self.rep_count += 1  # Sumo una repeticion
                self.state = "up"
                return "up"
        elif shoulder['y'] >= self.shoulder_config.alt_min_y:
            # Hombro abajo - esto significa que bajo
            if self.state == "up":
                self.state = "down"
                return "down"
        
        return None
    
    def _dibujar_info(self, frame: np.ndarray, state: str = "up") -> np.ndarray:
        """Dibuja informacion en el frame para que se vea en el video."""
        # Pongo el contador de repeticiones en la esquina
        cv2.putText(
            frame,
            f"Repeticiones: {self.rep_count}",
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (0, 255, 0),
            3
        )
        
        # Pongo el estado actual (arriba o abajo)
        color_estado = (0, 255, 0) if state == "up" else (0, 165, 255)
        cv2.putText(
            frame,
            f"Estado: {state.upper()}",
            (20, 100),
            cv2.FONT_HERSHEY_SIMPLEX,
            1,
            color_estado,
            2
        )
        
        # Pongo la configuracion de hombros para que el usuario vea los valores
        cv2.putText(
            frame,
            f"Umbral sup: {self.shoulder_config.alt_max_y:.2f}",
            (20, 140),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (200, 200, 200),
            2
        )
        cv2.putText(
            frame,
            f"Umbral inf: {self.shoulder_config.alt_min_y:.2f}",
            (20, 170),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (200, 200, 200),
            2
        )
        
        return frame
    
    def procesar_video(self, 
                       video_path: str, 
                       generar_video: bool = True,
                       output_filename: Optional[str] = None) -> Dict:
        """
        Procesa un video de dominadas y cuenta repeticiones.
        
        Args:
            video_path: Ruta del video de entrada.
            generar_video: Si True, genera video con analisis.
            output_filename: Nombre del archivo de salida (opcional).
        
        Returns:
            Diccionario con resultados.
        """
        # Verifico que exista el video
        if not os.path.exists(video_path):
            return {"error": "El video no existe"}
        
        # Reinicio los contadores para este video nuevo
        self.reset_counters()
        
        # Abro el video
        cap = cv2.VideoCapture(video_path)
        
        # Si no se pudo abrir, devuelvo error
        if not cap.isOpened():
            return {"error": "No se pudo abrir el video"}
        
        # Obtengo las propiedades del video (fps, ancho, alto)
        fps = cap.get(cv2.CAP_PROP_FPS)
        ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Configurar video de salida si el usuario quiere
        video_output_path = None
        writer = None
        
        if generar_video:
            # Genero un nombre unico para el video
            if output_filename is None:
                output_filename = f"analisis_{uuid.uuid4().hex[:8]}.mp4"
            
            video_output_path = str(self.output_dir / output_filename)
            # Configuro el writer de video
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(video_output_path, fourcc, fps, (ancho, alto))
        
        frame_count = 0
        last_state = self.state
        
        # Proceso frame por frame
        while True:
            ret, frame = cap.read()
            
            # Si no hay mas frames, salgo del loop
            if not ret:
                break
            
            # Convierto a RGB para MediaPipe (OpenCV usa BGR)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resultados = self.pose.process(frame_rgb)
            
            # Si detecto una persona, proceso los landmarks
            if resultados.pose_landmarks:
                # Extraigo los landmarks
                landmarks = self._extraer_landmarks(resultados.pose_landmarks)
                
                # Detecto si hay una repeticion
                cambio = self._detectar_repeticion(landmarks)
                if cambio:
                    last_state = cambio
                
                # Dibujo el esqueleto en el frame
                self.mp_drawing.draw_landmarks(
                    frame,
                    resultados.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                )
            
            # Dibujo la informacion en el frame
            frame = self._dibujar_info(frame, last_state)
            
            # Guardo el frame en el video de salida
            if writer:
                writer.write(frame)
            
            frame_count += 1
        
        # Libero los recursos
        cap.release()
        
        if writer:
            writer.release()
        
        # Cierro MediaPipe
        self.pose.close()
        
        # Preparo el resultado para devolver
        resultado = {
            "repeticiones": self.rep_count,
            "frames_procesados": frame_count,
            "fps_video": fps,
            "configuracion_hombros": {
                "umbral_superior": self.shoulder_config.alt_max_y,
                "umbral_inferior": self.shoulder_config.alt_min_y
            }
        }
        
        # Si genere video, agrego la ruta
        if video_output_path:
            resultado["video_path"] = video_output_path
            resultado["video_url"] = f"/static/videos/{os.path.basename(video_output_path)}"
        
        return resultado