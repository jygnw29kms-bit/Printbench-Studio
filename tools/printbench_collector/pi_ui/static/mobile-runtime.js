(() => {
  'use strict';
  // Only foreground/local status alerts. No cloud push, no background service.
  const byId=id=>document.getElementById(id);
  const alertButton=byId('enableJobAlerts');
  let alertsEnabled=false;
  let initialized=false;
  let previousState='';
  let previousOnline=false;
  let lastAlertAt=0;

  function stateName(state){
    return String(state||'').trim().toUpperCase();
  }
  async function alertLocal(title,body){
    if(!alertsEnabled||Date.now()-lastAlertAt<30000)return;
    lastAlertAt=Date.now();
    if(!('Notification' in window)||Notification.permission!=='granted')return;
    try{
      if(navigator.serviceWorker?.ready){
        const reg=await navigator.serviceWorker.ready;
        if(reg?.showNotification){
          await reg.showNotification(title,{body,icon:'/icons/icon-192.png',tag:'printbench-p2s-status'});
          return;
        }
      }
      new Notification(title,{body,icon:'/icons/icon-192.png'});
    }catch(error){
      if(typeof reportMobileCommand==='function')reportMobileCommand('Hinweis nicht angezeigt: '+error.message,'error');
    }
  }
  if(alertButton)alertButton.addEventListener('click',async()=>{
    if(alertsEnabled){
      alertsEnabled=false;alertButton.textContent='Druck-Ende melden';
      return;
    }
    if(location.protocol!=='https:'){
      reportMobileCommand('Lokale Meldungen erfordern die sichere HTTPS-App.','error');
      return;
    }
    if(!('Notification' in window)){
      reportMobileCommand('Für Mitteilungen PRINTBENCH zum iPhone-Home-Bildschirm hinzufügen.','error');
      return;
    }
    try{
      const permission=await Notification.requestPermission();
      alertsEnabled=permission==='granted';
      alertButton.textContent=alertsEnabled?'Meldungen aktiv · AUS':'Druck-Ende melden';
      reportMobileCommand(alertsEnabled
        ? 'Meldungen aktiviert, solange PRINTBENCH geöffnet ist.'
        : 'iOS hat die Berechtigung für lokale Meldungen nicht erteilt.',
        alertsEnabled?'success':'error');
    }catch(error){reportMobileCommand('Mitteilungen: '+error.message,'error');}
  });
  async function pollJobState(){
    try{
      const r=await fetch('/api/v1/live',{cache:'no-store'});
      if(!r.ok)return;
      const data=await r.json();
      const state=stateName(data.print_state);
      const online=data.online===true;
      if(initialized && alertsEnabled){
        if(online && state!==previousState && ['FINISH','FINISHED','COMPLETED'].includes(state)){
          alertLocal('PRINTBENCH · Druck fertig','Der P2S hat den Druckauftrag beendet.');
        } else if(online && state!==previousState && ['FAILED','ERROR'].includes(state)){
          alertLocal('PRINTBENCH · Druckerfehler','Am P2S wurde ein Fehlerstatus gemeldet.');
        } else if(previousOnline && !online){
          alertLocal('PRINTBENCH · Verbindung','Die P2S-Telemetrie ist nicht mehr aktuell.');
        }
      }
      initialized=true;previousState=state;previousOnline=online;
    }catch(_){}
  }
  // Visibility change does not imply background reliability on iOS.
  document.addEventListener('visibilitychange',()=>{
    if(!document.hidden){
      pollJobState();
      if(typeof refreshFast==='function')refreshFast();
      if(typeof refreshSlow==='function')refreshSlow();
    }
  });
  window.addEventListener('online',()=>{
    if(typeof refreshFast==='function')refreshFast();
  });
  setInterval(()=>{if(!document.hidden)pollJobState();},12000);
  pollJobState();
  byId('exportDiagnostics')?.addEventListener('click',async()=>{
    const button=byId('exportDiagnostics');
    button.disabled=true;
    try{
      const responses=await Promise.all(['/live','/system','/camera-status','/capabilities']
        .map(path=>fetch('/api/v1'+path,{cache:'no-store'}).then(async response=>({
          path,status:response.status,data:await response.json().catch(()=>({error:'JSON unavailable'}))
        }))));
      // No credentials, tokens, cookies or private URLs are exported.
      const report={
        product:'135er-PRINTBENCH',timestamp:new Date().toISOString(),
        origin:location.origin,api:responses
      };
      const blob=new Blob([JSON.stringify(report,null,2)],{type:'application/json'});
      const file=new File([blob],'PRINTBENCH-Diagnose-'+new Date().toISOString().slice(0,10)+'.json',
        {type:'application/json'});
      if(navigator.canShare?.({files:[file]})&&navigator.share){
        try{await navigator.share({files:[file],title:'PRINTBENCH Diagnose'});return;}
        catch(e){if(e.name==='AbortError')return;}
      }
      const url=URL.createObjectURL(blob),a=document.createElement('a');
      a.download=file.name;a.href=url;document.body.appendChild(a);a.click();a.remove();
      setTimeout(()=>URL.revokeObjectURL(url),30000);
    }catch(error){
      reportMobileCommand('Diagnose konnte nicht exportiert werden: '+error.message,'error');
    }finally{button.disabled=false;}
  });
})();
