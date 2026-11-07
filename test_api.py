"""Pruebas del contrato HTTP con un predictor simulado; no miden el modelo."""
import io
from PIL import Image
from fastapi.testclient import TestClient
from api_solar import create_app, CLASES

class PredictorPrueba:
    version='prueba-sin-pesos'
    def __call__(self,data):
        return dict(clase='Clean',confianza=.9,baja_confianza=False,revision_humana=False,
            probabilidades={c:(.9 if c=='Clean' else .02) for c in CLASES},nota='Predicción simulada para prueba.')

def imagen(formato='PNG'):
    out=io.BytesIO();Image.new('RGB',(64,64),(20,40,60)).save(out,format=formato);return out.getvalue()

def test_success():
    with TestClient(create_app(predictor=PredictorPrueba())) as c:
        assert c.get('/health').status_code==200
        ids=[]
        for fmt in ['PNG','JPEG','BMP','WEBP']:
            r=c.post('/predict',files={'file':('imagen.bin',imagen(fmt),'application/octet-stream')})
            assert r.status_code==200,r.text
            d=r.json();assert d['clase']=='Clean';assert len(d['probabilidades'])==6
            assert r.headers['X-Inspection-ID']==d['inspeccion_id'];ids.append(d['inspeccion_id'])
        assert len(set(ids))==4

def test_bad_files():
    with TestClient(create_app(predictor=PredictorPrueba(),max_bytes=1000)) as c:
        assert c.post('/predict',files={'file':('x',b'')}).status_code==400
        assert c.post('/predict',files={'file':('x.jpg',b'no es imagen')}).status_code==422
        assert c.post('/predict',files={'file':('x',b'x'*1001)}).status_code==413
        assert c.post('/predict',files={'file':('x.gif',imagen('GIF'))}).status_code==415
        assert c.post('/predict').status_code==422
    with TestClient(create_app(predictor=PredictorPrueba(),max_pixels=100)) as c:
        assert c.post('/predict',files={'file':('x',imagen())}).status_code==413

def test_unavailable(tmp_path):
    with TestClient(create_app(model_dir=tmp_path)) as c:
        assert c.get('/health').status_code==503
        assert c.post('/predict',files={'file':('x',imagen())}).status_code==503

def test_internal_failure():
    class Falla(PredictorPrueba):
        def __call__(self,data):raise RuntimeError('detalle interno')
    with TestClient(create_app(predictor=Falla())) as c:
        r=c.post('/predict',files={'file':('x',imagen())})
        assert r.status_code==500 and 'detalle interno' not in r.text
