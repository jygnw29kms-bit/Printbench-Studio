(() => {
  'use strict';
  const titles = {overview:'Übersicht',live:'Live Ansicht',control:'Steuerung',ams:'AMS 2 Pro',spools:'Material',jobs:'Druckaufträge',prints:'Historie',files:'Dateien',camera:'Kamera',setup:'Geräte-Setup',network:'Netzwerk',security:'Sicherheit',diagnostics:'Diagnose',system:'System'};
  const secureControl = location.protocol === 'https:' || ['localhost','127.0.0.1','::1'].includes(location.hostname);
  const transport = document.getElementById('securityTransport');
  const secureLink=document.getElementById('secureAppLink');
  if(secureLink)secureLink.href='https://'+location.hostname+':8444/';
  if (transport) transport.textContent = secureControl ? 'Verschlüsselte Verbindung. Das iPhone wird per geschützter Sitzung gekoppelt.' : 'HTTP: Nur Live-Anzeige. Für Druckbefehle bitte den HTTPS-Zugang aktivieren.';
  document.getElementById('networkOrigin').textContent = location.origin;
  const mobileConnection=document.getElementById('mobileActionMessage');
  if (location.protocol!=='https:' && mobileConnection) {
    mobileConnection.textContent='Liveüberwachung aktiv. Druckersteuerung nur über den HTTPS-Zugang unter Sicherheit.';
  }

  const controlNotice=document.getElementById('mobileControlNotice');
  function showControlNotice(enabled) {
    if(!controlNotice)return;
    if(!secureControl){
      controlNotice.textContent='Nur Drucküberwachung über HTTP. Für die Steuerung bitte in Sicherheit auf HTTPS umstellen und das iPhone koppeln.';
    }else if(enabled){
      controlNotice.textContent='Sichere iPhone-Verbindung aktiv. Befehle werden am P2S geprüft.';
    }else{
      controlNotice.textContent='HTTPS aktiv. Zum Freigeben der Steuerung zuerst unter Sicherheit das iPhone koppeln.';
    }
    controlNotice.classList.toggle('mobile-control-ready',Boolean(enabled));
  }
  showControlNotice(false);
  async function reloadControlCapability() {
    try {
      const r = await fetch('/api/v1/control-capabilities',{cache:'no-store',headers:mobileControlToken?{'X-API-Key':mobileControlToken}:{}});
      const auth = await r.json();
      nativeControlAuthorized = secureControl && !!auth.browser_write_endpoint;
      latestCaps.controls = auth.items || {};
      renderCaps(latestCaps);
      showControlNotice(nativeControlAuthorized);
      if(nativeControlAuthorized && currentView==='files')loadUploadedFiles();
      return nativeControlAuthorized;
    } catch (_) {
      nativeControlAuthorized = false;
      refreshControlButtons();
      showControlNotice(false);
      return false;
    }
  }
  const tokenInput = document.getElementById('controlToken');
  const securityMessage = document.getElementById('securityMessage');
  document.getElementById('applyControlToken')?.addEventListener('click',async()=>{
    if(!secureControl){securityMessage.textContent='Steuerung über unverschlüsseltes HTTP gesperrt.';return;}
    const code=tokenInput.value.trim();
    if(!/^[0-9]{8}$/.test(code)){securityMessage.textContent='Bitte den 8-stelligen Kopplungscode eingeben.';return;}
    tokenInput.value='';
    try {
      const response=await fetch('/api/v1/pair',{
        method:'POST',
        headers:{'Content-Type':'application/json'},
        body:JSON.stringify({code})
      });
      const result=await response.json();
      if(!response.ok || !result.ok)throw Error('Kopplungscode abgelaufen oder ungültig');
      const valid=await reloadControlCapability();
      if(!valid)throw Error('Keine Steuerfunktionen für dieses Gerät freigegeben');
      securityMessage.textContent='iPhone gekoppelt. Die Druckersteuerung ist jetzt freigegeben.';
    }catch(error){
      mobileControlToken='';
      securityMessage.textContent='Kopplung fehlgeschlagen: '+error.message;
    }
  });
  document.getElementById('clearControlToken')?.addEventListener('click',async()=>{
    try{await fetch('/api/v1/logout',{method:'POST',headers:{'Content-Type':'application/json'},body:'{}'});}catch(_){}
    mobileControlToken='';nativeControlAuthorized=false;tokenInput.value='';
    await reloadControlCapability();securityMessage.textContent='Steuerzugriff gesperrt.';
  });
  function showView(name) {
    if(!Object.prototype.hasOwnProperty.call(titles,name))return;
    currentView=name;
    stopCameraOnNonCameraView();
    document.querySelectorAll('.side-nav button[data-view]').forEach(el=>{
      el.classList.toggle('active',el.dataset.view===name);
      el.setAttribute('aria-current',el.dataset.view===name?'page':'false');
    });
    document.querySelectorAll('[data-view-panel]').forEach(el=>el.classList.toggle('active',el.dataset.viewPanel===name));
    document.getElementById('pageTitle').textContent=titles[name];
    setMobileNav(false);
    if(name==='camera'||name==='live'){
      const im=document.querySelector('.view.active .dedicated-camera');
      if(im)im.src='/camera/latest.jpg?t='+Date.now();
    }
    if(name==='files')loadUploadedFiles();
    window.scrollTo(0,0);
  }
  document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>showView(b.dataset.view)));
  document.getElementById('mobileFile')?.addEventListener('change',event=>{
    const file=event.target.files?.[0];if(!file)return;
    document.getElementById('fileInfo').textContent=/\.(3mf|stl|gcode|gco|bgcode)$/i.test(file.name)
      ? 'Ausgewählt: '+file.name+' ('+(file.size/1048576).toFixed(2)+' MB). Kein Upload. Slicing erfolgt weiterhin am PC.'
      : 'Dateityp nicht unterstützt.';
  });
  document.getElementById('diagnosticRefresh')?.addEventListener('click',async()=>{
    const output=document.getElementById('diagnosticStatus');
    try {
      const info=await api('/capabilities');
      output.textContent='Collector API '+(info.api||'-')+' erreichbar.';
      document.getElementById('diagnosticCaps').textContent=Object.entries(info.features||{}).map(([k,v])=>k+': '+(v?'JA':'NEIN')).join(' · ');
    }catch(e){output.textContent='Collector offline: '+e.message;}
  });
  function updateMobile() {
    const s=latestLive||{};
    const text=(id,val)=>{const e=document.getElementById(id);if(e)e.textContent=val;};
    text('jobState',s.print_state||'UNBEKANNT');
    text('jobProgress',s.progress!=null?Math.round(s.progress)+'%':'-');
    text('jobRemain',s.remaining_min!=null?Math.round(s.remaining_min)+' min':'-');
    text('networkWifi',s.wifi_rssi!=null?s.wifi_rssi+' dBm':'-');
    text('networkCollector',s.online?'P2S online':'Keine aktuellen P2S-Daten');
    text('setupStatus',s.online?'Bambu Lab P2S meldet aktuelle LAN-Telemetrie.':'Collector / Druckerverbindung prüfen.');
  }
  async function loadUploadedFiles() {
    const list=document.getElementById('mobileUploadList');
    if(!list)return;
    if(!secureControl || !nativeControlAuthorized){
      list.textContent='Dateien auf Jens-PC sind erst nach sicherer Kopplung sichtbar.';
      return;
    }
    try {
      const response=await fetch('/api/v1/files',{cache:'no-store'});
      const data=await response.json();
      if(!response.ok)throw Error(data.error||'Dateiliste nicht verfügbar');
      list.replaceChildren();
      const items=data.items||[];
      if(!items.length){list.textContent='Noch keine Dateien vom iPhone übertragen.';return;}
      for(const item of items){
        const line=document.createElement('div');
        line.className='mobile-upload-row';
        const title=document.createElement('strong');
        title.textContent=item.name;
        const size=document.createElement('span');
        size.textContent=(item.bytes/1048576).toFixed(2)+' MB';
        const queueButton=document.createElement('button');
        queueButton.type='button';
        queueButton.className='mobile-inline-action';
        queueButton.textContent='Auf Warteliste';
        queueButton.dataset.uploadQueue=item.name;
        line.append(title,size,queueButton);
        list.append(line);
      }
    } catch(error) {
      list.textContent='Dateiliste fehlgeschlagen: '+error.message;
    }
  }
  document.getElementById('refreshMobileFiles')?.addEventListener('click',loadUploadedFiles);
  document.getElementById('uploadMobileFile')?.addEventListener('click',async()=>{
    const input=document.getElementById('mobileFile');
    const selected=input?.files?.[0];
    const info=document.getElementById('fileInfo');
    if(!selected){info.textContent='Bitte zuerst eine 3MF-, STL- oder G-Code-Datei auswählen.';return;}
    if(!secureControl || !nativeControlAuthorized){
      info.textContent='Upload gesperrt: zuerst HTTPS öffnen und unter Sicherheit iPhone koppeln.';
      return;
    }
    if(!/\.(3mf|stl|gcode|gco|bgcode)$/i.test(selected.name)){
      info.textContent='Dieser Dateityp wird nicht unterstützt.';
      return;
    }
    if(!selected.size || selected.size>256*1024*1024){
      info.textContent='Datei ist leer oder größer als 256 MB.';
      return;
    }
    const button=document.getElementById('uploadMobileFile');
    button.disabled=true;
    info.textContent='Übertragung an Jens-PC läuft…';
    try{
      const response=await fetch('/api/v1/files',{
        method:'POST',
        headers:{'Content-Type':'application/octet-stream','X-File-Name':encodeURIComponent(selected.name)},
        body:selected
      });
      const data=await response.json();
      if(!response.ok || !data.ok)throw Error(data.error||'Übertragung fehlgeschlagen');
      info.textContent='Übertragen: '+data.name+' ('+(data.bytes/1048576).toFixed(2)+' MB). Im PRINTBENCH-Dateiordner auf Jens-PC verfügbar.';
      input.value='';
      await loadUploadedFiles();
    }catch(error){
      info.textContent='Upload fehlgeschlagen: '+error.message;
    }finally{button.disabled=false;}
  });

  const actionMessage=document.getElementById('mobileActionMessage');
  function message(text) {
    if(actionMessage) actionMessage.textContent=text;
  }
  function csvSafe(value) {
    const raw=String(value==null?'':typeof value==='object'?JSON.stringify(value):value);
    const safe=/^[=+\-@\t\r]/.test(raw)?"'"+raw:raw;
    return '"'+safe.replace(/"/g,'""')+'"';
  }
  function toCSV(items) {
    if(!items.length)return 'Keine Daten\n';
    const cols=[...new Set(items.flatMap(item=>Object.keys(item||{})))];
    return [cols.map(csvSafe).join(','),...items.map(item=>cols.map(key=>csvSafe(item[key])).join(','))].join('\r\n')+'\r\n';
  }
  async function exportFile(endpoint, filename, format) {
    message('Daten werden geladen…');
    try {
      const response=await fetch('/api/v1'+endpoint,{cache:'no-store'});
      if(!response.ok)throw Error('Server HTTP '+response.status);
      const data=await response.json();
      let content, mime;
      if(format==='csv') {
        const items=Array.isArray(data)?data:(data.items||data.sessions||[]);
        content=toCSV(items);
        mime='text/csv;charset=utf-8';
      }else{
        content=JSON.stringify(data,null,2);
        mime='application/json;charset=utf-8';
      }
      const blob=new Blob([content],{type:mime});
      const name='PRINTBENCH-'+filename+'-'+new Date().toISOString().slice(0,10)+'.'+format;
      if(navigator.canShare && navigator.share && navigator.canShare({files:[new File([blob],name,{type:mime})]})){
        try { await navigator.share({files:[new File([blob],name,{type:mime})],title:'PRINTBENCH '+filename});message('Datei bereitgestellt.');return; }
        catch(e){if(e.name==='AbortError'){message('Export abgebrochen.');return;}}
      }
      const url=URL.createObjectURL(blob),a=document.createElement('a');
      a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();
      setTimeout(()=>URL.revokeObjectURL(url),30000);
      message('Export bereitgestellt: '+name);
    }catch(error){message('Export fehlgeschlagen: '+error.message);}
  }
  document.getElementById('exportLive')?.addEventListener('click',()=>exportFile('/live','druckstatus','json'));
  document.getElementById('exportHistory')?.addEventListener('click',()=>exportFile('/sessions?limit=100','historie','csv'));
  document.getElementById('exportSpools')?.addEventListener('click',()=>exportFile('/spools','material','csv'));
  document.getElementById('refreshMobile')?.addEventListener('click',async()=>{
    message('P2S-Status wird aktualisiert…');
    try {await refreshFast();await refreshSlow();updateMobile();message('P2S-Daten aktualisiert.');}
    catch(error){message('Aktualisierung fehlgeschlagen: '+error.message);}
  });
  document.getElementById('refreshHistory')?.addEventListener('click',async()=>{
    try {const result=await api('/sessions?limit=30');renderSessions(Array.isArray(result)?result:(result.items||result.sessions||[]));message('Historie aktualisiert.');}
    catch(error){message('Historie nicht erreichbar: '+error.message);}
  });
  document.getElementById('refreshSpools')?.addEventListener('click',async()=>{
    try {renderSpools(await api('/spools'));message('Materialdaten aktualisiert.');}
    catch(error){message('Materialdaten nicht erreichbar: '+error.message);}
  });
  setInterval(updateMobile,5000);updateMobile();
  if('serviceWorker' in navigator && secureControl)navigator.serviceWorker.register('/sw.js').catch(()=>{});
})();