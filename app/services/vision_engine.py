import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, Optional
from datetime import datetime
import os
from pathlib import Path

class VisionEngine:
    """
    Motor de vision para analisis de ejercicio de dominadas.
    Version mejorada con deteccion por angulos.
    """
    
    def __init__(self, output_dir: str = "static/videos"):
        """
        Inicializa el motor de vision.
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Configuracion por defecto
        self.angulo_subir = 160  # Angulo para considerar que subio
        self.angulo_bajar = 100  # Angulo para considerar que bajo
        self.confianza_minima = 0.5
        
        # Inicializar MediaPipe Pose
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            enable_segmentation=False,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Contadores
        self.rep_count = 0
        self.state = "up"
        self.frame_count = 0
        
    def reset_counters(self):
        """Reinicia los contadores."""
        self.rep_count = 0
        self.state = "up"
        self.frame_count = 0
        
    def _extraer_landmarks(self, pose_landmarks):
        """Extrae landmarks del resultado de MediaPipe."""
        landmarks = []
        for landmark in pose_landmarks.landmark:
            landmarks.append({
                'x': landmark.x,
                'y': landmark.y,
                'z': landmark.z,
                'visibility': landmark.visibility
            })
        return landmarks
    
    def _calcular_angulo(self, p1, p2, p3):
        """Calcula el angulo en punto2 (p2 es el vertice)."""
        import math
        
        dx1 = p1['x'] - p2['x']
        dy1 = p1['y'] - p2['y']
        dx2 = p3['x'] - p2['x']
        dy2 = p3['y'] - p2['y']
        
        angulo1 = math.atan2(dy1, dx1)
        angulo2 = math.atan2(dy2, dx2)
        
        diferencia = angulo2 - angulo1
        
        while diferencia > math.pi:
            diferencia -= 2 * math.pi
        while diferencia < -math.pi:
            diferencia += 2 * math.pi
        
        return abs(math.degrees(diferencia))
    
    def _detectar_repeticion(self, landmarks):
        """Detecta si se ha completado una repeticion usando angulos."""
        if not landmarks or len(landmarks) < 33:
            return None
        
        # Landmarks importantes para dominadas:
        # 11 = hombro izquierdo, 13 = codo izquierdo, 15 = muneca izquierda
        # 12 = hombro derecho, 14 = codo derecho, 16 = muneca derecha
        
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        
        # Usar el brazo con mejor visibilidad
        if left_shoulder['visibility'] > right_shoulder['visibility']:
            # Usar brazo izquierdo
            shoulder = left_shoulder
            elbow = landmarks[13]
            wrist = landmarks[15]
        else:
            # Usar brazo derecho
            shoulder = landmarks[12]
            elbow = landmarks[14]
            wrist = landmarks[16]
        
        # Verificar confianza minima
        if shoulder['visibility'] < self.confianza_minima:
            return None
        
        # Calcular angulo del codo
        angulo = self._calcular_angulo(shoulder, elbow, wrist)
        
        # Debug: mostrar angulo
        print(f"DEBUG: Angulo={angulo:.1f}, Estado={self.state}")
        
        # Detectar fase
        if angulo >= self.angulo_subir:
            # Brazo extendido (arriba)
            if self.state == "down":
                self.rep_count += 1
                self.state = "up"
                print(f"DEBUG: Repeticion detectada! Total={self.rep_count}")
                return "up"
        elif angulo <= self.angulo_bajar:
            # Brazo flexionado (abajo)
            if self.state == "up":
                self.state = "down"
                return "down"
        
        return None
    
    def _dibujar_info(self, frame, state="up", angulo=None):
        """Dibuja informacion en el frame."""
        # Contador de repeticiones
        cv2.putText(
            frame,
            f"Repeticiones: {self.rep_count}",
            (20, 50),
            cv2.FONT_HERSHEY_SIMPLEX,
            1.5,
            (0, 255, 0),
            3
        )
        
        # Estado actual
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
        
        # Angulo si esta disponible
        if angulo is not None:
            cv2.putText(
                frame,
                f"Angulo: {angulo:.1f}°",
                (20, 140),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.8,
                (255, 255, 0),
                2
            )
        
        return frame
    
    def procesar_video(self, video_path: str, generar_video: bool = True) -> Dict:
        """
        Procesa un video de dominadas y cuenta repeticiones.
        """
        if not os.path.exists(video_path):
            return {"error": "El video no existe"}
        
        self.reset_counters()
        
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            return {"error": "No se pudo abrir el video"}
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        ancho = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        alto = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duracion = total_frames / fps if fps > 0 else 0
        
        # Configurar video de salida
        video_output_path = None
        writer = None
        
        if generar_video:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"analisis_{timestamp}.mp4"
            video_output_path = str(self.output_dir / filename)
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            writer = cv2.VideoWriter(video_output_path, fourcc, fps, (ancho, alto))
        
        frame_count = 0
        last_state = self.state
        last_angulo = 0
        inicio = datetime.now()
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resultados = self.pose.process(frame_rgb)
            
            if resultados.pose_landmarks:
                landmarks = self._extraer_landmarks(resultados.pose_landmarks)
                
                cambio = self._detectar_repeticion(landmarks)
                if cambio:
                    last_state = cambio
                
                # Calcular angulo para mostrar
                if len(landmarks) >= 33:
                    left_shoulder = landmarks[11]
                    right_shoulder = landmarks[12]
                    if left_shoulder['visibility'] > right_shoulder['visibility']:
                        elbow = landmarks[13]
                        wrist = landmarks[15]
                    else:
                        elbow = landmarks[14]
                        wrist = landmarks[16]
                    last_angulo = self._calcular_angulo(
                        left_shoulder if left_shoulder['visibility'] > right_shoulder['visibility'] else right_shoulder,
                        elbow, wrist
                    )
                
                # Dibujar esqueleto
                self.mp_drawing.draw_landmarks(
                    frame,
                    resultados.pose_landmarks,
                    self.mp_pose.POSE_CONNECTIONS,
                    landmark_drawing_spec=self.mp_drawing_styles.get_default_pose_landmarks_style()
                )
            
            # Dibujar informacion
            frame = self._dibujar_info(frame, last_state, last_angulo)
            
            # Guardar frame
            if writer:
                writer.write(frame)
            
            frame_count += 1
            
            # Mostrar progreso cada 30 frames
            if frame_count % 30 == 0:
                print(f"Progreso: {frame_count}/{total_frames} ({frame_count*100//total_frames}%)")
        
        cap.release()
        
        if writer:
            writer.release()
        
        fin = datetime.now()
        tiempo_procesamiento = (fin - inicio).total_seconds()
        
        # Preparar respuesta
        resultado = {
            "repeticiones": self.rep_count,
            "frames_procesados": frame_count,
            "fps": round(fps, 1),
            "duracion_segundos": round(duracion, 1),
            "tiempo_procesamiento": round(tiempo_procesamiento, 2),
        }
        
        if video_output_path and os.path.exists(video_output_path):
            resultado["video_salida"] = os.path.basename(video_output_path)
        
        print(f"RESULTADO FINAL: {self.rep_count} repeticiones")
        
        return resultado