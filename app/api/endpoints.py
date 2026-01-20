from fastapi import APIRouter, UploadFile, File, Query, HTTPException
from fastapi.responses import FileResponse
from typing import Optional
import os
from app.services.vision_engine import VisionEngine

# Creo el router para los endpoints de video
router = APIRouter()

# Inicializo el motor de vision una sola vez
vision_engine = VisionEngine()

@router.post("/analizar-video")
async def analizar_video(
    file: UploadFile = File(...),
    # Parametros opcionales con valores por defecto que funcionan conmigo
    alt_max_y: float = Query(default=0.35, description="Umbral superior de hombros (0-1)"),
    alt_min_y: float = Query(default=0.55, description="Umbral inferior de hombros (0-1)"),
    generar_video: bool = Query(default=True, description="Generar video con analisis")
):
    """
    Analiza un video de dominadas.
    
    Parameters:
    - file: El video que quiere analizar
    - alt_max_y: Umbral superior de hombros (posicion arriba)
    - alt_min_y: Umbral inferior de hombros (posicion abajo)
    - generar_video: Si True, genera video con analisis
    
    Para ajustar los umbrales:
    - Prueba con valores pequenos (0.3-0.4) si no detecta repeticiones
    - Aumenta los valores (0.4-0.6) si detecta demasadas repeticiones
    """
    # Valido que los parametros esten en el rango correcto
    if not 0 < alt_max_y < 1:
        raise HTTPException(status_code=400, detail="alt_max_y debe estar entre 0 y 1")
    if not 0 < alt_min_y < 1:
        raise HTTPException(status_code=400, detail="alt_min_y debe estar entre 0 y 1")
    if alt_max_y >= alt_min_y:
        raise HTTPException(status_code=400, detail="alt_max_y debe ser menor que alt_min_y")
    
    # Guardo el archivo temporalmente porque FastAPI lo recibe en memoria
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        f.write(await file.read())
    
    try:
        # Configuro los parametros de hombros que me mando el usuario
        vision_engine.set_shoulder_config(alt_max_y, alt_min_y)
        
        # Proceso el video con la configuracion nueva
        resultado = vision_engine.procesar_video(
            temp_path,
            generar_video=generar_video
        )
        
        return resultado
        
    except Exception as e:
        # Si hay un error, lo devuelvo como HTTPException
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Siempre borro el archivo temporal, asi haya error o no
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/descargar-video/{filename}")
async def descargar_video(filename: str):
    """
    Descarga el video procesado con el analisis.
    
    Args:
        filename: El nombre del archivo que quiere descargar
    """
    video_path = f"static/videos/{filename}"
    
    # Verifico que exista el archivo
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    # Devuelvo el archivo para que el usuario lo pueda descargar
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=filename
    )