# SolarScan — Hito 1: integración, rúbrica y evidencias

**Estado al 8 de noviembre de 2026:** preparación técnica avanzada, **no listo aún para dar por aprobadas las tres pruebas**. Este documento distingue lo comprobado de lo pendiente y sirve de guía para la demostración del 9–10 de noviembre.

## 1. Problema industrial, usuario y decisión (R7)

En una operación fotovoltaica, la suciedad, la nieve y los daños visibles pueden requerir acciones distintas. Un responsable de mantenimiento debe recibir un **triage visual preliminar**, asignar prioridad y programar limpieza o revisión técnica. El sistema no reemplaza una inspección en terreno ni estima producción perdida a partir de una sola fotografía.

- **Usuario:** supervisor o planificador de mantenimiento de una planta fotovoltaica.
- **Decisión:** seguimiento, limpieza programada, evaluación operativa o revisión técnica urgente.
- **Indicadores propuestos:** minutos entre carga de imagen y aviso recibido; porcentaje de inspecciones derivadas a revisión humana; número de eventos por clase y prioridad. **No se han estimado ahorros o ROI para este hito.**

## 2. Arquitectura del Hito 1 (R1, R2, R4, R6, R11)

Flujo separado **SolarScan - Hito 1** en n8n:

1. El formulario de n8n recibe una fotografía (disparador automático al enviarla).
2. n8n envía el archivo como `multipart/form-data` al servicio Python `POST /predict` de SolarScan en Render.
3. El servicio FastAPI procesa la imagen, ejecuta EfficientNet-B0 y responde con clase, confianza, probabilidades, UUID y política de revisión humana.
4. Un nodo **Gemini** recibe solo ese resultado visual y la decisión preventiva permitida. Se exige **JSON de cuatro cadenas**: `diagnostico`, `recomendacion`, `prioridad`, `justificacion`.
5. n8n valida los cuatro campos, limita afirmaciones técnicas y **envía el contenido de todas las inspecciones** tanto por **Gmail** como por **WhatsApp** (Twilio Sandbox durante la demostración).
6. n8n conserva un registro por inspección en `SolarScan_Inspecciones` y añade una fila en la planilla Google Sheets **SolarScan - Registro histórico de inspecciones**.

**Importante:** el flujo Hito 1 sigue **inactivo** hasta autorizar Twilio y Google Sheets y completar pruebas. El sistema público en Render tiene además **otro flujo independiente ya activo**, con Gmail y registro en n8n; no confundir sus pruebas con evidencia del flujo nuevo.

## 3. Datos y limpieza (R8)

- **Procedencia registrada:** dataset público de Kaggle `pythonafroz/solar-panel-images` (según `config.json`).
- **Seis clases:** `Bird-drop`, `Clean`, `Dusty`, `Electrical-damage`, `Physical-Damage`, `Snow-Covered`.
- **Preprocesamiento declarado:** interpretar orientación EXIF, convertir a RGB, ajustar con `ImageOps.pad` a **224 × 224**, normalización RGB con media/desviación estándar documentadas en `config.json`.
- **Partición:** los resultados visibles de validación y prueba están en `config.json`; el test contiene **117 ejemplos**. Semilla de entrenamiento: **42**.
- **Aspectos por comprobar en el informe definitivo:** enlace/cita y licencia específica de la versión del dataset, proporción exacta de train/validación/test, duplicados y estrategia de separación por panel o planta. El límite declarado es que un filtro pHash no garantiza independencia entre instalaciones.

## 4. Modelo y comparación con alternativa simple (R2, R4)

Se seleccionó un modelo **EfficientNet-B0**, CNN preentrenada adaptada a seis clases. En prueba, según `config.json`:

| Métrica | EfficientNet-B0 | Reglas simples |
| --- | ---: | ---: |
| Accuracy | 60,68 % | 41,88 % |
| Accuracy balanceada | 58,89 % | 44,30 % |
| F1 macro | 57,65 % | 38,23 % |
| Ejemplos de prueba | 117 | 117 |

La mejora de accuracy es **18,80 puntos porcentuales**; no se debe expresar como una precisión cercana al 100 %. La matriz de confusión contabiliza **46 errores de clasificación** de EfficientNet. Entre **22 casos de daño real**, seis no recibieron recomendación técnica y **dos quedaron sin derivación humana** según la evaluación operacional registrada. Son riesgos de falsos negativos que deben mencionarse durante la defensa.

Se obliga revisión humana si la confianza cae bajo **0,70** o si la clase es daño eléctrico/físico. La confianza softmax **no está calibrada**. Una fotografía aislada no puede diagnosticar fallas internas ni certificar seguridad eléctrica.

## 5. LLM y reglas de seguridad (R1)

**Entrada al LLM:** clase visual, confianza, bandera de revisión humana, prioridad permitida y acción permitida. La imagen en sí **no se transmite a Gemini** en el flujo Hito 1.

**Instrucción central del prompt:** "Produce exclusivamente un JSON válido con exactamente cuatro campos STRING: diagnostico, recomendacion, prioridad, justificacion. No certifiques fallas eléctricas, pérdida de generación o seguridad". El prompt exige coherencia con reglas preventivas y una justificación breve.

