"""Pantalla en español sobre la API original, sin cambiar la inferencia."""
from pathlib import Path
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from api_solar import app

WEB = Path(__file__).resolve().parent / 'interfaz'
app.mount('/interfaz', StaticFiles(directory=WEB), name='interfaz')

@app.get('/', include_in_schema=False)
def inicio():
    return FileResponse(WEB / 'index.html')
