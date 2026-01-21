from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
import os
import tempfile
from app.services.vision_engine import VisionEngine
import io

router = APIRouter()

# Inicializar motor de vision una sola vez
vision_engine = VisionEngine()


@router.post("/analizar")
async def analisar_video(file: UploadFile = File(...)):
    """
    Analiza un video de dominadas y devuelve el resultado + video.
    """
    # Guardar archivo temporalmente
    temp_input = f"temp_input_{file.filename}"
    temp_output = f"temp_output_{file.filename}"
    
    with open(temp_input, "wb") as f:
        content = await file.read()
        f.write(content)
    
    try:
        # Procesar video con analisis
        resultado = vision_engine.procesar_video(temp_input, generar_video=True, output_filename=temp_output)
        
        if "error" in resultado:
            raise HTTPException(status_code=400, detail=resultado["error"])
        
        # Devolver resultado + video
        return {
            **resultado,
            "video_procesado": f"/api/v1/video/{temp_output}"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
    finally:
        # Limpiar archivos temporales
        if os.path.exists(temp_input):
            os.remove(temp_input)


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