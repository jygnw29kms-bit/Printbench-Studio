from __future__ import annotations
import json, os, secrets, sqlite3, socket, subprocess, sys, threading, time, ssl
from datetime import datetime, timezone, timedelta
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote, quote
from http.cookies import SimpleCookie
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
import command_engine
import local_tls
import mobile_pairing
import mobile_workspace

ROOT=Path(__file__).resolve().parent
COLLECTOR=ROOT.parent
DB=COLLECTOR/'printbench.db'
STATIC=ROOT/'static'
CAMERA_SNAPSHOT=Path(os.environ.get('PRINTBENCH_CAMERA_SNAPSHOT','/run/printbench-camera/latest.jpg'))
CAMERA_VIEWER=CAMERA_SNAPSHOT.parent/'viewer.active'
CAMERA_STATUS=CAMERA_SNAPSHOT.parent/'status.json'
API_PREFIX='/api/v1'
CAMERA_STREAMS=threading.BoundedSemaphore(2)
CONTROL_TOKEN_FILE=Path(os.environ.get('PRINTBENCH_CONTROL_TOKEN_FILE','/etc/printbench/control.token'))
MAX_CONTROL_BODY=4096
UPLOADS=Path(os.environ.get('PRINTBENCH_MOBILE_UPLOADS',str(mobile_pairing.BASE/'uploads')))
MAX_UPLOAD_BYTES=256*1024*1024
UPLOAD_EXTS={'.3mf','.stl','.gcode','.gco','.bgcode'}


def dbconn():
    con=sqlite3.connect(f'file:{DB}?mode=ro',uri=True,timeout=2)
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA query_only=ON')
    return con


def _table_exists(db,name):
    return bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(name,)).fetchone())


def safe_json(v,default=None):
    if not v:return default
    try:return json.loads(v)
    except Exception:return default


def camera_fresh(max_age=30):
    try:return CAMERA_SNAPSHOT.is_file() and CAMERA_SNAPSHOT.stat().st_size>5000 and time.time()-CAMERA_SNAPSHOT.stat().st_mtime<max_age
    except Exception:return False


def camera_state():
    try:
        state=json.loads(CAMERA_STATUS.read_text(encoding='utf-8')) if CAMERA_STATUS.exists() else {}
        error=str(state.get('error') or '')[:200]
        if 'timeout' in error.lower():
            error='P2S-Kamera meldet keine RTSPS-Daten. Andere Kamera-Apps schließen; LAN-Liveview am P2S aus- und wieder einschalten.'
        elif 'ssl' in error.lower() or 'tls' in error.lower():
            error='P2S-Kamera: TLS-Verbindung fehlgeschlagen. LAN-Liveview und Netzwerk prüfen.'
        return {'online':camera_fresh(),'error':error,
                'frame_age_sec':round(time.time()-CAMERA_SNAPSHOT.stat().st_mtime,1) if CAMERA_SNAPSHOT.exists() else None,
                'frames':int(state.get('frames') or 0),
                'printer_liveview':bool(state.get('liveview_required'))}
    except Exception:return {'online':False,'error':'camera_status_unavailable','frame_age_sec':None}


