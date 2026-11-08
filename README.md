# SolarScan: servicio de clasificación visual

## Alcance
Servicio Python para clasificar una imagen en seis condiciones visuales. Devuelve clase, puntaje de confianza, probabilidades, indicador de revisión humana, UUID de inspección y versión del modelo. Incorpora recomendaciones orientativas de Gemini **cuando se configura una clave de API**. La aplicación pública también se conecta con n8n para avisos por Gmail y registro de inspecciones, como se explica en [CONFIGURAR_N8N.md](CONFIGURAR_N8N.md). El flujo ampliado del Hito 1 (formulario, WhatsApp y Google Sheets) está **en preparación**, aún sin activar. No confirma fallas eléctricas ni mide pérdidas de generación.

El notebook genera este directorio con los pesos reales de su sesión. El archivo .ipynb por sí solo contiene código y resultados visibles, no los pesos .pt. Conservar el ZIP del servicio descargado al finalizar la nueva sección.

## Ejecución local
Recomendado: Python 3.12, entorno virtual y CPU. Desde este directorio:

```bash
python -m venv .venv
```
Activar el entorno (`.venv\Scripts\activate` en Windows o `source .venv/bin/activate` en Linux/macOS).

```bash
python -m pip install -r requirements.txt
python -m uvicorn interfaz_solar:app --host 127.0.0.1 --port 8000
```
Abrir http://127.0.0.1:8000/ para utilizar la interfaz o `/docs` para probar la API. `/health` confirma que el modelo se cargó. El servidor carga los pesos una sola vez al iniciar; no entrena ni descarga el dataset.

## Actualizar GitHub y Render con recomendaciones de Gemini

