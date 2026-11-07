"""Inferencia reutilizable; no requiere acceso a Kaggle ni descarga de pesos."""
import json
from pathlib import Path
import torch
import timm
from PIL import Image, ImageOps
from torchvision import transforms

class AjustarCuadrado:
    """Conservar toda la imagen y su proporción; rellenar márgenes con gris."""
    def __init__(self,tam=224):self.tam=tam
    def __call__(self,im):
        return ImageOps.pad(im,(self.tam,self.tam),method=Image.Resampling.BILINEAR,color=(128,128,128))

def abrir_rgb(ruta):
    with Image.open(ruta) as im:
        im.load();return ImageOps.exif_transpose(im).convert('RGB')

def transformacion_eval(config):
    return transforms.Compose([AjustarCuadrado(config['tam']),transforms.ToTensor(),transforms.Normalize(config['media'],config['desv'])])

def cargar_modelo(carpeta,dispositivo='cpu'):
    carpeta=Path(carpeta);config=json.loads((carpeta/'config.json').read_text())
    modelo=timm.create_model(config['arquitectura'],pretrained=False,num_classes=len(config['clases']))
    modelo.load_state_dict(torch.load(carpeta/'efficientnet_b0_solar.pt',map_location='cpu',weights_only=True))
    return modelo.to(dispositivo).eval(),config,transformacion_eval(config)

def predecir(ruta,modelo,config,tf,dispositivo='cpu'):
    x=tf(abrir_rgb(ruta)).unsqueeze(0).to(dispositivo)
    with torch.inference_mode():p=torch.softmax(modelo(x),dim=1)[0].cpu()
    i=int(p.argmax());clase=config['clases'][i];conf=float(p[i])
    baja=conf<config['umbral_revision']
    return {'clase':clase,'confianza':conf,'baja_confianza':baja,
            'revision_humana':baja or clase in ['Electrical-damage','Physical-Damage'],
            'probabilidades':{c:float(p[k]) for k,c in enumerate(config['clases'])},
            'nota':'Puntaje softmax no calibrado; no confirma una falla eléctrica.'}