def latest_payload():
    with dbconn() as db:
        r=db.execute('''SELECT ts,print_state,progress,remaining_min,layer_current,layer_total,
          nozzle_c,nozzle_target_c,bed_c,bed_target_c,chamber_c,wifi_rssi,speed_level,speed_mag,
          fan_part,fan_aux,fan_chamber,fan_heatbreak,print_stage,print_sub_stage,print_error,fail_reason,
          ams_json,ipcam_json,hms_json,raw_json FROM telemetry ORDER BY id DESC LIMIT 1''').fetchone()
        if not r:return {'online':False,'reason':'no_telemetry'}
        out={k:r[k] for k in r.keys() if k not in ('ams_json','ipcam_json','hms_json')}
        ams=safe_json(r['ams_json'],{}) or {};unit=(ams.get('ams') or [{}])[0]
        out['ams']={'temp_c':unit.get('temp'),'humidity':unit.get('humidity'),'humidity_raw':unit.get('humidity_raw'),
          'active_slot':ams.get('tray_now'),'tray_exist_bits':ams.get('tray_exist_bits'),'dry_time':unit.get('dry_time',0),
          'dry_setting':unit.get('dry_setting') or {},'slots':[{'id':str(t.get('id','')),'state':t.get('state'),
          'material':t.get('tray_type') or '','color':t.get('tray_color') or '','remain':t.get('remain'),'source':'printer_report'}
          for t in (unit.get('tray',[]) or []) if isinstance(t,dict)]}
        ip=safe_json(r['ipcam_json'],{}) or {}
        out['camera']={'printer_liveview':bool(ip.get('liveview_preview')),'browser_bridge':camera_fresh(),
          'recording':ip.get('ipcam_record')=='enable','timelapse':ip.get('timelapse')=='enable','resolution':ip.get('resolution')}
        raw=safe_json(r['raw_json'],{}) or {}
        airduct=(raw.get('print') or {}).get('airduct') or {}
        try:
            mode=int(airduct.get('modeCur',-1))
            out['airduct_mode']=mode if mode in (0,1) else None
        except (ValueError,TypeError,AttributeError):out['airduct_mode']=None
        hms=safe_json(r['hms_json'],[]) or [];out['hms_count']=len(hms) if isinstance(hms,list) else 0
        try:age=(datetime.now(timezone.utc)-datetime.fromisoformat(r['ts'])).total_seconds()
        except Exception:age=9999
        out['online']=age<45;out['age_sec']=round(age,1)
        return out


def history(hours=24,limit=240):
    hours=max(1,min(int(hours),24*30));limit=max(20,min(int(limit),500));cutoff=(datetime.now(timezone.utc)-timedelta(hours=hours)).isoformat()
    with dbconn() as db:rows=db.execute('''SELECT ts,progress,nozzle_c,nozzle_target_c,bed_c,bed_target_c,chamber_c,wifi_rssi FROM telemetry WHERE ts>=? ORDER BY id''',(cutoff,)).fetchall()
    data=[dict(x) for x in rows]
    if len(data)>limit:
        step=(len(data)-1)/(limit-1);data=[data[round(i*step)] for i in range(limit)]
    return {'hours':hours,'points':data,'source_points':len(rows)}


def sessions(limit=20):
    with dbconn() as db:rows=db.execute('''SELECT id,started_at,ended_at,state,outcome,max_progress,max_layer,filament_type,filament_vendor,planned_filament_g,actual_time_sec,self_cost_eur,sale_price_eur,energy_is_estimated FROM print_sessions ORDER BY id DESC LIMIT ?''',(max(1,min(int(limit),50)),)).fetchall()
    return [dict(x) for x in rows]


def rfid_summary():
    with dbconn() as db:rows=db.execute('''SELECT o.ams_id,o.slot_id,o.ts,o.tray_present,o.reading,o.read_done,o.is_bambu,o.tray_state,o.tray_info_idx,o.tray_type,o.tray_color,o.tag_uid,o.tray_uuid FROM ams_rfid_observations o JOIN (SELECT ams_id,slot_id,MAX(id) id FROM ams_rfid_observations GROUP BY ams_id,slot_id) x ON x.id=o.id ORDER BY CAST(o.slot_id AS INTEGER)''').fetchall()
    out=[]
    for r in rows:
        d=dict(r);uid=d.pop('tag_uid',None);uuid=d.pop('tray_uuid',None);d['uid_exposed']=False
        d['uid_nonzero_observed']=uid not in (None,'','0000000000000000');d['uuid_nonzero_observed']=uuid not in (None,'','00000000000000000000000000000000')
        d['confidence']='reported' if d.get('read_done') else 'transient';out.append(d)
    return out


def external_tags(limit=16):
    with dbconn() as db:
        if not _table_exists(db,'external_tag_observations'):return {'items':[],'uid_exposed':False,'available':False}
        rows=db.execute('''SELECT id,ts,reader_id,ams_id,slot_id,tag_type,spool_id,matched FROM external_tag_observations ORDER BY id DESC LIMIT ?''',(max(1,min(int(limit),64)),)).fetchall()
    return {'items':[dict(x) for x in rows],'uid_exposed':False,'available':True}


