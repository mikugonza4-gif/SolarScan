"""Pruebas offline: la clave no se expone y el modelo visual sigue funcionando."""

import asyncio

import httpx

from fastapi.testclient import TestClient

import api_solar
import recomendacion_gemini
from recomendacion_gemini import decision_para


def test_acciones_auditables():
    assert decision_para("Dusty", False) == ("Limpieza programada", "Media")
    assert decision_para("Electrical-damage", True) == ("Inspección técnica", "Alta")
    assert decision_para("Clean", False) == ("Seguimiento", "Baja")
    assert decision_para("Clean", True) == ("Seguimiento", "Media")


def test_sin_clave_informa_sin_interferir(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with TestClient(api_solar.create_app(predictor=lambda _: None)) as client:
        result = client.post("/recommend", json={
            "inspeccion_id": "ensayo-1", "clase": "Dusty", "confianza": .997,
            "revision_humana": False,
        })
        assert result.status_code == 503
        assert "GEMINI_API_KEY" in result.text


def test_recomendacion_simulada(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "solo-para-prueba")

    async def gemini_falso(clase, confianza, revision_humana):
        assert (clase, confianza, revision_humana) == ("Dusty", .997, False)
        return {
            "fuente": "Gemini", "modelo": "simulado", "accion": "Limpieza programada",
            "prioridad": "Media", "resumen": "Revisar polvo visible.",
            "justificacion": "La suciedad puede dificultar la operación.",
            "pasos": ["Validar la superficie", "Programar limpieza segura"],
        }

    monkeypatch.setattr(api_solar, "consultar_gemini", gemini_falso)
    with TestClient(api_solar.create_app(predictor=lambda _: None)) as client:
        result = client.post("/recommend", json={
            "inspeccion_id": "ensayo-2", "clase": "Dusty", "confianza": .997,
            "revision_humana": False,
        })
        assert result.status_code == 200, result.text
        assert result.json()["inspeccion_id"] == "ensayo-2"
        assert result.json()["prioridad"] == "Media"
        assert "solo-para-prueba" not in result.text


def test_respuesta_realista_de_gemini_sin_red(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "clave-de-prueba")
    cliente_original = httpx.AsyncClient

    def servidor_falso(peticion):
        assert peticion.url.path.endswith("gemini-3.5-flash-lite:generateContent")
        assert peticion.headers["x-goog-api-key"] == "clave-de-prueba"
        assert b"Polvo acumulado" in peticion.content
        return httpx.Response(200, json={"candidates": [{"content": {"parts": [{
            "text": '{"resumen":"Suciedad visible sobre el panel.",'
                    '"justificacion":"Se recomienda evaluar limpieza según las condiciones y el procedimiento del sitio.",'
                    '"pasos":["Confirmar presencia de polvo en terreno",'
                    '"Coordinar limpieza siguiendo seguridad del fabricante"]}'
        }]}}]})

    def cliente_simulado(*args, **kwargs):
        return cliente_original(transport=httpx.MockTransport(servidor_falso), **kwargs)

    monkeypatch.setattr(recomendacion_gemini.httpx, "AsyncClient", cliente_simulado)
    resultado = asyncio.run(recomendacion_gemini.consultar_gemini("Dusty", .997, False))
    assert resultado["accion"] == "Limpieza programada"
    assert resultado["prioridad"] == "Media"
    assert len(resultado["pasos"]) == 2
