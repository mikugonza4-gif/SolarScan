"""Pruebas offline de la integración SolarScan -> n8n."""
import asyncio
import io

import httpx
from fastapi.testclient import TestClient
from PIL import Image

import api_solar


class PredictorPrueba:
    version = 'simulada'

    def __call__(self, data):
        return {
            'clase': 'Dusty', 'confianza': 0.8, 'baja_confianza': False,
            'revision_humana': False,
            'probabilidades': {clase: (0.8 if clase == 'Dusty' else 0.04)
                               for clase in api_solar.CLASES},
            'nota': 'Prueba con predictor simulado.',
        }


def imagen():
    salida = io.BytesIO()
    Image.new('RGB', (16, 16), (10, 20, 30)).save(salida, format='PNG')
    return salida.getvalue()


def test_un_evento_valido_por_inspeccion(monkeypatch):
    enviados = []
    monkeypatch.setenv('GEMINI_API_KEY', 'clave-simulada')
    monkeypatch.setenv('N8N_WEBHOOK_URL', 'https://solarscan.app.n8n.cloud/webhook/solarscan/alertas-v1')
    monkeypatch.setenv('N8N_WEBHOOK_TOKEN', 'token-simulado')

    async def gemini_falso(clase, confianza, revision_humana):
        return {'resumen': 'Polvo visible', 'justificacion': 'Revisar en sitio',
                'pasos': ['Programar limpieza'], 'prioridad': 'Media', 'accion': 'Limpieza programada'}

    async def n8n_falso(evento):
        enviados.append(evento)

    monkeypatch.setattr(api_solar, 'consultar_gemini', gemini_falso)
    monkeypatch.setattr(api_solar, 'enviar_evento_n8n', n8n_falso)
    with TestClient(api_solar.create_app(predictor=PredictorPrueba())) as cliente:
        resultado = cliente.post('/predict', files={'file': ('imagen.png', imagen(), 'image/png')})
        assert resultado.status_code == 200
        prediccion = resultado.json()
        datos = {'inspeccion_id': prediccion['inspeccion_id'], 'clase': 'Dusty',
                 'confianza': 0.8, 'revision_humana': False}

        # Una solicitud fabricada o alterada nunca genera notificaciones.
        falso = cliente.post('/recommend', json={**datos, 'confianza': 0.79})
        assert falso.status_code == 200
        assert enviados == []

        ok = cliente.post('/recommend', json=datos)
        assert ok.status_code == 200
        assert len(enviados) == 1
        assert enviados[0]['recomendacion']['resumen'] == 'Polvo visible'
        assert enviados[0]['inspeccion_id'] == prediccion['inspeccion_id']
        assert 'probabilidades' not in enviados[0]
        assert 'imagen' not in enviados[0]

        repetido = cliente.post('/recommend', json=datos)
        assert repetido.status_code == 200
        assert len(enviados) == 1


def test_encabezado_privado_y_envio_https(monkeypatch):
    monkeypatch.setenv('N8N_WEBHOOK_URL', 'https://solarscan.app.n8n.cloud/webhook/solarscan/alertas-v1')
    monkeypatch.setenv('N8N_WEBHOOK_TOKEN', 'token-local-prueba')
    original = httpx.AsyncClient
    recibidos = []

    def recibir(peticion):
        recibidos.append(peticion)
        return httpx.Response(200, text='ok')

    def cliente_sin_red(*args, **kwargs):
        return original(transport=httpx.MockTransport(recibir), **kwargs)

    monkeypatch.setattr(api_solar.httpx, 'AsyncClient', cliente_sin_red)
    asyncio.run(api_solar.enviar_evento_n8n({
        'inspeccion_id': 'ejemplo-n8n', 'clase': 'Dusty', 'confianza': 0.8,
        'recomendacion': {'resumen': 'Revisar polvo'},
    }))
    assert len(recibidos) == 1
    assert recibidos[0].headers['x-solarscan-token'] == 'token-local-prueba'
    assert recibidos[0].url.path == '/webhook/solarscan/alertas-v1'