**Ejemplo de formato esperado, no sustituye una ejecución real:**

```json
{
  "diagnostico": "Se observa posible acumulación de polvo superficial.",
  "recomendacion": "Programar limpieza de los módulos y verificar resultados.",
  "prioridad": "MEDIA",
  "justificacion": "La categoría visual indica suciedad; confirmar en terreno antes de intervenir."
}
```

Las reglas de negocio en n8n establecen la prioridad que se envía y no permiten que una salida del LLM reduzca la revisión requerida por el clasificador.

## 6. Estado de notificaciones y persistencia (R6, R11)

- **Confirmado en producción anterior:** Gmail recibió un correo real con ID de inspección, clase, confianza, prioridad, resumen de Gemini y pasos; el evento quedó registrado en n8n.
- **Implementado en el nuevo flujo Hito 1, pendiente de activar:** notificación Gmail por cada inspección, nodo Twilio WhatsApp, tabla histórica n8n y Google Sheets.
- **Google Sheets:** planilla creada con 13 columnas (`inspeccion_id`, fecha, clase, confianza, prioridad, diagnóstico, recomendación, justificación, revisión humana, notificar, versión del modelo y estado de los dos canales). Su nodo de n8n necesita autorización **Google Sheets OAuth2**. Los campos de canal se registran como **pendientes de comprobación** y nunca se presentan falsamente como entrega confirmada.
- **WhatsApp:** requiere credencial **Twilio Account SID/Auth Token** configurada de forma privada en n8n y número de destino con formato internacional. Para la demo se puede usar **Twilio Sandbox**, cuya conversación de prueba tiene restricciones de ventana de 24 h y de inscripción. No se considera funcional hasta recibir un mensaje auténtico en el teléfono.
- **Robustez:** FastAPI valida tipo/tamaño de archivo y devuelve errores HTTP; n8n valida clases, rango de confianza y salida JSON; cualquier fallo de autorización se detecta revisando ejecuciones y logs. No se promete tolerancia industrial a caídas o exactamente-una-vez.

## 7. Tres escenarios obligatorios de prueba

Ejecutar el **formulario del nuevo flujo Hito 1** con **tres imágenes diferentes** que no sean duplicados de entrenamiento, guardar el identificador de inspección y capturas legibles de cada etapa.

| Escenario | Resultado visual buscado | Qué comprobar |
| --- | --- | --- |
| 1. Panel con polvo | `Dusty` | Prioridad media y limpieza programada |
| 2. Panel limpio | `Clean` | Seguimiento y **también** mensajes por Gmail y WhatsApp |
| 3. Posible daño | `Physical-Damage` o `Electrical-damage` | Prioridad alta y revisión humana indicada |

En **cada una de las tres**: capturar (a) ejecución exitosa en n8n, (b) correo recibido en Gmail, (c) mensaje en WhatsApp y (d) la nueva fila en la hoja. No anticipar ni inventar clasificaciones: anotar lo que salga realmente. Si una foto no produce la categoría esperada, documentar el error o elegir otro caso y conservar la evidencia de la prueba.

## 8. Entregables del 9–10 noviembre (Hito 1)

- [ ] Exportación **JSON del nuevo workflow Hito 1** sin credenciales/tokens, y captura del canvas completo.
- [ ] Código Python entregable y comentado (`interfaz_solar.py`, módulos de inferencia y notebook de entrenamiento que sustenta las métricas).
- [ ] Informe de **máximo 6 páginas**: problema/usuario, datos, diagrama, modelo vs. simple, prompt+JSON real, limitaciones.
- [ ] Presentación de **7 minutos** y demostración en vivo del flujo automatizado. La rúbrica adicional de la **app web** pide una exposición de 10 minutos: verificar con el docente si es entrega separada.
- [ ] **Tres ejecuciones exitosas con datos diferentes**, con capturas de n8n, Gmail y WhatsApp.
- [ ] Conexiones privadas autorizadas y prueba de que Sheets recibe la fila correcta.
- [ ] Confirmación de que ningún token, número personal o clave está en código, captura o exportación.

### Distribución sugerida de 7 minutos

- **0:00–0:55:** problema industrial, supervisor y KPI.
- **0:55–1:55:** origen y preparación de datos; seis clases.
- **1:55–3:05:** EfficientNet vs. reglas; métricas y falsos negativos.
- **3:05–3:55:** prompt, salida JSON, decisión y límites.
- **3:55–6:15:** recorrido de n8n y demo con correo, WhatsApp y registro.
- **6:15–7:00:** conclusiones, riesgos y controles humanos.

## 9. Para el Hito 2, no para esta entrega

Series temporales, Transformer/NLP, tablero, ROI y aprobación humana automatizada están marcados para **16–17 de noviembre**. No son condición obligatoria del Hito 1, aunque el control de riesgos debe explicarse.

**Última actualización técnica:** infraestructura pública y correo de producción ya verificados; el nuevo flujo Hito 1 todavía debe completar autorización de WhatsApp/Sheets, publicación y tres pruebas. Este documento es preparación, **no evidencia de ejecución exitosa**.
