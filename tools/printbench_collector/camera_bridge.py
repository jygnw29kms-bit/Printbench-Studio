"""Single-session P2S camera bridge, local RTSPS/H.264 to JPEG.

Uses the MIT-licensed strands-cad RTSP implementation (vendored in
vendor_strands_camera.py) to avoid the FFmpeg RTSPS LIVE555 handshake hang.
No cloud, no media uploads. Snapshot is atomically replaced for the local UI.
"""
from __future__ import annotations
import json, os, signal, time
from pathlib import Path
import collector
from vendor_strands_camera import BambuCamera

ROOT=Path(__file__).resolve().parent
RUNTIME=Path(os.environ.get('PRINTBENCH_CAMERA_RUNTIME',ROOT/'runtime'/'camera'))
SNAPSHOT=RUNTIME/'latest.jpg'
TMP=RUNTIME/'latest.tmp.jpg'
VIEWER_MARK=RUNTIME/'viewer.active'
STATUS=RUNTIME/'status.json'
STOP=False

def stop(*_):
    global STOP
    STOP=True

def viewer_active(max_age=7.0):
    try:
        return VIEWER_MARK.is_file() and time.time()-VIEWER_MARK.stat().st_mtime<max_age
    except OSError:
        return False

def _save_status(camera,bytes_written):
    status=camera.status()
    result={
        'service':'PRINTBENCH camera bridge',
        'online':bytes_written>5000 and SNAPSHOT.exists() and time.time()-SNAPSHOT.stat().st_mtime<15,
        'last_frame_age_s':status.get('last_frame_age_s'),
        'frames':status.get('frames',0),
        'error':status.get('error') if not bytes_written else None,
        'source':'P2S LAN RTSPS',
        'liveview_required':True
    }
    # No access codes, stream URLs, or credentials in web-accessible state.
    tmp=RUNTIME/'status.tmp.json'
    tmp.write_text(json.dumps(result,ensure_ascii=False),encoding='utf-8')
    tmp.replace(STATUS)

def run_forever(active_interval=0.8,idle_interval=15.0):
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    serial,access=collector.load_local_bambu_identity()
    if not access:
        raise RuntimeError('Bambu LAN access identity not configured')
    RUNTIME.mkdir(parents=True,exist_ok=True)
    camera=BambuCamera(collector.P2S_HOST,access,fps=10,quality=6,width=960)
    camera.start()
    last_frame=None
    last_written=0.0
    last_status=0.0
    announced_error=''
    try:
        while not STOP:
            frame=camera.latest()
            state=camera.status()
            interval=active_interval if viewer_active() else idle_interval
            if frame and frame is not last_frame and time.monotonic()-last_written>=interval:
                if len(frame)>5000 and frame.startswith(b'\xff\xd8') and frame.endswith(b'\xff\xd9'):
                    tmp=TMP
                    tmp.write_bytes(frame)
                    tmp.replace(SNAPSHOT)
                    last_written=time.monotonic()
                    last_frame=frame
            if time.monotonic()-last_status>5:
                _save_status(camera,len(frame) if frame else 0)
                last_status=time.monotonic()
            error=str(state.get('error') or '')
            if error and error!=announced_error:
                # Don't print authenticated stream URL or other secrets.
                sanitized=error.replace(access,'[REDACTED]')
                print('[PRINTBENCH CAMERA] '+sanitized[:180],flush=True)
                announced_error=error
            elif not error:
                announced_error=''
            time.sleep(.25)
    finally:
        camera.stop()

if __name__=='__main__':
    run_forever()
