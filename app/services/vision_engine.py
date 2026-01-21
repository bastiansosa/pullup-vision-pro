"""
Motor de vision por computadora para deteccion de dominadas.
 Refactorizado del script original para funcionar en servidor.
"""
# math: funciones matematicas como sqrt, acos, degrees
# typing: para definir tipos de datos en las funciones
# numpy: para manejar arrays e imagenes
# mediapipe: la libreria de Google para deteccion de poses
# structlog: para logging estructurado
# dataclasses: para crear clases simples de datos
import math
from typing import Dict, List, Tuple, Optional
import numpy as np
import mediapipe as mp
import structlog
from dataclasses import dataclass


# Obtener un logger con el nombre del modulo actual
logger = structlog.get_logger(__name__)


# ===========================================
# CLASE Repeticion
# ===========================================

# @dataclass es un decorador que crea automaticamente
# los metodos __init__, __repr__, __eq__, etc.
# Es como una clase pero mas corta de escribir
@dataclass
class Repeticion:
    """Representa una repeticion detectada."""
    # Cada atributo con su tipo
    repeticion: int                 # Numero de la repeticion (1, 2, 3...)
    angulo_maximo: float            # Angulo mas abierto durante la repeticion
    angulo_minimo: float            # Angulo mas cerrado durante la repeticion
    timestamp: float                # En que frame/ tiempo se conto


# ===========================================
# CLASE VisionEngine
# ===========================================

