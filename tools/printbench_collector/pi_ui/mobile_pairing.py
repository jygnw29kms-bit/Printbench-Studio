"""One-use local iPhone pairing. Never sends control secrets over HTTP."""
from __future__ import annotations
import os, pathlib, secrets, threading, time, sqlite3, hashlib
from contextlib import contextmanager
BASE=pathlib.Path(os.environ.get('LOCALAPPDATA',str(pathlib.Path.home()/'AppData'/'Local')))/'PRINTBENCH'/'mobile'
TOKEN=BASE/'control.token'
PIN=BASE/'pairing.code'
LOCK=threading.Lock()
ATTEMPTS={}
MAX_ATTEMPTS=5
WINDOW=600

def protect(path):
    try:
        import subprocess
        user=os.environ.get('USERNAME','')
        if user and os.name=='nt':
            subprocess.run(['icacls',str(path),'/inheritance:r','/grant:r',
                            f'{user}:F','SYSTEM:F','Administrators:F'],capture_output=True,check=False)
    except Exception:pass

def issue_pairing_code():
    BASE.mkdir(parents=True,exist_ok=True)
    if not TOKEN.exists():
        TOKEN.write_text(secrets.token_hex(32),encoding='ascii')
        protect(TOKEN)
    # A pairing code remains valid for 15 minutes and only one successful pairing.
    pin=f'{secrets.randbelow(100000000):08d}'
    PIN.write_text(f'{int(time.time()+900)}:{pin}',encoding='ascii')
    protect(PIN)
    return pin


SESSIONS=BASE/'sessions.sqlite3'
SESSION_AGE=30*24*3600

@contextmanager
def _open_sessions():
    BASE.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(SESSIONS,timeout=3)
    try:
        con.execute('CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, expiry INTEGER NOT NULL)')
        con.execute('DELETE FROM sessions WHERE expiry<?',(int(time.time()),))
        con.commit()
        yield con
        con.commit()
    finally:
        con.close()

def create_session():
    value=secrets.token_urlsafe(40)
    digest=hashlib.sha256(value.encode('ascii')).hexdigest()
    with LOCK, _open_sessions() as db:
        db.execute('INSERT INTO sessions(token_hash,expiry) VALUES(?,?)',(digest,int(time.time()+SESSION_AGE)))
        db.commit()
    protect(SESSIONS)
    return value

def authenticated_session(value):
    if not value or len(value)>200:return False
    digest=hashlib.sha256(value.encode('utf-8')).hexdigest()
    with LOCK, _open_sessions() as db:
        row=db.execute('SELECT expiry FROM sessions WHERE token_hash=?',(digest,)).fetchone()
        return bool(row and row[0]>time.time())

def revoke_session(value):
    if not value or len(value)>200:return
    digest=hashlib.sha256(value.encode('utf-8')).hexdigest()
    with LOCK, _open_sessions() as db:
        db.execute('DELETE FROM sessions WHERE token_hash=?',(digest,))
        db.commit()

def pair(code,ip):
    now=time.time()
    if not isinstance(code,str) or len(code)!=8 or not code.isascii() or not code.isdigit():
        return None
    with LOCK:
        attempts=[t for t in ATTEMPTS.get(ip,[]) if now-t<WINDOW]
        if len(attempts)>=MAX_ATTEMPTS:return None
        attempts.append(now)
        ATTEMPTS[ip]=attempts
        try:
            expiry,pin=PIN.read_text(encoding='ascii').strip().split(':',1)
            if now>int(expiry) or not secrets.compare_digest(pin,code):
                return None
            token=TOKEN.read_text(encoding='ascii').strip()
            if len(token)!=64:return None
            PIN.unlink(missing_ok=True)
            ATTEMPTS.pop(ip,None)
            return token
        except (OSError,ValueError):return None
