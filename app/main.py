"""
Aplicación principal - PullUp Vision Pro
=========================================

API REST para análisis de videos de dominadas usando MediaPipe.
"""

# Importamos las herramientas basicas que necesitamos
import os              # Para operaciones con archivos y carpetas del sistema
import sys             # Para acceder a variables y funciones del sistema
from contextlib import asynccontextmanager  # Para manejar el ciclo de vida de la app
import structlog       # Para hacer logging estructurado (ver民生or lo que pasa)

# Añadir el directorio raíz al path de Python
# Esto nos permite importar modulos Relative como "from app.core.config import settings"
# Sin esto, Python no encontraria los paquetes dentro de la carpeta "app"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Importamos FastAPI, el framework principal para crear la API REST
from fastapi import FastAPI

# Middleware para habilitar CORS (Cross-Origin Resource Sharing)
# Esto permite que paginas web de otros dominios puedan hacer peticiones a nuestra API
from fastapi.middleware.cors import CORSMiddleware

# Para servir archivos estaticos (HTML, CSS, JS del frontend)
from fastapi.staticfiles import StaticFiles

# Para hacer redirecciones (enviar al usuario a otra URL)
from fastapi.responses import RedirectResponse

# Importamos la configuracion que living en core/config.py
from app.core.config import settings

# Importamos la funcion que configura el logging desde core/logging.py
from app.core.logging import setup_logging

# Importamos el router que creamos en api/endpoints.py
# Este router contiene todos los endpoints de la API
from app.api.endpoints import router


# Configurar logging al inicio de todo
# Esto es lo primero que hacemos para que todos los logs tengan el formato correcto
setup_logging()

# Creamos un logger para este modulo
# Lo usamos para registrar eventos importantes de la aplicacion
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestión del ciclo de vida de la aplicación.
    Se ejecuta al inicio y al cierre.
    
    Este es un decorador que nos permite ejecutar codigo:
    1. ANTES de que la app arranque (antes del yield)
    2. DESPUES de que la app termine (despues del yield)
    
    Es como decir "antes de empezar, haz esto" y "al terminar, haz esto otro".
    """
    # --- CODIGO QUE SE EJECUTA AL INICIAR ---
    # Registramos en los logs que la aplicacion esta arrancando
    logger.info("Iniciando aplicación",
               project=settings.PROJECT_NAME,
               version=settings.VERSION)
    
    # Creamos los directorios necesarios si no existen
    # Esto asegura que las carpetas para uploads y videos procesados existan
    os.makedirs(settings.get_upload_path(), exist_ok=True)
    os.makedirs(settings.get_processed_path(), exist_ok=True)
    
    # El "yield" divide las acciones de inicio y cierre
    # Todo lo de arriba pasa ANTES de que la app comience a recibir peticioneS
    yield
    
    # --- CODIGO QUE SE EJECUTA AL CERRAR ---
    # Esto pasa cuando la aplicacion se apaga (Ctrl+C, kill, etc.)
    logger.info("Cerrando aplicación")


# Crear aplicación FastAPI
# Esto es el corazon de nuestra API - sin esto, no hay nada
app = FastAPI(
    title=settings.PROJECT_NAME,           # Titulo que aparece en la documentacion
    description="""
    ## API de Análisis de Dominadas con Visión por Computadora
    
    Esta API utiliza MediaPipe para detectar y contar repeticiones de dominadas
    en videos de entrenamiento.
    
    ### Características:
    - Detección automática de fases (arriba/abajo)
    - Conteo preciso de repeticiones
    - Análisis de ángulos de codo
    - Videos anotados con overlay visual
    
    ### Uso:
    1. Subir un video de dominadas al endpoint `/api/v1/analizar`
    2. Recibir el conteo de repeticiones y estadísticas
    3. Descargar el video procesado con anotaciones
    """,
    version=settings.VERSION,              # Version desde config
    lifespan=lifespan,                     # Funcion que maneja inicio/cierre
    docs_url="/docs",                      # URL de la documentacion Swagger
    redoc_url="/redoc"                     # URL de la documentacion ReDoc
)

# Configurar CORS (Cross-Origin Resource Sharing)
# CORS es un mecanismo de seguridad que limita quienes pueden acceder a nuestra API
# Por defecto, los navegadores bloquean peticiones de dominios diferentes
# Aqui configuramos que dominios pueden acceder
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,  # Lista de dominios permitidos
    allow_credentials=True,                    # Permitir cookies/auth
    allow_methods=["*"],                       # Permitir todos los metodos (GET, POST, etc.)
    allow_headers=["*"],                       # Permitir todos los headers
)

# Montar archivos estáticos (frontend)
# Esto sirve los archivos HTML, CSS y JS que viven en la carpeta "app/static"
# Cuando alguien entra a /static/index.html, FastAPI busca el archivo ahi
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Incluir routers
# Aqui conectamos el router que creamos en api/endpoints.py
# Sin esta linea, nuestros endpoints no estarian accesibles
app.include_router(router, prefix="/api/v1")


@app.get("/", include_in_schema=False)
async def root():
    """Redirigir al frontend."""
    # Cuando alguien entra a la raiz de la API (/)
    # Lo redirigimos automaticamente a la pagina web (/static/index.html)
    return RedirectResponse(url="/static/index.html")


@app.exception_handler(Exception)
async def exception_handler(request, exc):
    """
    Manejador global de excepciones.
    
    Este decorador captura CUALQUIER error que no haya sido manejado antes.
    Es como un "plan B" - si algo falla y nadie lo intercepto, llega aqui.
    """
    # Registramos el error completo en los logs (incluye traceback)
    logger.error("Error no manejado", error=str(exc), traceback=True)
    
    # Devolvemos una respuesta de error al cliente
    # Si estamos en modo DEBUG, mostramos el detalle del error
    # Si estamos en produccion, ocultamos el detalle por seguridad
    return {
        "error": "Error interno del servidor",
        "detalle": str(exc) if settings.DEBUG else "Contacte al administrador",
        "timestamp": datetime.now().isoformat()
    }


# Importamos datetime al final para evitar problemas con los imports
from datetime import datetime


# Bloque que se ejecuta solo cuando corremos el archivo directamente
# python app/main.py
if __name__ == "__main__":
    # Importamos uvicorn, el servidor ASGI que ejecuta FastAPI
    import uvicorn
    
    # Arrancamos el servidor con uvicorn
    uvicorn.run(
        "app.main:app",              # Indica donde esta la app (modulo.clase)
        host=settings.HOST,          # En que IP escuchar (0.0.0.0 = todas)
        port=settings.PORT,          # En que puerto (por defecto 8000)
        reload=settings.DEBUG        # Recargar automaticamente al cambiar codigo
    )