def spools():
    with dbconn() as db:
        rows=db.execute('''SELECT spool_id,display_name,vendor,material,color_name,color_hex,filament_profile,remaining_g,initial_net_g,purchase_price_eur,nozzle_temp_min,nozzle_temp_max,dry_temp_c,dry_duration_h,last_dried_at,status,ams_id,ams_slot,nfc_tag_type,server_updated_at,synced_at FROM spool_inventory ORDER BY COALESCE(display_name,spool_id)''').fetchall()
        matches=db.execute('SELECT COUNT(*) FROM ams_spool_matches WHERE matched=1').fetchone()[0]
        ready=db.execute("SELECT COUNT(*) FROM ams_action_proposals WHERE status='ready'").fetchone()[0]
        blocked=db.execute("SELECT COUNT(*) FROM ams_action_proposals WHERE status='blocked'").fetchone()[0]
    return {'items':[dict(x) for x in rows],'matched_count':matches,'ready_proposals':ready,'blocked_proposals':blocked,'uid_exposed':False}



def firmware():
    with dbconn() as db:
        if not _table_exists(db,'device_modules'):
            return {'items':[],'available':False}
        rows=db.execute("SELECT name,hw_ver,sw_ver,updated_at FROM device_modules ORDER BY CASE name WHEN 'ota' THEN 0 ELSE 1 END,name").fetchall()
    return {'items':[dict(x) for x in rows],'available':True}


def system_info():
    def cmd(args):
        try:return subprocess.check_output(args,text=True,stderr=subprocess.DEVNULL,timeout=1).strip()
        except Exception:return None
    try:temp=round(int(Path('/sys/class/thermal/thermal_zone0/temp').read_text())/1000,1)
    except Exception:temp=None
    try:
        st=os.statvfs('/');disk={'total_gb':round(st.f_blocks*st.f_frsize/1e9,1),'free_gb':round(st.f_bavail*st.f_frsize/1e9,1)}
    except Exception:disk=None
    if os.name=='nt':
        try:
            import shutil
            st=shutil.disk_usage(str(Path.home()))
            disk={'total_gb':round(st.total/1e9,1),'free_gb':round(st.free/1e9,1)}
        except OSError:pass
    try:uptime=int(float(Path('/proc/uptime').read_text().split()[0]))
    except Exception:uptime=None
    if os.name=='nt':
        try:
            import ctypes
            ctypes.windll.kernel32.GetTickCount64.restype=ctypes.c_ulonglong
            uptime=int(ctypes.windll.kernel32.GetTickCount64()/1000)
        except Exception:pass
    try:cam_age=round(time.time()-CAMERA_SNAPSHOT.stat().st_mtime,1) if CAMERA_SNAPSHOT.exists() else None
    except Exception:cam_age=None
    return {'hostname':socket.gethostname(),'pi_temp_c':temp,'collector':('ONLINE' if latest_payload().get('online') else 'TELEMETRIE FEHLT') if os.name=='nt' else (cmd(['systemctl','is-active','printbench-collector.service']) or 'unknown'),
      'camera_bridge':'active' if camera_fresh() else 'unavailable','reader_bridge':('NICHT EINGERICHTET' if os.name=='nt' else (cmd(['systemctl','is-active','printbench-reader.service']) or 'inactive')),'camera_snapshot_age_sec':cam_age,'camera_error':camera_state().get('error'),'ui':'active',
      'uptime_sec':uptime,'disk':disk,'time':datetime.now(timezone.utc).isoformat()}


def _control_token():
    try:
        token=CONTROL_TOKEN_FILE.read_text(encoding='utf-8').strip()
        if len(token) != 64 or any(ch not in '0123456789abcdefABCDEF' for ch in token):
            return ''
        return token
    except Exception:return ''


def control_catalog(authorized=False):
    items={}
    for name,value in command_engine.capabilities().items():
        item=dict(value)
        if not authorized and item.get('enabled'):
            item['enabled']=False;item['status']='authorization_required'
        items[name]=item
    return {'available':bool(_control_token()),'browser_write_endpoint':bool(authorized),'items':items}


def capabilities():
    return {'api':'v1','read_only':True,'printer':'P2S','material_system':'AMS 2 Pro','features':{'telemetry':True,'history':True,
      'sessions':True,'ams_status':True,'rfid_diagnostics':True,'external_tag_observations':True,'spool_inventory':True,
      'camera_browser_bridge':camera_fresh(),'camera_mjpeg':camera_fresh(),'reader_serial_bridge':True,'device_firmware':True,
      'control_catalog':True,'native_control_api':bool(_control_token()),'raw_mqtt_control':False,'raw_uid_browser':False}}


