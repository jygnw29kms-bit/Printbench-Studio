(() => {
  'use strict';
  const $=id=>document.getElementById(id);
  const state={
    busy:false,
    failures:0,
    lastGood:0,
    lastResult:null
  };
  let controller=null;
  function display(text,kind){
    const summary=$('mobileHealthText'),led=$('mobileHealthLed'),bar=$('mobileHealthBar');
    if(summary)summary.textContent=text;
    if(led)led.dataset.status=kind;
    if(bar)bar.dataset.status=kind;
  }
  async function update(force=false){
    if(state.busy)return;
    if(document.hidden&&!force)return;
    state.busy=true;
    const button=$('mobileHealthRetry');
    if(button)button.disabled=true;
    controller?.abort();
    controller=new AbortController();
    const abort=controller;
    const timeout=setTimeout(()=>abort.abort(),6000);
    try {
      const response=await fetch('/api/v1/mobile-health',{
        cache:'no-store',credentials:'same-origin',signal:abort.signal
      });
      if(!response.ok)throw new Error('HTTP '+response.status);
      const data=await response.json();
      state.failures=0;
      state.lastGood=Date.now();
      state.lastResult=data;
      const access=data.transport==='https'
        ? data.paired?'Steuerung bereit':'HTTPS · Kopplung erforderlich'
        :'Nur Anzeige · HTTPS für Steuerung';
      const printer=data.printer_online?'P2S online':'P2S offline';
      const camera=data.camera_online?'Kamera live':'Kamera nicht verfügbar';
      display([printer,camera,access].join(' · '),
        data.printer_online&&data.camera_online?'ok':
        data.printer_online?'warn':'error');
      const pairing=$('mobilePairingSignal');
      if(pairing){
        pairing.textContent=data.transport==='https'
          ? data.paired?'GEKOPPELT':'KOPPLUNG FEHLT'
          :'NUR ANZEIGE';
        pairing.classList.toggle('connected',!!data.paired);
        pairing.classList.toggle('warning',!data.paired);
      }
      const printerSignal=$('mobileDeviceSignal');
      if(printerSignal){
        printerSignal.textContent=data.printer_online?'P2S ONLINE':'P2S OFFLINE';
        printerSignal.classList.toggle('connected',!!data.printer_online);
        printerSignal.classList.toggle('warning',!data.printer_online);
      }
      const cameraSignal=$('mobileCameraSignal');
      if(cameraSignal){
        cameraSignal.textContent=data.camera_online?'KAMERA LIVE':'KAMERA OFFLINE';
        cameraSignal.classList.toggle('connected',!!data.camera_online);
        cameraSignal.classList.toggle('warning',!data.camera_online);
      }
      // Restore authorization state immediately when an old 30-day cookie
      // expires; never keep dangerous action buttons falsely enabled.
      if(typeof nativeControlAuthorized!=='undefined' &&
         nativeControlAuthorized && !data.paired){
        nativeControlAuthorized=false;
        if(typeof refreshControlButtons==='function')refreshControlButtons();
        const notice=$('mobileControlNotice');
        if(notice)notice.textContent='Kopplung abgelaufen. Unter Sicherheit erneut koppeln.';
      }
    } catch(error) {
      state.failures++;
      const issue=error?.name==='AbortError'?'Zeitüberschreitung':'nicht erreichbar';
      display('Jens-PC '+issue+' · Netzwerk prüfen · Erneut versuchen','error');
    } finally {
      clearTimeout(timeout);
      state.busy=false;
      if(button)button.disabled=false;
    }
  }
  $('mobileHealthRetry')?.addEventListener('click',()=>{
    if(typeof refreshFast==='function')refreshFast().catch(()=>{});
    if(typeof refreshSlow==='function')refreshSlow().catch(()=>{});
    // refreshSlow already re-reads pairing authorization via the existing API.
    update(true);
  });
  document.addEventListener('visibilitychange',()=>{if(!document.hidden)update(true);});
  window.addEventListener('online',()=>update(true));
  setInterval(()=>update(),10000);
  update(true);
})();
