'use strict';
const categories=[['Bird-drop','Excrementos de aves','Depósitos localizados sobre la superficie del panel.'],['Clean','Panel limpio','Superficie sin suciedad o daño evidente según la etiqueta del dataset.'],['Dusty','Polvo acumulado','Suciedad extendida sobre la superficie.'],['Electrical-damage','Indicios de daño eléctrico','Categoría visual del dataset. La causa debe confirmarse mediante revisión técnica.'],['Physical-Damage','Daño físico','Roturas o deterioro visible del panel.'],['Snow-Covered','Cubierto de nieve','Presencia de nieve sobre parte o todo el panel.']];
const $=id=>document.getElementById(id);let selected=null,previewUrl=null,last=null,busy=false,adviceController=null;
function tab(id){document.querySelectorAll('[role=tabpanel]').forEach(p=>p.hidden=p.id!==id);document.querySelectorAll('[role=tab]').forEach(b=>{const yes=b.dataset.tab===id;b.setAttribute('aria-selected',String(yes));b.tabIndex=yes?0:-1;});}
const tabs=[...document.querySelectorAll('[role=tab]')];tabs.forEach((b,i)=>{b.onclick=()=>tab(b.dataset.tab);b.onkeydown=e=>{let k;if(e.key==='ArrowRight')k=(i+1)%tabs.length;if(e.key==='ArrowLeft')k=(i+tabs.length-1)%tabs.length;if(e.key==='Home')k=0;if(e.key==='End')k=tabs.length-1;if(k!==undefined){e.preventDefault();tabs[k].focus();tab(tabs[k].dataset.tab);}}});$('start').onclick=$('go-analyze').onclick=()=>tab('analizar');
// Un panel independiente mantiene visible la clasificación aunque Gemini no responda.
const advicePanel=document.createElement('section');
advicePanel.id='gemini-panel';
advicePanel.className='card ai-card';
advicePanel.hidden=true;
advicePanel.innerHTML=`<div class="ai-heading"><div><span class="eyebrow">Orientación para mantenimiento</span><h2>Recomendación con Gemini</h2></div><span class="ai-label">IA generativa</span></div><p id="gemini-status" role="status" aria-live="polite"></p><div id="gemini-result" hidden><div class="ai-summary"><span id="gemini-priority" class="ai-priority"></span><strong id="gemini-action"></strong></div><p id="gemini-description"></p><h3>¿Por qué?</h3><p id="gemini-reason"></p><h3>Próximos pasos sugeridos</h3><ul id="gemini-steps"></ul><p class="meta">Recomendación orientativa. Confirmar en terreno antes de realizar intervenciones.</p></div>`;
document.querySelector('.analysis').append(advicePanel);
for(const [key,name,desc] of categories){const c=document.createElement('article');c.className='card';const a=document.createElement('a');a.href='/interfaz/ejemplos/'+key+'.jpg';a.target='_blank';a.rel='noopener';const img=document.createElement('img');img.src=a.href;img.alt='Ejemplos del dataset: '+name;img.loading='lazy';a.append(img);const h=document.createElement('h3');h.textContent=name;const p=document.createElement('p');p.textContent=desc;const s=document.createElement('span');s.textContent='Ampliar lámina ↗';a.append(s);c.append(a,h,p);$('gallery').append(c);}
function resetResult(){
  if(adviceController)adviceController.abort();
  adviceController=null;
  last=null;
  advicePanel.hidden=true;
  $('gemini-result').hidden=true;
  $('gemini-status').textContent='';
  $('result').hidden=true;$('empty').hidden=false;$('message').textContent='';$('message').className='';
}
function reset(){if(busy)return;selected=null;$('file').value='';if(previewUrl)URL.revokeObjectURL(previewUrl);previewUrl=null;$('preview').hidden=true;$('preview').removeAttribute('src');$('filename').textContent='';$('submit').disabled=true;resetResult();}
$('clear').onclick=reset;
$('file').onchange=()=>{resetResult();selected=$('file').files[0]||null;if(previewUrl)URL.revokeObjectURL(previewUrl);$('preview').hidden=true;$('submit').disabled=true;$('filename').textContent='';if(!selected)return;if(selected.size>15*1024*1024){$('message').textContent='La imagen supera 15 MiB. Selecciona un archivo más pequeño.';$('message').className='error';selected=null;return;}previewUrl=URL.createObjectURL(selected);$('preview').src=previewUrl;$('preview').hidden=false;$('filename').textContent=selected.name;$('submit').disabled=false;};
$('preview').onerror=()=>{$('preview').hidden=true;$('message').textContent='No se pudo mostrar la vista previa. El servicio comprobará si el archivo es una imagen válida.';};
const errors={400:'El archivo está vacío.',413:'La imagen supera el tamaño o la resolución permitidos.',415:'Formato no admitido. Utiliza una imagen estática JPG, PNG, WEBP o BMP.',422:'No se pudo leer la imagen. Selecciona otro archivo.',503:'El modelo no está disponible. Revisa la ventana de SolarScan.',500:'No se pudo completar el análisis. Revisa la ventana de SolarScan e inténtalo nuevamente.'};
function validResult(out){return categories.some(c=>c[0]===out.clase)&&Number.isFinite(out.confianza)&&out.confianza>=0&&out.confianza<=1&&typeof out.revision_humana==='boolean'&&typeof out.baja_confianza==='boolean'&&typeof out.inspeccion_id==='string'&&typeof out.fecha_utc==='string'&&out.probabilidades&&categories.every(([key])=>Number.isFinite(out.probabilidades[key])&&out.probabilidades[key]>=0&&out.probabilidades[key]<=1);}
async function solicitarRecomendacion(out){
  advicePanel.hidden=false;
  $('gemini-result').hidden=true;
  $('gemini-status').textContent='Gemini está preparando una recomendación para el inspector…';
  const controller=new AbortController();
  adviceController=controller;
  const timer=setTimeout(()=>controller.abort(),35000);
  try{
    const response=await fetch('/recommend',{
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({
        inspeccion_id:out.inspeccion_id,
        clase:out.clase,
        confianza:out.confianza,
        revision_humana:out.revision_humana
      }),
      signal:controller.signal
    });
    const data=await response.json();
    if(!response.ok)throw new Error(data.error||data.detail||'No fue posible consultar Gemini.');
    if(!['Seguimiento','Limpieza programada','Inspección técnica'].includes(data.accion)
      ||!['Baja','Media','Alta'].includes(data.prioridad)
      ||!Array.isArray(data.pasos)||data.pasos.length<2
      ||typeof data.resumen!=='string'||typeof data.justificacion!=='string'
      ||data.inspeccion_id!==out.inspeccion_id)throw new Error('La respuesta de Gemini está incompleta.');
    if(last?.inspeccion_id!==out.inspeccion_id)return;
    $('gemini-priority').textContent='Prioridad '+data.prioridad.toLowerCase();
    $('gemini-priority').dataset.priority=data.prioridad;
    $('gemini-action').textContent=data.accion;
    $('gemini-description').textContent=data.resumen;
    $('gemini-reason').textContent=data.justificacion;
    const list=$('gemini-steps');list.replaceChildren();
    for(const paso of data.pasos){const li=document.createElement('li');li.textContent=paso;list.append(li);}
    $('gemini-status').textContent='Recomendación generada por '+data.modelo+'.';
    $('gemini-result').hidden=false;
    last.recomendacion=data;
  }catch(error){
    if(last?.inspeccion_id===out.inspeccion_id&&!controller.signal.aborted){
      $('gemini-status').textContent=error.message||'Gemini no está disponible en este momento.';
    }else if(last?.inspeccion_id===out.inspeccion_id&&error.name==='AbortError'){
      $('gemini-status').textContent='Gemini tardó demasiado. La clasificación sigue disponible.';
    }
  }finally{clearTimeout(timer);if(adviceController===controller)adviceController=null;}
}
$('submit').onclick=async()=>{if(!selected||busy)return;resetResult();busy=true;$('submit').disabled=true;$('file').disabled=true;$('clear').disabled=true;$('submit').textContent='Analizando…';$('message').textContent='El modelo está procesando la fotografía.';const controller=new AbortController(),timer=setTimeout(()=>controller.abort(),120000);try{const data=new FormData();data.append('file',selected);const r=await fetch('/predict',{method:'POST',body:data,signal:controller.signal});if(!r.ok)throw new Error(errors[r.status]||'No se pudo obtener el resultado.');const out=await r.json();if(!validResult(out))throw new Error('La respuesta del servicio está incompleta.');if((out.confianza<0.7||['Electrical-damage','Physical-Damage'].includes(out.clase))&&!out.revision_humana)throw new Error('La respuesta no cumple la política de revisión humana.');last=out;$('class').textContent=categories.find(c=>c[0]===out.clase)[1];$('confidence').textContent=(out.confianza*100).toLocaleString('es-CL',{maximumFractionDigits:1})+' %';$('review').textContent=out.revision_humana?'Revisión humana requerida. Verifica la condición antes de decidir una intervención.':'La política del modelo no solicita revisión obligatoria para este resultado. Esto no certifica el estado del panel.';$('probs').replaceChildren();for(const [key,name]of categories){const v=out.probabilidades[key],row=document.createElement('div');row.className='prob';const label=document.createElement('span');label.textContent=name;const value=document.createElement('span');value.textContent=(v*100).toFixed(1)+' %';const bar=document.createElement('progress');bar.max=1;bar.value=v;bar.setAttribute('aria-label',name);row.append(label,value,bar);$('probs').append(row);}$('inspection').textContent='Inspección: '+out.inspeccion_id+' · '+new Date(out.fecha_utc).toLocaleString('es-CL');$('empty').hidden=true;$('result').hidden=false;$('message').textContent='Análisis completado.';void solicitarRecomendacion(out);}catch(e){$('message').className='error';$('message').textContent=e.name==='AbortError'?'El análisis tardó demasiado. Comprueba que el servicio siga abierto.':e instanceof TypeError?'No se pudo conectar con SolarScan. Comprueba que la ventana de inicio siga abierta.':e.message;}finally{clearTimeout(timer);busy=false;$('file').disabled=false;$('clear').disabled=false;$('submit').disabled=!selected;$('submit').textContent='Analizar imagen';}};
$('download').onclick=()=>{if(!last)return;const label=categories.find(c=>c[0]===last.clase)[1];const lines=['SolarScan — Resultado de inspección','Identificador: '+last.inspeccion_id,'Fecha: '+last.fecha_utc,'Condición visual: '+label,'Confianza: '+(last.confianza*100).toFixed(1)+' %','Revisión humana: '+(last.revision_humana?'Requerida':'No requerida por la política del modelo'),'Nota: puntaje no calibrado; no confirma una falla eléctrica.'];if(last.recomendacion){lines.push('Acción recomendada: '+last.recomendacion.accion,'Prioridad: '+last.recomendacion.prioridad,'Justificación Gemini: '+last.recomendacion.justificacion,...last.recomendacion.pasos.map((paso,i)=>'Paso '+(i+1)+': '+paso));}const u=URL.createObjectURL(new Blob([lines.join('\n')],{type:'text/plain;charset=utf-8'}));const a=document.createElement('a');a.href=u;a.download='SolarScan_resultado.txt';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000);};
fetch('/health').then(r=>{if(!r.ok)throw Error();return r.json();}).then(x=>{$('health').textContent=x.estado==='listo'?'● Modelo disponible':'Modelo no disponible';}).catch(()=>{$('health').textContent='Modelo no disponible';});
