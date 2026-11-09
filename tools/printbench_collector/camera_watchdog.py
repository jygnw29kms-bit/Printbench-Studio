"""Keep the local P2S RTSPS camera running and recover stuck decoders.

One supervisor owns one child. Uses a local Windows file lock so repeated
PRINTBENCH startup never creates duplicate camera connections.
"""
from __future__ import annotations
import os, subprocess, sys, time, signal
from pathlib import Path

ROOT=Path(__file__).resolve().parent
RUNTIME=Path(os.environ.get('PRINTBENCH_CAMERA_RUNTIME',ROOT/'runtime'/'camera'))
SNAPSHOT=RUNTIME/'latest.jpg'
LOCK=RUNTIME/'camera-watchdog.lock'
LOG=RUNTIME/'camera-watchdog.log'
STOP=False

def terminate(*_):
    global STOP
    STOP=True

def fresh(limit=105):
    try:return SNAPSHOT.stat().st_size>5000 and 0<=time.time()-SNAPSHOT.stat().st_mtime<limit
    except OSError:return False

def write_log(message):
    with LOG.open('a',encoding='utf-8') as log:
        log.write(time.strftime('%Y-%m-%d %H:%M:%S')+' '+message+'\n')

def run():
    import msvcrt
    RUNTIME.mkdir(parents=True,exist_ok=True)
    with LOCK.open('a+b') as lock:
        lock.seek(0)
        lock.write(b'0')
        lock.flush()
        lock.seek(0)
        try:msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
        except OSError:return
        signal.signal(signal.SIGINT,terminate)
        signal.signal(signal.SIGTERM,terminate)
        child=None
        started=0.0
        last_fresh=time.monotonic()
        restarts=0
        try:
            while not STOP:
                if child is None or child.poll() is not None:
                    if child is not None:
                        write_log('camera worker exited with code '+str(child.returncode))
                    # Give the P2S RTSPS service time to release its previous connection.
                    if restarts:
                        time.sleep(min(20,3*restarts))
                    child=subprocess.Popen([sys.executable,'-u',str(ROOT/'camera_bridge.py')],
                         cwd=str(ROOT),env=os.environ.copy(),stdin=subprocess.DEVNULL,
                         stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,
                         creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    started=time.monotonic()
                    last_fresh=started
                    restarts+=1
                    write_log('camera worker launched PID='+str(child.pid))
                if fresh():
                    last_fresh=time.monotonic()
                    restarts=0
                # Check the JPEG's actual age, not a repeatedly refreshed observation
                # timestamp. Otherwise a frozen frame can delay recovery to ~210 s.
                if time.monotonic()-started>105 and not fresh(105):
                    write_log('camera stalled; restarting worker after 105 seconds without fresh frame')
                    child.terminate()
                    try:child.wait(timeout=8)
                    except subprocess.TimeoutExpired:
                        child.kill()
                        child.wait(timeout=5)
                    child=None
                time.sleep(5)
        finally:
            if child and child.poll() is None:
                child.terminate()
                try:child.wait(timeout=8)
                except subprocess.TimeoutExpired:child.kill()
            lock.seek(0)
            msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)

if __name__=='__main__':
    run()
