# SolarScan: servicio de clasificación visual

## Alcance
Servicio Python para clasificar una imagen en seis condiciones visuales. Devuelve clase, puntaje de confianza, probabilidades, indicador de revisión humana, UUID de inspección y versión del modelo. No incorpora n8n, un LLM, mensajería ni almacenamiento histórico. No confirma fallas eléctricas ni mide pérdidas de generación.

El notebook genera este directorio con los pesos reales de su sesión. El archivo .ipynb por sí solo contiene código y resultados visibles, no los pesos .pt. Conservar el ZIP del servicio descargado al finalizar la nueva sección.

## Ejecución local
Recomendado: Python 3.12, entorno virtual y CPU. Desde este directorio:

```bash
python -m venv .venv
```
Activar el entorno (`.venv\Scripts\activate` en Windows o `source .venv/bin/activate` en Linux/macOS).

```bash
python -m pip install -r requirements.txt
python -m uvicorn api_solar:app --host 127.0.0.1 --port 8000
```
Abrir http://127.0.0.1:8000/docs para probar una imagen. `/health` confirma que el modelo se cargó. El servidor carga los pesos una sola vez al iniciar; no entrena ni descarga el dataset.

## Contrato HTTP
`POST /predict`, cuerpo `multipart/form-data`, campo **file**. Se aceptan JPEG, PNG, WEBP y BMP estáticos. Máximo 15 MiB y 40 millones de píxeles. Se inspecciona el contenido real; la extensión y el MIME declarados no bastan. La verificación comprueba el archivo, no que la foto sea realmente de un panel solar.

```bash
curl -X POST http://127.0.0.1:8000/predict -F "file=@panel.jpg"
```

La respuesta 200 contiene `inspeccion_id`, `fecha_utc`, `modelo_version`, `clase`, `confianza`, `baja_confianza`, `revision_humana`, `probabilidades`, `nota` y `tiempo_servicio_ms`. La fecha usa UTC. El UUID identifica cada solicitud, no un panel físico. El tiempo no incluye LLM, notificaciones ni todo el transporte HTTP.

| Código | Significado |
|---|---|
| 400 | Archivo vacío |
| 413 | Tamaño o resolución excesivos |
| 415 | Formato o animación no admitidos |
| 422 | Imagen ilegible o falta el campo file |
| 503 | Modelo no disponible |
| 500 | Fallo durante la predicción |

Los archivos temporales se eliminan tras la inferencia. No se conserva un historial de inspecciones. La confianza es un puntaje softmax no calibrado; el servicio conserva la política del modelo y no decide acciones físicas.

## Comprobaciones
`python -m pytest test_api.py -q` verifica el contrato y casos de error con un predictor simulado. No mide accuracy ni acredita el funcionamiento de los pesos reales. La sección adicional del notebook usa el modelo real y compara API frente a inferencia directa para una imagen de validación de cada clase. `verificacion_servicio.json` registra ese resultado solo después de pasar las comprobaciones.

`manifest_sha256.json` registra hashes de los archivos del paquete. El manifiesto permite comprobar integridad, no autentica al autor del modelo. Los requisitos de inferencia fijan versiones sin el sufijo local CUDA; `entorno_exportacion.json` conserva las versiones observadas en Colab. La instalación se debe verificar en el equipo de destino.

## Estado previo a n8n
El paquete se prepara para ejecución local. No existe una URL pública ni se configura n8n. Para conectarlo posteriormente habrá que alojar el servicio en un entorno alcanzable desde n8n y configurar el transporte y el acceso. Este paquete no expone automáticamente ningún puerto a internet. El límite de archivo se verifica en la aplicación; un futuro despliegue deberá fijar también su límite de carga en el servidor de entrada.
