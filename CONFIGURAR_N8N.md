# Activar notificaciones de SolarScan con n8n

Este cambio conecta la aplicación pública con el flujo **SolarScan - Alertas Gmail desde Render**. La clasificación y Gemini siguen funcionando como antes.

## 1. Configurar n8n

Abrir https://solarscan.app.n8n.cloud/workflow/PHdPeOczhVMpg2G0

1. Abrir el nodo **Recibir informe SolarScan**.
2. En **Authentication: Header Auth**, crear/asignar una credencial del tipo **Header Auth**:
   - **Name / Header Name:** `X-SolarScan-Token`
   - **Value:** inventar un secreto largo y aleatorio (guardar en un gestor de contraseñas).
   - El nombre de la *credencial* es libre. El nombre del *header* debe ser exactamente el indicado.
3. Abrir **Enviar aviso por Gmail** dentro del grupo **Decisión y notificación**. Crear/asignar la conexión de Google Gmail OAuth e iniciar sesión. Destinatario del flujo: `mikugonza4@gmail.com`.
4. Confirmar que el nodo **Registrar inspección** esté conectado a la tabla `SolarScan_Inspecciones`.
5. Guardar, revisar las alertas rojas y **Publicar/Activar** el workflow cuando esté listo.

**No subir claves ni tokens a GitHub ni compartir capturas que los muestren.**

## 2. Configurar Render

En el servicio existente **SolarScan** (no crear uno nuevo), abrir **Environment** y añadir dos variables:

| Clave | Valor |
| --- | --- |
| `N8N_WEBHOOK_URL` | `https://solarscan.app.n8n.cloud/webhook/solarscan/alertas-v1` |
| `N8N_WEBHOOK_TOKEN` | El mismo secreto definido en la credencial Header Auth de n8n |

Conservar `GEMINI_API_KEY` y el resto de las variables existentes. Guardar para que Render implemente el cambio de configuración.

## 3. Comprobar de extremo a extremo

1. Abrir https://solarscan-zuqf.onrender.com
2. Analizar una foto de panel con polvo y esperar el resultado de **Recomendación con Gemini**.
3. En n8n abrir **Ejecuciones** y verificar que el webhook recibió `inspeccion_id`, `clase`, `confianza` y `recomendacion`.
4. Revisar el correo de `mikugonza4@gmail.com` y el registro de inspección en la Data Table.
5. Probar también **Clean**: debe registrarse, pero sin enviar correo salvo que las reglas de revisión humana indiquen alerta.

## Qué hace el código

- Solo genera el evento a partir de una predicción real y reciente del servidor cuando Gemini respondió.
- Envía a n8n la categoría, confianza, identificador, fecha, indicadores de revisión y texto de Gemini; **no envía fotografías**.
- Cada identificación se notifica como máximo una vez desde el proceso en ejecución.
- Usa HTTPS y un encabezado secreto almacenado exclusivamente en variables de entorno.
- Si faltan las variables, SolarScan sigue clasificando y recomendando normalmente; el webhook no se llama.
- El aviso se envía en segundo plano. Si n8n rechaza o falla la solicitud, se registra en los logs de Render. No hay reintento automático para evitar correos duplicados.

**Limitación del prototipo:** si Gemini devuelve error o llega al límite de solicitudes, no se crea evento en n8n para esa inspección. Las inspecciones en memoria pueden perderse si el servidor se reinicia; para fiabilidad operativa real habría que implementar una cola persistente.

## Seguridad

Esta integración no sustituye un criterio técnico profesional ni confirma el estado del panel. La API de Gemini debe mantenerse en Render como variable de entorno; si una clave aparece en una captura compartida, revocarla y crear otra.
