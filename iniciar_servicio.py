"""Prepara un entorno local y arranca la API original sin entrenar el modelo."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent

def main():
    os.chdir(ROOT)
    for name, expected in json.loads((ROOT / 'manifest_sha256.json').read_text()).items():
        if hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != expected:
            raise RuntimeError('Archivo original modificado o incompleto: ' + name)
    env = ROOT / '.venv'
    python = env / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not python.exists():
        subprocess.run([sys.executable, '-m', 'venv', str(env)], check=True)
    req = ROOT / 'requirements.txt'
    digest = hashlib.sha256(req.read_bytes()).hexdigest()
    stamp = env / 'solarscan_requirements.sha256'
    if not stamp.exists() or stamp.read_text() != digest:
        print('Instalando dependencias originales. La primera vez puede tardar.', flush=True)
        subprocess.run([str(python), '-m', 'pip', 'install', '-r', str(req)], check=True)
        stamp.write_text(digest)
    process = subprocess.Popen([str(python), '-m', 'uvicorn', 'interfaz_solar:app', '--host', '127.0.0.1', '--port', '8000'], cwd=ROOT)
    try:
        ready = False
        for _ in range(120):
            if process.poll() is not None:
                raise RuntimeError('El servidor terminó antes de iniciar. Revisa los mensajes anteriores.')
            try:
                with urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2) as response:
                    ready = json.load(response).get('estado') == 'listo'
                if ready:
                    break
            except Exception:
                pass
            time.sleep(1)
        if not ready:
            raise RuntimeError('El modelo no está listo. Revisa el error de carga mostrado arriba.')
        print('Modelo listo. Se abre la página para probar una imagen. Mantén esta ventana abierta.', flush=True)
        print('Servicio LOCAL: todavía no está conectado a n8n Cloud. Ctrl+C para detenerlo.', flush=True)
        webbrowser.open('http://127.0.0.1:8000/')
        process.wait()
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nServicio detenido.')
    except Exception as exc:
        print('ERROR:', exc)
        sys.exit(1)