class VisionEngine:
    """
    Motor de deteccion de poses para contar dominadas.
    
    Utiliza MediaPipe para detectar puntos corporales y calcula
    angulos para determinar la fase del ejercicio.
    """
    
    # Este es el metodo constructor, se ejecuta al crear una instancia
    def __init__(self, umbral_alto: float = 0.20, umbral_bajo: float = 0.30):
        """
        Inicializa el motor de vision.
        
        Args:
            umbral_alto: Valor Y para considerar "arriba"
            umbral_bajo: Valor Y para considerar "abajo"
        """
        # Inicializar MediaPipe Pose
        # Esto carga el modelo de deteccion de poses
        # static_image_mode=False porque procesamos video (no fotos sueltas)
        # model_complexity=1: 0=rapido pero menos preciso, 2=lento pero mas preciso
        # min_detection_confidence: cuanto confiar en que detecto una persona
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=1,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
        
        # Guardar las utilidades de MediaPipe para dibujar
        # Usaremos esto para dibujar el esqueleto en el video
        self.mp_drawing = mp.solutions.drawing_utils
        self.mp_drawing_styles = mp.solutions.drawing_styles
        
        # Guardar los umbrales que nos pasaron
        # Estos definen cuando esta arriba o abajo
        self.umbral_alto = umbral_alto
        self.umbral_bajo = umbral_bajo
        
        # Inicializar el estado del contador
        # LLamamos a reset() para tener valores iniciales
        self.reset()
        
        # Loguear que se inicio el motor
        logger.info("VisionEngine inicializado", 
                   umbral_alto=umbral_alto, 
                   umbral_bajo=umbral_bajo)
    
    # Metodo para resetear el estado
    def reset(self):
        """Resetea el estado interno del contador."""
        # Bandera que indica si esta en posicion alta (barbian arriba)
        self.en_posicion_alta = False
        # Contador de repeticiones
        self.contador_repeticiones = 0
        # Contador de frames procesados
        self.frame_count = 0
        # La ultima fase que detectamos
        self.ultima_fase = "BAJO"
        # Lista con el historial de todas las repeticiones
        self.historial_repeticiones: List[Repeticion] = []
        # Angulo y altura actuales
        self.angulo_actual = 0.0
        self.altura_actual = 0.0
        # Para tracking de angulos durante una repeticion
        self.angulo_maximo_durante_repeticion = 0.0
        self.angulo_minimo_durante_repeticion = 180.0
    
    # ===========================================
    # METODO: calcular_angulo_codo
    # ===========================================
    
    def calcular_angulo_codo(self, landmarks: List) -> float:
        """
        Calcula el angulo del codo.
        
        Args:
            landmarks: Lista de landmarks de MediaPipe
                Los landmarks son puntos del cuerpo que detecta MediaPipe
                Cada landmark tiene x, y, z (posicion)
            
        Returns:
            Angulo del codo en grados
        """
        # Si hay menos de 17 landmarks, no podemos calcular
        # Retornamos 180 (brazos extendidos = 180 grados)
        if len(landmarks) < 17:
            return 180.0
        
        # Obtener los 3 puntos relevantes para el angulo del codo
        # Landmark 11: Hombro izquierdo
        # Landmark 13: Codo
        # Landmark 15: Muñeca
        hombro = landmarks[11]  # Hombro izquierdo
        codo = landmarks[13]    # Codo
        muneca = landmarks[15]  # Muñeca
        
        # Calcular vectores desde el codo hacia el hombro y hacia la muneca
        # Vector 1: del codo al hombro
        v1 = (hombro.x - codo.x, hombro.y - codo.y)
        # Vector 2: del codo a la muneca
        v2 = (muneca.x - codo.x, muneca.y - codo.y)
        
        # Producto punto de los dos vectores
        # Esto nos ayuda a calcular el angulo entre ellos
        dot = v1[0] * v2[0] + v1[1] * v2[1]
        
        # Magnitud (longitud) de cada vector
        # Formula de distancia: sqrt(x^2 + y^2)
        mag1 = math.sqrt(v1[0]**2 + v1[1]**2)
        mag2 = math.sqrt(v2[0]**2 + v2[1]**2)
        
        # Si algn vector tiene longitud 0, no podemos calcular
        # Evitamos division por cero
        if mag1 * mag2 == 0:
            return 180.0
        
        # Calcular coseno del angulo usando producto punto
        cos_angle = dot / (mag1 * mag2)
        
        # El coseno puede dar valores fuera de -1 a 1 por errores de precision
        # Lo clampiamos para evitar errores en acos
        cos_angle = max(-1.0, min(1.0, cos_angle))
        
        # Convertir de radianes a grados
        # math.acos da el angulo en radianes
        return math.degrees(math.acos(cos_angle))
    
    # ===========================================
    # METODO: calcular_altura_hombros
    # ===========================================
    
    def calcular_altura_hombros(self, landmarks: List) -> float:
        """
        Calcula la altura normalizada de los hombros.
        
        Args:
            landmarks: Lista de landmarks de MediaPipe
            
        Returns:
            Altura normalizada (0 = arriba, 1 = abajo)
            Esto funciona porque MediaPipe normaliza las coordenadas
            donde y=0 es el top de la imagen y y=1 es el bottom
        """
        # Si hay menos de 13 landmarks, retornar valor por defecto
        if len(landmarks) < 13:
            return 0.5
        
        # Obtener ambos hombros
        hombro_izq = landmarks[11]
        hombro_der = landmarks[12]
        
        # Calcular el promedio de la altura de ambos hombros
        # Esto nos da un valor unico que representa la posicion del cuerpo
        altura_promedio = (hombro_izq.y + hombro_der.y) / 2
        
        return altura_promedio
    
    # ===========================================
    # METODO: detectar_fase
    # ===========================================
    
    def detectar_fase(self, landmarks: List) -> str:
        """
        Detecta la fase actual de la dominada.
        
        Args:
            landmarks: Lista de landmarks de MediaPipe
            
        Returns:
            Fase detectada: "ALTO", "BAJO" o "TRANSICION"
            "ALTO": barbian arriba (hombros cerca de la barra)
            "BAJO": colgado (hombros lejos de la barra)
            "TRANSICION": en medio de las dos posiciones
        """
        # Si no hay landmarks o son muy pocos
        if not landmarks or len(landmarks) < 33:
            return "SIN_DETECCION"
        
        # Calcular altura y angulo
        altura = self.calcular_altura_hombros(landmarks)
        angulo = self.calcular_angulo_codo(landmarks)
        
        # Guardar como valores actuales para uso posterior
        self.altura_actual = altura
        self.angulo_actual = angulo
        
        # Actualizar angulos extremos durante esta repeticion
        # Esto nos sirve para analytics despues
        self.angulo_maximo_durante_repeticion = max(
            self.angulo_maximo_durante_repeticion, angulo
        )
        self.angulo_minimo_durante_repeticion = min(
            self.angulo_minimo_durante_repeticion, angulo
        )
        
        # Detectar fase basada en altura de hombros
        # Recordar: y=0 es arriba, y=1 es abajo
        # Si altura es MENOR a umbral_alto -> esta ARRIBA
        if altura < self.umbral_alto:
            return "ALTO"
        # Si altura es MAYOR a umbral_bajo -> esta ABAJO
        elif altura > self.umbral_bajo:
            return "BAJO"
        # Esta en medio
        else:
            return "TRANSICION"
    
    # ===========================================
    # METODO: procesar_frame
    # ===========================================
    
    def procesar_frame(self, frame_rgb: np.ndarray) -> Tuple[bool, str]:
        """
        Procesa un frame y actualiza el conteo.
        
        Args:
            frame_rgb: Frame en formato RGB (no BGR)
                OpenCV lee imagenes en BGR, MediaPipe necesita RGB
                Por eso convertimos antes de pasar aqui
            
        Returns:
            Tupla (nueva_repeticion, fase_actual)
            nueva_repeticion: True si se conto una nueva repeticion
            fase_actual: La fase detectada en este frame
        """
        # Procesar con MediaPipe
        # Esto devuelve las coordenadas de todos los puntos del cuerpo
        resultados = self.pose.process(frame_rgb)
        
        # Si no detecto ninguna persona
        if not resultados.pose_landmarks:
            return False, "SIN_DETECCION"
        
        # Obtener los landmarks
        landmarks = resultados.pose_landmarks.landmark
        
        # Detectar en que fase estamos
        fase = self.detectar_fase(landmarks)
        
        # Variable para saber si contamos una nueva repeticion
        nueva_repeticion = False
        
        # Si estamos en ALTO y veniamos de BAJO o TRANSICION
        # Y no habiamos marcado que estamos en posicion alta
        if fase == "ALTO" and self.ultima_fase in ["BAJO", "TRANSICION"]:
            if not self.en_posicion_alta:
                # Marcar que estamos en posicion alta
                self.en_posicion_alta = True
                # Aumentar el contador
                self.contador_repeticiones += 1
                
                # Crear objeto Repeticion y guardar en historial
                repeticion = Repeticion(
                    repeticion=self.contador_repeticiones,
                    angulo_maximo=self.angulo_maximo_durante_repeticion,
                    angulo_minimo=self.angulo_minimo_durante_repeticion,
                    timestamp=self.frame_count
                )
                self.historial_repeticiones.append(repeticion)
                
                # Resetear los contadores de angulos para la prox repeticion
                self.angulo_maximo_durante_repeticion = 0.0
                self.angulo_minimo_durante_repeticion = 180.0
                
                # Marcar que fue una nueva repeticion
                nueva_repeticion = True
                
                # Loguear
                logger.info("Repeticion detectada", 
                           repeticion=self.contador_repeticiones)
        
        # Si pasamos a BAJO, ya no estamos en posicion alta
        if fase == "BAJO":
            self.en_posicion_alta = False
        
        # Actualizar la ultima fase
        self.ultima_fase = fase
        # Aumentar contador de frames
        self.frame_count += 1
        
        return nueva_repeticion, fase
    
    # ===========================================
    # METODO: obtener_estadisticas
    # ===========================================
    
    def obtener_estadisticas(self) -> Dict:
        """
        Obtiene las estadisticas actuales.
        
        Returns:
            Diccionario con todas las estadisticas
        """
        # Retornar un diccionario con toda la info
        return {
            "repeticiones": self.contador_repeticiones,
            "fase_actual": self.ultima_fase,
            "angulo_actual": round(self.angulo_actual, 1),
            "altura_actual": round(self.altura_actual, 3),
            "frames_procesados": self.frame_count,
            "historial": [
                {
                    "repeticion": r.repeticion,
                    "angulo_maximo": round(r.angulo_maximo, 1),
                    "angulo_minimo": round(r.angulo_minimo, 1)
                }
                for r in self.historial_repeticiones
            ]
        }
    
    # ===========================================
    # METODO: liberar_recursos
    # ===========================================
    
    def liberar_recursos(self):
        """Libera los recursos de MediaPipe."""
        # Cerrar el modelo de MediaPipe
        # Esto libera memoria
        self.pose.close()
        logger.info("VisionEngine recursos liberados")