1. Descomprimir `SolarScan_Gemini_Actualizacion.zip`. Subir a la **raíz** del repositorio `SolarScan` todos los archivos y la carpeta `interfaz/` del paquete, **manteniendo sus rutas**. Reemplazar los archivos existentes y confirmar el commit en `main`. No subir el archivo ZIP como único archivo; tampoco es necesario volver a subir los pesos `.pt` o el notebook.
2. En Render, servicio web SolarScan, ir a **Environment** y añadir la variable **`GEMINI_API_KEY`** con la clave obtenida en [Google AI Studio](https://aistudio.google.com/app/apikey). La clave nunca debe copiarse en GitHub, el código JS ni el README.
3. Opcional: añadir `GEMINI_MODEL=gemini-3.5-flash-lite`. Este es el modelo predeterminado del código. La disponibilidad y la cuota gratuita dependen de las condiciones vigentes de Gemini.
4. Guardar la variable, esperar el **redeploy** de Render y recargar el sitio con `Ctrl+F5`. Si el repositorio está vinculado con despliegue automático, cada commit en `main` inicia una nueva publicación. Verificar el estado **Live** en Render.
5. Analizar una foto: bajo las probabilidades aparece **Recomendación con Gemini**, con acción, prioridad, explicación y pasos sugeridos. Descargar resultado incorpora esas recomendaciones si Gemini ya terminó de responder.

**Importante:** Gemini recibe únicamente la categoría, confianza y bandera de revisión humana; la fotografía **no se envía** a Gemini. Acción y prioridad se asignan mediante reglas explícitas del servicio; Gemini redacta la explicación. Las recomendaciones no sustituyen inspección presencial ni procedimientos de seguridad eléctrica. El plan gratuito puede poner la instancia en reposo; la primera solicitud posterior puede demorar más. Ante falta de clave, cuota agotada o error del proveedor, la predicción de EfficientNet sigue funcionando.

La primera consulta puede fallar si la clave está restringida, el modelo no está disponible para tu cuenta o no hay cuota. Revisa los registros de Render sin revelar la clave. El endpoint de Gemini tiene un límite básico de ocho solicitudes por minuto por instancia para cuidar la cuota; es un prototipo público, no un servicio autenticado de producción.

## Contrato HTTP
`POST /predict`, cuerpo `multipart/form-data`, campo **file**. Se aceptan JPEG, PNG, WEBP y BMP estáticos. Máximo 15 MiB y 40 millones de píxeles. Se inspecciona el contenido real; la extensión y el MIME declarados no bastan. La verificación comprueba el archivo, no que la foto sea realmente de un panel solar.

```bash
curl -X POST http://127.0.0.1:8000/predict -F "file=@panel.jpg"
```

La respuesta 200 contiene `inspeccion_id`, `fecha_utc`, `modelo_version`, `clase`, `confianza`, `baja_confianza`, `revision_humana`, `probabilidades`, `nota` y `tiempo_servicio_ms`. La fecha usa UTC. El UUID identifica cada solicitud, no un panel físico. El tiempo no incluye la consulta posterior a Gemini, notificaciones ni todo el transporte HTTP.

| Código | Significado |
|---|---|
| 400 | Archivo vacío |
| 413 | Tamaño o resolución excesivos |
| 415 | Formato o animación no admitidos |
| 422 | Imagen ilegible o falta el campo file |
| 503 | Modelo no disponible |
| 500 | Fallo durante la predicción |

Los archivos temporales se eliminan tras la inferencia. La API no mantiene un historial local permanente; n8n guarda los eventos notificados en su tabla histórica y el flujo Hito 1 prevé replicarlos en Google Sheets. La confianza es un puntaje softmax no calibrado; el servicio conserva la política del modelo y no decide acciones físicas.

## Comprobaciones
`python -m pytest test_api.py -q` verifica el contrato y casos de error con un predictor simulado. No mide accuracy ni acredita el funcionamiento de los pesos reales. La sección adicional del notebook usa el modelo real y compara API frente a inferencia directa para una imagen de validación de cada clase. `verificacion_servicio.json` registra ese resultado solo después de pasar las comprobaciones.

`manifest_sha256.json` registra hashes de los archivos del paquete. El manifiesto permite comprobar integridad, no autentica al autor del modelo. Los requisitos de inferencia fijan versiones sin el sufijo local CUDA; `entorno_exportacion.json` conserva las versiones observadas en Colab. La instalación se debe verificar en el equipo de destino.

## Estado de la automatización (noviembre de 2026)

- **Producción confirmada:** SolarScan en Render → webhook autenticado de n8n → Gmail y tabla `SolarScan_Inspecciones`. Se recibió al menos un correo real con diagnóstico y pasos sugeridos; el webhook rechazó solicitudes antes de corregir su configuración, y esa incidencia está documentada.
- **Hito 1 en preparación:** existe en n8n un segundo flujo, `SolarScan - Hito 1`, con entrada por formulario, clasificación Python, nodo Gemini con salida JSON de cuatro campos, Gmail, WhatsApp por Twilio y doble registro (n8n y Google Sheets). **No se ha publicado ni probado de extremo a extremo**: faltan credenciales/autorización de Twilio y Google Sheets, y las tres evidencias reales.
- La publicación en Render no certifica entrega de mensajes ni una clasificación clínico-técnica definitiva; revisar ejecuciones y logs para cada prueba.

Consulta [docs/HITO1_EVIDENCIAS.md](docs/HITO1_EVIDENCIAS.md) para arquitectura, métricas, preparación de la demostración y pendientes.

## Comparación contra un método simple

En un conjunto interno de **117 imágenes de prueba** registrado en `config.json`, EfficientNet-B0 obtuvo **accuracy 60,68 %** y **F1 macro 57,65 %**; el método de *reglas simples* obtuvo **accuracy 41,88 %** y **F1 macro 38,23 %**. Es una mejora de 18,80 puntos porcentuales en accuracy, pero no implica fiabilidad industrial: hubo **46 clasificaciones erróneas** en prueba, incluidas **2 imágenes de daño real sin derivación humana**. La confianza softmax no está calibrada y el conjunto no demuestra generalización a nuevas plantas. La política exige revisión humana para confianza menor a 70 % y para clases de posible daño eléctrico o físico.

## Uso declarado de IA

Se utilizó IA generativa como asistencia en programación, documentación y redacción de recomendaciones; el procesamiento visual usa un modelo EfficientNet-B0 entrenado/evaluado por separado. La respuesta de Gemini interpreta **la predicción y su confianza**, no la foto; sus textos se limitan con reglas de prioridad y revisión humana. Los errores y límites se comunican explícitamente, y una persona debe validar cualquier intervención en terreno.
