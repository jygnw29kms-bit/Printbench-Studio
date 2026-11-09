"""One-use PINs and cookie sessions shared by the Windows dialog and web server."""
from __future__ import annotations

import hashlib
import os
import pathlib
import secrets
import sqlite3
import subprocess
import threading
import time
from contextlib import closing, contextmanager, suppress

BASE = pathlib.Path(os.environ.get('LOCALAPPDATA', str(pathlib.Path.home() / 'AppData' / 'Local'))) / 'PRINTBENCH' / 'mobile'
TOKEN = BASE / 'control.token'
LEGACY_PIN = BASE / 'pairing.code'
SESSIONS = BASE / 'sessions.sqlite3'
PIN_AGE = 15 * 60
SESSION_AGE = 30 * 24 * 3600
MAX_ATTEMPTS = 5
WINDOW = 600
ATTEMPTS = {}
ATTEMPT_LOCK = threading.Lock()


def protect(path):
    if os.name == 'nt':
        user = os.environ.get('USERNAME')
        if user:
            with suppress(OSError):
                subprocess.run(
                    ['icacls', str(path), '/inheritance:r', '/grant:r',
                     f'{user}:F', '*S-1-5-18:F', '*S-1-5-32-544:F'],
                    capture_output=True, check=False,
                )
    else:
        path.chmod(0o600)


def _is_pin(code):
    return isinstance(code, str) and len(code) == 8 and code.isascii() and code.isdigit()


@contextmanager
def _open_store(write=False):
    if write:
        BASE.mkdir(parents=True, exist_ok=True)
    new_file = write and not SESSIONS.exists()
    with closing(sqlite3.connect(SESSIONS, timeout=3)) as db, db:
        if new_file:
            protect(SESSIONS)
        migrate_pin = False
        if write:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE IF NOT EXISTS sessions(token_hash TEXT PRIMARY KEY, expiry INTEGER NOT NULL)')
            migrate_pin = db.execute(
                "SELECT 1 FROM sqlite_master WHERE type='table' AND name='pairing_pin'"
            ).fetchone() is None
            if migrate_pin:
                db.execute('CREATE TABLE pairing_pin(id INTEGER PRIMARY KEY CHECK(id=1), code TEXT NOT NULL, expiry INTEGER NOT NULL)')
                with suppress(OSError, ValueError):
                    expiry, code = LEGACY_PIN.read_text(encoding='ascii').strip().split(':', 1)
                    if int(expiry) > time.time() and _is_pin(code):
                        db.execute('INSERT INTO pairing_pin VALUES(1, ?, ?)', (code, int(expiry)))
        yield db
    if migrate_pin:
        with suppress(OSError):
            LEGACY_PIN.unlink(missing_ok=True)


def initialize():
    """Prepare storage without opening a new pairing window."""
    with _open_store(write=True):
        if not TOKEN.exists():
            TOKEN.write_text(secrets.token_hex(32), encoding='ascii')
            protect(TOKEN)


def ensure_pairing_code():
    """Return the PIN and its expiry from the same transaction."""
    with _open_store(write=True) as db:
        now = int(time.time())
        row = db.execute('SELECT code, expiry FROM pairing_pin WHERE id=1 AND expiry>?', (now,)).fetchone()
        if row is None:
            row = (f'{secrets.randbelow(100000000):08d}', now + PIN_AGE)
            db.execute('INSERT OR REPLACE INTO pairing_pin VALUES(1, ?, ?)', row)
        return {'code': row[0], 'expires_at': row[1]}


def pairing_seconds_remaining():
    if not SESSIONS.is_file():
        return 0
    with _open_store() as db:
        row = db.execute('SELECT expiry FROM pairing_pin WHERE id=1').fetchone()
    return max(0, row[0] - int(time.time())) if row else 0


def _digest(value):
    return hashlib.sha256(value.encode('utf-8')).hexdigest()


def authenticated_session(value):
    if not value or len(value) > 200 or not SESSIONS.is_file():
        return False
    try:
        with _open_store() as db:
            row = db.execute('SELECT expiry FROM sessions WHERE token_hash=?', (_digest(value),)).fetchone()
        return bool(row and row[0] > time.time())
    except (OSError, sqlite3.Error):
        return False


def revoke_session(value):
    if not value or len(value) > 200 or not SESSIONS.is_file():
        return
    with _open_store(write=True) as db:
        db.execute('DELETE FROM sessions WHERE token_hash=?', (_digest(value),))


def pair_and_create_session(code, ip):
    if not _is_pin(code):
        return None, 'invalid_format'
    with ATTEMPT_LOCK:
        now = int(time.time())
        attempts = [ts for ts in ATTEMPTS.get(ip, []) if now - ts < WINDOW]
        if len(attempts) >= MAX_ATTEMPTS:
            return None, 'too_many_attempts'
        try:
            with _open_store(write=True) as db:
                now = int(time.time())
                row = db.execute('SELECT code, expiry FROM pairing_pin WHERE id=1').fetchone()
                if row is None:
                    return None, 'pairing_not_initialized'
                if row[1] <= now:
                    return None, 'expired_code'
                if not secrets.compare_digest(row[0], code):
                    ATTEMPTS[ip] = attempts + [now]
                    return None, 'invalid_code'
                value = secrets.token_urlsafe(40)
                db.execute('DELETE FROM sessions WHERE expiry<=?', (now,))
                db.execute('INSERT INTO sessions VALUES(?, ?)', (_digest(value), now + SESSION_AGE))
                # A rollback restores the PIN if creating the session fails.
                db.execute('DELETE FROM pairing_pin WHERE id=1')
        except (OSError, sqlite3.Error):
            return None, 'session_storage_unavailable'
        ATTEMPTS.pop(ip, None)
        return value, None


def pair(code, ip):
    """Compatibility for callers that only need the success flag."""
    _, reason = pair_and_create_session(code, ip)
    return reason is None
