const CACHE_PREFIX='printbench-mobile-shell-';
const CACHE=CACHE_PREFIX+'v28';
const ASSETS=['/','/index.html','/app.css','/app.js','/mobile-app.js','/mobile-workspace.js','/mobile-runtime.js','/mobile-health.js','/manifest.webmanifest','/icons/icon-180.png','/icons/icon-192.png','/icons/icon-512.png','/images/printbench_hero_p2s_ams.png'];
self.addEventListener('install',event=>{
  event.waitUntil(caches.open(CACHE).then(cache=>cache.addAll(ASSETS)).then(()=>self.skipWaiting()));
});
self.addEventListener('activate',event=>{
  event.waitUntil(caches.keys().then(names=>Promise.all(names
    .filter(name=>name.startsWith(CACHE_PREFIX) && name!==CACHE)
    .map(name=>caches.delete(name)))).then(()=>self.clients.claim()));
});
self.addEventListener('fetch',event=>{
  const request=event.request;
  if(request.method!=='GET')return;
  const url=new URL(request.url);
  if(url.origin!==self.location.origin || url.pathname.startsWith('/api/') || url.pathname.startsWith('/camera/'))return;
  if(!ASSETS.includes(url.pathname))return;
  event.respondWith(fetch(request).catch(async()=>{
    return (await caches.match(url.pathname,{cacheName:CACHE})) || Response.error();
  }));
});
