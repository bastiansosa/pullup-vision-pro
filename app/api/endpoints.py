from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
import os
from app.services.vision_engine import VisionEngine

router = APIRouter()

# Inicializar motor de vision una sola vez
vision_engine = VisionEngine()

@router.post("/analizar")
async def analisar_video(file: UploadFile = File(...)):
    """
    Analiza un video de dominadas.
    """
    # Guardar archivo temporalmente
    temp_path = f"temp_{file.filename}"
    with open(temp_path, "wb") as f:
        content = await file.read()
        f.write(content)
    
    try:
        # CAMBIO CLAVE: generar_video=True para guardar el video con landmarks
        resultado = vision_engine.procesar_video(temp_path, generar_video=True)
        
        return resultado
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Borrar archivo temporal
        if os.path.exists(temp_path):
            os.remove(temp_path)


@router.get("/video/{filename}")
async def obtener_video(filename: str):
    """
    Obtiene el video procesado para mostrarlo en el navegador.
    """
    video_path = f"static/videos/{filename}"
    
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=filename
    )


@router.get("/descargar/{filename}")
async def descargar_video(filename: str):
    """
    Descarga el video procesado.
    """
    video_path = f"static/videos/{filename}"
    
    if not os.path.exists(video_path):
        raise HTTPException(status_code=404, detail="Video no encontrado")
    
    return FileResponse(
        path=video_path,
        media_type="video/mp4",
        filename=f"analisis_{filename}"
    )