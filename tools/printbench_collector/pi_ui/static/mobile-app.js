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
  document.querySelectorAll('.side-nav button[data-view]').forEach(b=>b.addEventListener('click',()=>showView(b.dataset.view)));
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
  setInterval(updateMobile,5000);updateMobile();
  if('serviceWorker' in navigator && secureControl)navigator.serviceWorker.register('/sw.js').catch(()=>{});
})();