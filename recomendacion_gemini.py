"""Recomendaciones textuales con Gemini basadas solo en la salida del clasificador.

No se envían fotografías ni claves al navegador ni a Gemini. Las decisiones de
prioridad y acción se calculan mediante reglas auditables; Gemini explica y
propone pasos para que un responsable de O&M los revise.
"""

import json
import logging
import os

import httpx

logger = logging.getLogger("solarscan.gemini")

ACCIONES = {
    "Bird-drop": ("Limpieza programada", "Media"),
    "Clean": ("Seguimiento", "Baja"),
    "Dusty": ("Limpieza programada", "Media"),
    "Electrical-damage": ("Inspección técnica", "Alta"),
    "Physical-Damage": ("Inspección técnica", "Alta"),
    "Snow-Covered": ("Seguimiento", "Media"),
}

ETIQUETAS = {
    "Bird-drop": "Excrementos de aves",
    "Clean": "Panel aparentemente limpio",
    "Dusty": "Polvo acumulado",
    "Electrical-damage": "Indicios visuales de posible daño eléctrico",
    "Physical-Damage": "Posible daño físico",
    "Snow-Covered": "Cubierto de nieve",
}

RESPONSE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "resumen": {"type": "STRING"},
        "justificacion": {"type": "STRING"},
        "pasos": {"type": "ARRAY", "items": {"type": "STRING"}},
    },
    "required": ["resumen", "justificacion", "pasos"],
}


class GeminiNoDisponible(Exception):
    """La respuesta del proveedor no pudo utilizarse de forma segura."""

    def __init__(self, mensaje, status_code=503):
        super().__init__(mensaje)
        self.status_code = status_code


def decision_para(clase, revision_humana):
    accion, prioridad = ACCIONES[clase]
    if revision_humana and prioridad == "Baja":
        prioridad = "Media"
    return accion, prioridad


async def consultar_gemini(clase, confianza, revision_humana):
    """Retorna un JSON validado sin permitir que el LLM altere la prioridad."""
    clave = os.environ.get("GEMINI_API_KEY", "").strip()
    if not clave:
        raise GeminiNoDisponible("Falta configurar GEMINI_API_KEY en Render.")

    modelo = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash-lite")
    # El identificador del modelo proviene solo de la configuración del servidor.
    if not modelo.replace("-", "").replace(".", "").isalnum():
        raise GeminiNoDisponible("El modelo Gemini configurado no es válido.")

    accion, prioridad = decision_para(clase, revision_humana)
    prompt = (
        "Eres un asistente prudente para un supervisor de operación y mantenimiento "
        "de paneles fotovoltaicos. NO has visto la fotografía: únicamente recibes "
        "el resultado de un clasificador de imágenes. No inventes grietas, puntos "
        "calientes, mediciones eléctricas, pérdidas energéticas ni urgencias no "
        "observadas. El puntaje de confianza NO está calibrado y no equivale a "
        "probabilidad real de acierto. No confirmes fallas eléctricas. Responde en "
        "español chileno claro y profesional, sin tecnicismos excesivos. "
        "Entrega un resumen de máximo 35 palabras, una justificación de máximo "
        "60 palabras y 2 o 3 pasos concretos, cada uno de máximo 20 palabras. "
        "No recomiendes intervenciones eléctricas por personal no calificado. "
        "La recomendación de acción y prioridad se determina por reglas del "
        "sistema y NO debes contradecirlas. Ante baja confianza o daño visible, "
        "destaca la validación humana.\n"
        + json.dumps(
            {
                "condicion_visual": ETIQUETAS[clase],
                "confianza_modelo": round(confianza, 4),
                "requiere_revision_humana": revision_humana,
                "accion_predefinida": accion,
                "prioridad_predefinida": prioridad,
            }, ensure_ascii=False
        )
    )
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": RESPONSE_SCHEMA,
            "temperature": 0.2,
            "maxOutputTokens": 800,
        },
    }
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{modelo}:generateContent"

    try:
        async with httpx.AsyncClient(timeout=28.0) as client:
            respuesta = await client.post(
                url,
                headers={"x-goog-api-key": clave, "Content-Type": "application/json"},
                json=payload,
            )
        if respuesta.status_code == 429:
            raise GeminiNoDisponible("Se alcanzó temporalmente el límite de Gemini. Intenta más tarde.", 429)
        if respuesta.status_code >= 400:
            logger.warning("Gemini devolvió HTTP %s", respuesta.status_code)
            raise GeminiNoDisponible("Gemini no respondió correctamente. Revisa la clave y los límites de uso.")

        contenido = respuesta.json()["candidates"][0]["content"]["parts"]
        texto = "".join(p.get("text", "") for p in contenido)
        generado = json.loads(texto)
        if not isinstance(generado, dict):
            raise ValueError("Respuesta no es un objeto JSON")
        resumen = generado["resumen"]
        justificacion = generado["justificacion"]
        pasos = generado["pasos"]
        if (
            not isinstance(resumen, str) or not 10 <= len(resumen) <= 500
            or not isinstance(justificacion, str) or not 10 <= len(justificacion) <= 800
            or not isinstance(pasos, list) or not 2 <= len(pasos) <= 3
            or not all(isinstance(p, str) and 5 <= len(p) <= 300 for p in pasos)
        ):
            raise ValueError("Estructura de respuesta inválida")
    except GeminiNoDisponible:
        raise
    except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Respuesta de Gemini inválida o inaccesible: %s", type(exc).__name__)
        raise GeminiNoDisponible("No fue posible generar la recomendación en este momento.") from exc

    return {
        "fuente": "Gemini",
        "modelo": modelo,
        "accion": accion,
        "prioridad": prioridad,
        "resumen": resumen.strip(),
        "justificacion": justificacion.strip(),
        "pasos": [p.strip() for p in pasos],
        "revision_humana": revision_humana,
        "advertencia": "Orientación preliminar: validar en terreno antes de intervenir.",
    }