class Handler(SimpleHTTPRequestHandler):
    server_version='PRINTBENCH';sys_version='';protocol_version='HTTP/1.1'
    def end_headers(self):
        # A fixed local IP is frequently saved to the iPhone home screen.
        # Do not let Safari keep an older broken PRINTBENCH user interface.
        self.send_header('Cache-Control','no-store, max-age=0')
        self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Cross-Origin-Resource-Policy','same-origin')
        self.send_header('Referrer-Policy','no-referrer');self.send_header('Permissions-Policy','camera=(), microphone=(), geolocation=()')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");super().end_headers()
    def list_directory(self,path):self.send_error(403);return None
    def _json(self,obj,status=200,cookie=None):
        raw=json.dumps(obj,ensure_ascii=False,separators=(',',':')).encode()
        self.send_response(status)
        self.send_header('Content-Type','application/json; charset=utf-8')
        self.send_header('Cache-Control','no-store')
        if cookie:self.send_header('Set-Cookie',cookie)
        self.send_header('Content-Length',str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)
    def _viewer_touch(self):
        try:CAMERA_VIEWER.touch();return True
        except Exception:return False
    def _jpeg(self):
        self._viewer_touch()
        try:
            if not camera_fresh(30):self.send_error(503,'Camera frame stale');return
            raw=CAMERA_SNAPSHOT.read_bytes();self.send_response(200);self.send_header('Content-Type','image/jpeg');self.send_header('Cache-Control','no-store, max-age=0');self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        except OSError:self.send_error(404)
    def _mjpeg(self):
        if not CAMERA_STREAMS.acquire(blocking=False):
            return self._json({'error':'camera_busy'},503)
        try:
            self._viewer_touch()
            # Never leave an iPhone's MJPEG image pending indefinitely when the
            # local decoder is down. A 503 triggers its snapshot fallback.
            if not camera_fresh(30):
                return self._json({'error':'camera_not_ready'},503)
            self.send_response(200)
            self.send_header('Content-Type','multipart/x-mixed-replace; boundary=frame')
            self.send_header('Cache-Control','no-store, no-cache, must-revalidate, max-age=0')
            self.send_header('Connection','close')
            self.end_headers()
            last_mtime=0.0
            stale_since=None
            while True:
                self._viewer_touch()
                if not camera_fresh(30):
                    if stale_since is None:stale_since=time.monotonic()
                    if time.monotonic()-stale_since>8:
                        # Closing the stream permits Safari to reconnect or
                        # fall back, rather than displaying a frozen image.
                        break
                    time.sleep(.5)
                    continue
                stale_since=None
                st=CAMERA_SNAPSHOT.stat()
                if st.st_mtime<=last_mtime:time.sleep(.2);continue
                raw=CAMERA_SNAPSHOT.read_bytes();last_mtime=st.st_mtime
                if len(raw)<5000:continue
                self.wfile.write(b'--frame\r\nContent-Type: image/jpeg\r\nContent-Length: '+str(len(raw)).encode()+b'\r\n\r\n'+raw+b'\r\n')
                self.wfile.flush()
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):
            pass
        finally:
            CAMERA_STREAMS.release()
    def _is_tls(self):
        return isinstance(self.connection,ssl.SSLSocket)
    def _same_origin(self):
        origin=self.headers.get('Origin','')
        if not origin:return False
        host=self.headers.get('Host','')
        return origin==('https://' + host)
    def _session_value(self):
        try:
            cookie=SimpleCookie()
            cookie.load(self.headers.get('Cookie',''))
            return cookie['PRINTBENCH_SESSION'].value if 'PRINTBENCH_SESSION' in cookie else ''
        except Exception:return ''
    def _control_authorized(self):
        if not self._is_tls():return False
        if mobile_pairing.authenticated_session(self._session_value()):return True
        expected=_control_token();provided=self.headers.get('X-API-Key','')
        return bool(expected and provided and secrets.compare_digest(expected,provided))
    def _upload_file(self):
        try:
            length=int(self.headers.get('Content-Length','0'))
        except ValueError:return self._json({'error':'invalid_file_length'},400)
        if length<=0 or length>MAX_UPLOAD_BYTES:return self._json({'error':'file_size_out_of_range'},413)
        if (self.headers.get('Content-Type') or '').split(';',1)[0]!='application/octet-stream':
            return self._json({'error':'binary_upload_required'},415)
        original=unquote(self.headers.get('X-File-Name',''))
        clean=''.join(ch for ch in original if ch.isalnum() or ch in '._- ')[:120].strip(' .')
        if not clean or Path(clean).suffix.lower() not in UPLOAD_EXTS:
            return self._json({'error':'unsupported_file_type'},400)
        UPLOADS.mkdir(parents=True,exist_ok=True)
        if sum(p.stat().st_size for p in UPLOADS.iterdir() if p.is_file())+length>1024*1024*1024:
            return self._json({'error':'local_upload_storage_full'},507)
        filename=f'{int(time.time())}-{secrets.token_hex(6)}-{clean}'
        final=UPLOADS/filename
        tmp=UPLOADS/(filename+'.partial')
        left=length
        try:
            with tmp.open('xb') as output:
                while left:
                    chunk=self.rfile.read(min(left,1024*1024))
                    if not chunk:raise OSError('incomplete_upload')
                    output.write(chunk)
                    left-=len(chunk)
            tmp.replace(final)
            return self._json({'ok':True,'name':clean,'stored_as':filename,'bytes':length})
        except OSError:
            tmp.unlink(missing_ok=True)
            return self._json({'error':'upload_failed'},500)
    def _download_file(self,name):
        # Download only an exact file from the managed inbox.
        # Authorization is checked before this method is called.
        if not isinstance(name,str) or not name or len(name)>170:
            return self._json({'error':'invalid_file_name'},400)
        if Path(name).name!=name or name in ('.','..') or '\\' in name or '/' in name:
            return self._json({'error':'invalid_file_name'},400)
        if Path(name).suffix.lower() not in UPLOAD_EXTS:
            return self._json({'error':'unsupported_file_type'},400)
        path=UPLOADS/name
        try:
            if path.is_symlink() or not path.is_file() or path.parent.resolve()!=UPLOADS.resolve():
                return self._json({'error':'file_not_found'},404)
            # Open without following a file that was replaced by a symlink.
            if hasattr(os,'O_NOFOLLOW'):
                fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
                inp=os.fdopen(fd,'rb')
            else:
                inp=path.open('rb')
            with inp:
                st=os.fstat(inp.fileno())
                if not path.is_file() or path.is_symlink():
                    return self._json({'error':'file_not_found'},404)
                original=mobile_workspace.queue_display_name(name)
                ascii_name='PRINTBENCH-download'+path.suffix.lower()
                self.send_response(200)
                self.send_header('Content-Type','application/octet-stream')
                self.send_header('Content-Disposition',
                    'attachment; filename="'+ascii_name+'"; filename*=UTF-8\'\''+quote(original,safe=''))
                self.send_header('Content-Length',str(st.st_size))
                self.end_headers()
                while True:
                    chunk=inp.read(1024*1024)
                    if not chunk:break
                    self.wfile.write(chunk)
        except (OSError,ValueError):
            # If headers have already gone out, a client disconnect is handled
            # by the HTTP server. Never claim a successful transfer.
            return

    def _read_json_body(self):
        if (self.headers.get('Content-Type') or '').split(';',1)[0].strip().lower()!='application/json':
            raise ValueError('application/json required')
        try:length=int(self.headers.get('Content-Length','0'))
        except Exception:raise ValueError('invalid content length')
        if length<0 or length>MAX_CONTROL_BODY:raise ValueError('request body too large')
        raw=self.rfile.read(length) if length else b'{}'
        data=json.loads(raw.decode('utf-8'))
        if not isinstance(data,dict):raise ValueError('JSON object required')
        return data
    def do_POST(self):
        u=urlparse(self.path);path=u.path
        if path.startswith('/api/') and not path.startswith(API_PREFIX+'/'):path=API_PREFIX+path[4:]
        if not self._is_tls():
            return self._json({'error':'https_required'},403)
        if not self._same_origin():
            return self._json({'error':'origin_required'},403)
        if path==API_PREFIX+'/pair':
            try:
                data=self._read_json_body()
                session,reason=mobile_pairing.pair_and_create_session(data.get('code'),self.client_address[0])
                if not session:
                    status=429 if reason=='too_many_attempts' else 503 if reason=='session_storage_unavailable' else 403
                    return self._json({'error':reason or 'pairing_failed'},status)
                cookie='PRINTBENCH_SESSION='+session+'; Path=/api/v1; Secure; HttpOnly; SameSite=Strict; Max-Age=2592000'
                return self._json({'ok':True},cookie=cookie)
            except ValueError:return self._json({'error':'invalid_pairing_request'},400)
        if path==API_PREFIX+'/materials':
            if not self._control_authorized():return self._json({'error':'pairing_required'},403)
            try:return self._json(mobile_workspace.save_material(self._read_json_body()))
            except ValueError as e:return self._json({'error':str(e)},400)
        if path==API_PREFIX+'/materials/delete':
            if not self._control_authorized():return self._json({'error':'pairing_required'},403)
            try:return self._json(mobile_workspace.remove_material(self._read_json_body().get('id','')))
            except ValueError as e:return self._json({'error':str(e)},400)
        if path==API_PREFIX+'/queue':
            if not self._control_authorized():return self._json({'error':'pairing_required'},403)
            try:return self._json(mobile_workspace.queue_file(self._read_json_body().get('upload_name',''),UPLOADS))
            except ValueError as e:return self._json({'error':str(e)},400)
        if path==API_PREFIX+'/queue/move':
            if not self._control_authorized():return self._json({'error':'pairing_required'},403)
            try:
                body=self._read_json_body()
                return self._json(mobile_workspace.move_queued(body.get('id',''),body.get('direction','')))
            except ValueError as e:return self._json({'error':str(e)},400)
        if path==API_PREFIX+'/queue/remove':
            if not self._control_authorized():return self._json({'error':'pairing_required'},403)
            try:return self._json(mobile_workspace.remove_queued(self._read_json_body().get('id','')))
            except ValueError as e:return self._json({'error':str(e)},400)
        if path==API_PREFIX+'/files/delete':
            if not self._control_authorized():return self._json({'error':'pairing_required'},403)
            try:
                payload=self._read_json_body()
                if payload.get('confirm') is not True:
                    return self._json({'error':'confirmation_required'},400)
                return self._json(mobile_workspace.remove_uploaded_file(payload.get('name',''),UPLOADS))
            except ValueError as e:return self._json({'error':str(e)},400)
        if path==API_PREFIX+'/files':
            if not self._control_authorized():return self._json({'error':'pairing_required'},403)
            return self._upload_file()
        if path==API_PREFIX+'/logout':
            mobile_pairing.revoke_session(self._session_value())
            return self._json({'ok':True},cookie='PRINTBENCH_SESSION=; Path=/api/v1; Secure; HttpOnly; SameSite=Strict; Max-Age=0')
        if not path.startswith(API_PREFIX+'/control/'):
            return self._json({'error':'not_found'},404)
        if not self._control_authorized():
            return self._json({'error':'control_authorization_required'},403)
        try:
            body=self._read_json_body();name=path[len(API_PREFIX+'/control/'):].replace('/','.')
            result=command_engine.execute(name,body.get('args') or {},bool(body.get('confirm',False)))
            return self._json(result,200 if result.get('ok') else 409)
        except PermissionError as e:return self._json({'error':'policy','detail':str(e)},403)
        except ValueError as e:return self._json({'error':'invalid','detail':str(e)},400)
        except RuntimeError as e:return self._json({'error':'unavailable','detail':str(e)},409)
        except Exception:return self._json({'error':'internal'},500)
    def do_GET(self):
        u=urlparse(self.path)
        if u.path=='/camera/latest.jpg':return self._jpeg()
        if u.path=='/camera/stream.mjpg':return self._mjpeg()
        if u.path.startswith('/api/'):
            try:
                q=parse_qs(u.query);path=u.path
                if path.startswith('/api/') and not path.startswith(API_PREFIX+'/'):path=API_PREFIX+path[4:]
                if path==API_PREFIX+'/live':return self._json(latest_payload())
                if path==API_PREFIX+'/camera-status':return self._json(camera_state())
                if path==API_PREFIX+'/pairing-status':
                    # PIN bytes are never sent to browsers; only expiry.
                    expires_in=0
                    try:
                        expiry_str=mobile_pairing.PIN.read_text(encoding='ascii').split(':',1)[0]
                        expires_in=max(0,int(expiry_str)-int(time.time()))
                    except (ValueError,OSError):pass
                    return self._json({'https':self._is_tls(),
                        'paired':bool(self._is_tls() and mobile_pairing.authenticated_session(self._session_value())),
                        'control_authorized':self._control_authorized(),
                        'pin_available':expires_in>0,
                        'pin_expires_in_sec':expires_in,
                        'pin_valid_minutes':15})
                if path==API_PREFIX+'/mobile-health':
                    # The app's public health page never reveals session tokens,
                    # certificate private keys or printer access credentials.
                    telemetry=latest_payload()
                    camera=camera_state()
                    return self._json({
                        'version':'V28',
                        'server':'online',
                        'transport':'https' if self._is_tls() else 'http',
                        'paired':bool(self._is_tls() and mobile_pairing.authenticated_session(self._session_value())),
                        'control_authorized':self._control_authorized(),
                        'printer_online':bool(telemetry.get('online')),
                        'telemetry_age_sec':telemetry.get('age_sec'),
                        'print_state':telemetry.get('print_state'),
                        'camera_online':camera.get('online',False),
                        'camera_age_sec':camera.get('frame_age_sec'),
                        'camera_frames':camera.get('frames',0),
                        'camera_error':camera.get('error','')
                    })

                if path==API_PREFIX+'/history':return self._json(history(q.get('hours',['24'])[0],q.get('limit',['240'])[0]))
                if path==API_PREFIX+'/sessions':return self._json(sessions(q.get('limit',['20'])[0]))
                if path==API_PREFIX+'/rfid':return self._json(rfid_summary())
                if path==API_PREFIX+'/external-tags':return self._json(external_tags(q.get('limit',['16'])[0]))
                if path==API_PREFIX+'/spools':return self._json(spools())
                if path==API_PREFIX+'/system':return self._json(system_info())
                if path==API_PREFIX+'/firmware':return self._json(firmware())
                if path==API_PREFIX+'/capabilities':return self._json(capabilities())
                if path==API_PREFIX+'/control-capabilities':return self._json(control_catalog(self._control_authorized()))
                if path==API_PREFIX+'/materials':
                    if not self._control_authorized():return self._json({'error':'pairing_required'},403)
                    return self._json(mobile_workspace.list_materials())
                if path==API_PREFIX+'/queue':
                    if not self._control_authorized():return self._json({'error':'pairing_required'},403)
                    return self._json(mobile_workspace.list_queue())
                if path==API_PREFIX+'/files/download':
                    if not self._control_authorized():return self._json({'error':'pairing_required'},403)
                    names=q.get('name',[])
                    if len(names)!=1:return self._json({'error':'file_name_required'},400)
                    return self._download_file(names[0])
                if path==API_PREFIX+'/files':
                    if not self._control_authorized():return self._json({'error':'pairing_required'},403)
                    UPLOADS.mkdir(parents=True,exist_ok=True)
                    rows=[{'name':p.name,'display_name':mobile_workspace.queue_display_name(p.name),'bytes':p.stat().st_size,'mtime':p.stat().st_mtime} for p in UPLOADS.iterdir() if p.is_file() and not p.is_symlink() and p.suffix.lower() in UPLOAD_EXTS]
                    return self._json({'items':sorted(rows,key=lambda r:r['mtime'],reverse=True)[:100],
                                       'count':len(rows),
                                       'used_bytes':sum(row['bytes'] for row in rows),
                                       'max_bytes':1024*1024*1024})
                return self._json({'error':'not_found'},404)
            except Exception:return self._json({'error':'internal'},500)
        return super().do_GET()
    def handle(self):
        try:super().handle()
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass
    def log_message(self,*args):pass


if __name__=='__main__':
    os.chdir(STATIC);host=os.environ.get('PRINTBENCH_UI_HOST','0.0.0.0');port=int(os.environ.get('PRINTBENCH_UI_PORT','8080'))
    tls_cert=os.environ.get('PRINTBENCH_UI_TLS_CERT','')
    tls_key=os.environ.get('PRINTBENCH_UI_TLS_KEY','')
    server=ThreadingHTTPServer((host,port),Handler)
    if tls_cert and tls_key:
        ctx=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        ctx.minimum_version=ssl.TLSVersion.TLSv1_2
        ctx.load_cert_chain(tls_cert,tls_key)
        server.socket=ctx.wrap_socket(server.socket,server_side=True)
    scheme='https' if tls_cert and tls_key else 'http'
    print(f'[PRINTBENCH UI] {scheme}://{host}:{port}/',flush=True)
    server.serve_forever()
