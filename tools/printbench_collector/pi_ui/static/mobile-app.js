(() => {
  'use strict';
  const titles = {overview:'Übersicht',live:'Live Ansicht',control:'Steuerung',ams:'AMS 2 Pro',spools:'Material',jobs:'Druckaufträge',prints:'Historie',files:'Dateien',camera:'Kamera',setup:'Geräte-Setup',network:'Netzwerk',security:'Sicherheit',diagnostics:'Diagnose',system:'System'};
  const secureControl = location.protocol === 'https:' || ['localhost','127.0.0.1','::1'].includes(location.hostname);
  const transport = document.getElementById('securityTransport');
  if (transport) transport.textContent = secureControl ? 'Verschlüsselte Verbindung. API-Schlüssel bleibt nur im Arbeitsspeicher.' : 'Nur Lesezugriff über HTTP. Steuerbefehle erfordern HTTPS.';
  document.getElementById('networkOrigin').textContent = location.origin;
  async function reloadControlCapability() {
    try {
      const r = await fetch('/api/v1/control-capabilities',{cache:'no-store',headers:mobileControlToken?{'X-API-Key':mobileControlToken}:{}});
      const auth = await r.json();
      nativeControlAuthorized = secureControl && !!auth.browser_write_endpoint;
      latestCaps.controls = auth.items || {};
      renderCaps(latestCaps);
      return nativeControlAuthorized;
    } catch (_) {
      nativeControlAuthorized = false;
      refreshControlButtons();
      return false;
    }
  }
  const tokenInput = document.getElementById('controlToken');
  const securityMessage = document.getElementById('securityMessage');
  document.getElementById('applyControlToken')?.addEventListener('click',async()=>{
    if(!secureControl){securityMessage.textContent='Steuerung über unverschlüsseltes HTTP gesperrt.';return;}
    const key=tokenInput.value.trim();
    if(!/^[a-f0-9]{64}$/i.test(key)){securityMessage.textContent='64 hexadezimale Zeichen erforderlich.';return;}
    mobileControlToken=key;tokenInput.value='';
    const valid=await reloadControlCapability();
    if(!valid)mobileControlToken='';
    securityMessage.textContent=valid?'Steuerung autorisiert.':'Zugriff nicht autorisiert.';
  });
  document.getElementById('clearControlToken')?.addEventListener('click',async()=>{
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