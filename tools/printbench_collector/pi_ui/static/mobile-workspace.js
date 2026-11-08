(() => {
  'use strict';
  // FINAL MASTER local workspace: real spool edits and prepared-file queue.
  // No automatic printing. All writes require the paired HTTPS session.
  const secure=location.protocol==='https:';
  const $=id=>document.getElementById(id);
  const notice=(id,value)=>{const e=$(id);if(e)e.textContent=value;};
  async function request(path,data) {
    if(data!==undefined && !secure)throw Error('Schreibzugriff nur über HTTPS');
    const response=await fetch('/api/v1'+path,{
      method:data===undefined?'GET':'POST',
      cache:'no-store',
      credentials:'same-origin',
      headers:data===undefined?{}:{'Content-Type':'application/json'},
      body:data===undefined?undefined:JSON.stringify(data)
    });
    const result=await response.json();
    if(!response.ok){
      if(response.status===403)throw Error('iPhone zuerst unter Sicherheit koppeln');
      throw Error(result.error||'API-Fehler '+response.status);
    }
    return result;
  }
  function el(tag,text,cls) {
    const node=document.createElement(tag);
    if(text!=null)node.textContent=String(text);
    if(cls)node.className=cls;
    return node;
  }
  function btn(title,fn) {
    const button=el('button',title,'mobile-inline-action');
    button.type='button';
    button.addEventListener('click',fn);
    return button;
  }
  async function loadMaterials() {
    const list=$('localMaterialList');
    if(!list)return;
    try{
      const items=(await request('/materials')).items||[];
      list.replaceChildren();
      if(!items.length){list.textContent='Noch keine eigenen Materialien gespeichert.';return;}
      for(const item of items){
        const line=el('div',null,'mobile-upload-row');
        const details=el('div');
        const swatch=el('span','●','material-swatch');
        swatch.style.color=item.color;
        const label=el('strong',' '+item.label);
        const sub=el('div',item.vendor+' · '+item.material+' · '+item.remaining_g+' g','mobile-small');
        details.append(swatch,label,sub);
        const actions=el('div',null,'mobile-inline-actions');
        actions.append(btn('Bearbeiten',()=>{
          const form=$('materialForm');
          for(const name of ['id','label','vendor','material','color','remaining_g','profile','note']){
            if(form.elements[name])form.elements[name].value=item[name]??'';
          }
          form.scrollIntoView({behavior:'smooth',block:'start'});
        }));
        actions.append(btn('Löschen',async()=>{
          if(!confirm('Material "'+item.label+'" aus der lokalen Verwaltung entfernen?'))return;
          try{
            await request('/materials/delete',{id:item.id});
            notice('materialMessage','Material entfernt.');
            loadMaterials();
          }catch(e){notice('materialMessage',e.message);}
        }));
        line.append(details,actions);
        list.append(line);
      }
    }catch(e){list.textContent='Materialverwaltung: '+e.message;}
  }
  const form=$('materialForm');
  form?.addEventListener('submit',async event=>{
    event.preventDefault();
    const fields=new FormData(form);
    const data=Object.fromEntries(fields.entries());
    notice('materialMessage','Material wird gespeichert…');
    try{
      await request('/materials',data);
      notice('materialMessage','Material auf Jens-PC gespeichert.');
      form.reset();
      form.elements.id.value='';
      await loadMaterials();
    }catch(e){notice('materialMessage',e.message);}
  });
  form?.addEventListener('reset',()=>{
    setTimeout(()=>{form.elements.id.value='';},0);
  });

  async function loadQueue() {
    const list=$('localQueueList');
    if(!list)return;
    try{
      const {items=[]}=await request('/queue');
      list.replaceChildren();
      if(!items.length){list.textContent='Keine vorbereiteten Druckdateien.';return;}
      for(const item of items){
        const line=el('div',null,'mobile-upload-row');
        const details=el('div');
        details.append(el('strong',item.upload_name),el('div','Bereitgestellt, kein automatischer Druckstart','mobile-small'));
        line.append(details,btn('Entfernen',async()=>{
          if(!confirm('Datei aus der Warteliste entfernen? Die hochgeladene Datei bleibt erhalten.'))return;
          try{
            await request('/queue/remove',{id:item.id});
            notice('queueMessage','Eintrag entfernt.');
            await loadQueue();
          }catch(e){notice('queueMessage',e.message);}
        }));
        list.append(line);
      }
    }catch(e){list.textContent='Warteliste: '+e.message;}
  }
  $('refreshQueue')?.addEventListener('click',loadQueue);
  $('mobileUploadList')?.addEventListener('click',async e=>{
    const button=e.target.closest('button[data-upload-queue]');
    if(!button)return;
    button.disabled=true;
    try{
      await request('/queue',{upload_name:button.dataset.uploadQueue});
      button.textContent='In Warteliste';
      notice('fileInfo','Datei in die lokale Warteliste aufgenommen. Es wird kein Druck gestartet.');
    }catch(error){
      notice('fileInfo','Warteliste: '+error.message);
      button.disabled=false;
    }
  });
  document.querySelectorAll('[data-view]').forEach(button=>{
    button.addEventListener('click',()=>{
      const view=button.dataset.view;
      if(view==='spools')loadMaterials();
      if(view==='jobs')loadQueue();
    });
  });
})();
