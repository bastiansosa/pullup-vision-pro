"""
Tests unitarios para el motor de visión.
"""
import pytest
import numpy as np
from app.services.vision_engine import VisionEngine


class TestVisionEngine:
    """Tests para VisionEngine."""
    
    @pytest.fixture
    def engine(self):
        """Crea una instancia del motor para cada test."""
        return VisionEngine(umbral_alto=0.20, umbral_bajo=0.30)
    
    def test_inicializacion(self, engine):
        """Test que el motor se inicializa correctamente."""
        assert engine.contador_repeticiones == 0
        assert engine.frame_count == 0
        assert engine.ultima_fase == "BAJO"
    
    def test_calcular_altura_hombros_con_landmarks_validos(self, engine):
        """Test cálculo de altura con landmarks válidos."""
        # Crear landmarks mock con hombros en posición media
        landmarks = type('Landmark', (), {
            '11': type('Point', (), {'y': 0.35})(),  # Hombro izq
            '12': type('Point', (), {'y': 0.35})()   # Hombro der
        })()
        
        # Simular comportamiento de lista
        landmarks_list = [
            None, None, None, None, None, None, None, None, None, None, None,
            type('Point', (), {'y': 0.35})(),
            type('Point', (), {'y': 0.35})()
        ]
        
        altura = engine.calcular_altura_hombros(landmarks_list)
        assert altura == 0.35
    
    def test_calcular_altura_hombros_con_pocos_landmarks(self, engine):
        """Test que retorna valor por defecto con pocos landmarks."""
        landmarks = [None] * 10  # Menos de 13 landmarks
        altura = engine.calcular_altura_hombros(landmarks)
        assert altura == 0.5  # Valor por defecto
    
    def test_detectar_fase_sin_landmarks(self, engine):
        """Test que retorna SIN_DETECCION sin landmarks."""
        fase = engine.detectar_fase(None)
        assert fase == "SIN_DETECCION"
    
    def test_detectar_fase_con_pocos_landmarks(self, engine):
        """Test que retorna SIN_DETECCION con pocos landmarks."""
        fase = engine.detectar_fase([None] * 20)
        assert fase == "SIN_DETECCION"
    
    def test_reset(self, engine):
        """Test que reset limpia el estado."""
        # Simular algunas repeticiones
        engine.contador_repeticiones = 5
        engine.frame_count = 100
        engine.historial_repeticiones.append("mock")
        
        engine.reset()
        
        assert engine.contador_repeticiones == 0
        assert engine.frame_count == 0
        assert engine.historial_repeticiones == []
    
    def test_obtener_estadisticas(self, engine):
        """Test que retorna estadísticas correctamente."""
        stats = engine.obtener_estadisticas()
        
        assert "repeticiones" in stats
        assert "fase_actual" in stats
        assert "angulo_actual" in stats
        assert "altura_actual" in stats
        assert "frames_procesados" in stats
        assert "historial" in stats


class TestAPI:
    """Tests para la API."""
    
    @pytest.fixture
    def client(self):
        """Crea cliente de test."""
        from fastapi.testclient import TestClient
        from app.main import app
        return TestClient(app)
    
    def test_health_endpoint(self, client):
        """Test endpoint de salud."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data
    
    def test_root_endpoint(self, client):
        """Test endpoint raíz."""
        response = client.get("/")
        # Debe redirigir al frontend
        assert response.status_code in [200, 302]
    
    def test_invalid_file_type(self, client):
        """Test que rechaza tipos de archivo inválidos."""
        from io import BytesIO
        response = client.post(
            "/api/v1/analizar",
            files={"file": ("test.txt", BytesIO(b"test"), "text/plain")}
        )
        assert response.status_code == 400