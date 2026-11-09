"""PRINTBENCH local material inventory and prepared print queue.

Storage is local to the Windows companion, never on a cloud service.
Prepared jobs are NOT sent to a busy printer automatically.
"""
from __future__ import annotations
import os, sqlite3, time, uuid
from pathlib import Path
from contextlib import contextmanager

BASE=Path(os.environ.get('LOCALAPPDATA',str(Path.home()/'AppData'/'Local')))/'PRINTBENCH'/'mobile'
DB=BASE/'workspace.sqlite3'
UPLOADS=Path(os.environ.get('PRINTBENCH_MOBILE_UPLOADS') or BASE/'uploads').resolve()
MATERIAL_TYPES={'PLA','PETG','ABS','ASA','TPU','PA','PC','PVA','OTHER'}

@contextmanager
def connection():
    BASE.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(DB,timeout=5)
    db.row_factory=sqlite3.Row
    try:
        db.execute("""CREATE TABLE IF NOT EXISTS materials (
             id TEXT PRIMARY KEY, label TEXT NOT NULL, vendor TEXT NOT NULL,
             material TEXT NOT NULL, color TEXT NOT NULL, remaining_g REAL NOT NULL,
             profile TEXT NOT NULL, note TEXT NOT NULL, updated INTEGER NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS queue (
             id TEXT PRIMARY KEY, upload_name TEXT NOT NULL,
             position INTEGER NOT NULL, status TEXT NOT NULL,
             created INTEGER NOT NULL)""")
        db.commit()
        yield db
        db.commit()
    finally:
        db.close()

def list_materials():
    with connection() as db:
        return {'items':[dict(r) for r in db.execute(
            'SELECT * FROM materials ORDER BY updated DESC LIMIT 500').fetchall()]}

def _short(value,maxlen=100):
    if not isinstance(value,str):raise ValueError('text_required')
    value=value.strip()
    if len(value)>maxlen:raise ValueError('text_too_long')
    return value

def save_material(data):
    label=_short(data.get('label',''),90)
    vendor=_short(data.get('vendor',''),70)
    material=_short(data.get('material',''),16).upper()
    color=_short(data.get('color',''),7).upper()
    profile=_short(data.get('profile',''),120)
    note=_short(data.get('note',''),250)
    if not label:raise ValueError('material_label_required')
    if material not in MATERIAL_TYPES:raise ValueError('unsupported_material_type')
    if len(color)!=7 or color[0]!='#' or any(c not in '0123456789ABCDEF' for c in color[1:]):
        raise ValueError('invalid_color')
    try:remaining=float(data.get('remaining_g'))
    except (ValueError,TypeError):raise ValueError('invalid_remaining_mass')
    if not 0<=remaining<=100000:raise ValueError('mass_out_of_range')
    id=_short(data.get('id',''),36) or uuid.uuid4().hex
    with connection() as db:
        db.execute("""INSERT INTO materials(id,label,vendor,material,color,remaining_g,profile,note,updated)
          VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
          label=excluded.label,vendor=excluded.vendor,material=excluded.material,color=excluded.color,
          remaining_g=excluded.remaining_g,profile=excluded.profile,note=excluded.note,updated=excluded.updated""",
          (id,label,vendor,material,color,remaining,profile,note,int(time.time())))
    return {'ok':True,'id':id}

def remove_material(id):
    id=_short(id,36)
    with connection() as db:
        changed=db.execute('DELETE FROM materials WHERE id=?',(id,)).rowcount
    return {'ok':True,'deleted':bool(changed)}

def queue_display_name(upload_name):
    """Remove the local timestamp/random-id prefix; never expose it as a real title."""
    parts=str(upload_name).split('-',2)
    if len(parts)==3 and parts[0].isdigit() and len(parts[1])==12 and all(
        c in '0123456789abcdefABCDEF' for c in parts[1]):
        return parts[2]
    return str(upload_name)


def list_queue():
    with connection() as db:
        rows=[dict(r) for r in db.execute(
            'SELECT * FROM queue ORDER BY position ASC, created ASC LIMIT 200').fetchall()]
    for row in rows:
        stored=str(row['upload_name'])
        path=UPLOADS/stored
        size=None
        if path.parent==UPLOADS and not path.is_symlink() and path.is_file():
            try:
                size=path.stat().st_size
            except OSError:
                pass
        row['display_name']=queue_display_name(stored)
        row['file_available']=size is not None
        row['bytes']=size
        row['file_type']=path.suffix.lower() if size is not None else ''
    return {'items':rows,'auto_start':False,'count':len(rows)}

def queue_file(upload_name,uploads):
    name=_short(upload_name,170)
    if not name or Path(name).name!=name or not (uploads/name).is_file():
        raise ValueError('uploaded_file_not_found')
    if (uploads/name).suffix.lower() not in {'.3mf','.stl','.gcode','.gco','.bgcode'}:
        raise ValueError('unsupported_file_type')
    with connection() as db:
        exists=db.execute('SELECT id FROM queue WHERE upload_name=?',(name,)).fetchone()
        if exists:return {'ok':True,'id':exists[0],'duplicate':True}
        pos=db.execute('SELECT COALESCE(MAX(position),0)+1 FROM queue').fetchone()[0]
        id=uuid.uuid4().hex
        db.execute('INSERT INTO queue(id,upload_name,position,status,created) VALUES(?,?,?,?,?)',
                   (id,name,pos,'prepared',int(time.time())))
    return {'ok':True,'id':id,'auto_start':False}

def remove_uploaded_file(upload_name,uploads):
    """Delete only an unqueued regular file from the managed upload directory.

    The shared queue is checked using the same write transaction as other
    queue changes. Neither slicer projects outside uploads nor queued jobs
    can be removed by this API.
    """
    name=_short(upload_name,170)
    if not name or Path(name).name!=name or name in ('.','..'):
        raise ValueError('invalid_file_name')
    if Path(name).suffix.lower() not in {'.3mf','.stl','.gcode','.gco','.bgcode'}:
        raise ValueError('unsupported_file_type')
    path=uploads/name
    if path.is_symlink() or not path.is_file() or path.parent.resolve()!=uploads.resolve():
        raise ValueError('uploaded_file_not_found')
    with connection() as db:
        if db.execute('SELECT 1 FROM queue WHERE upload_name=?',(name,)).fetchone():
            raise ValueError('file_is_in_queue_remove_queue_entry_first')
        try:
            size=path.stat().st_size
            path.unlink()
        except OSError as exc:
            raise ValueError('file_delete_failed') from exc
    return {'ok':True,'deleted':True,'freed_bytes':size,'auto_start':False}


def move_queued(id,direction):
    id=_short(id,36)
    if direction not in ('up','down'):raise ValueError('invalid_direction')
    with connection() as db:
        rows=db.execute('SELECT id FROM queue ORDER BY position ASC,created ASC').fetchall()
        ids=[row['id'] for row in rows]
        if id not in ids:raise ValueError('queue_entry_not_found')
        index=ids.index(id)
        target=index+(-1 if direction=='up' else 1)
        if 0<=target<len(ids):
            ids[index],ids[target]=ids[target],ids[index]
            for pos,ident in enumerate(ids,1):
                db.execute('UPDATE queue SET position=? WHERE id=?',(pos,ident))
    return {'ok':True,'id':id,'moved':0<=target<len(ids),'auto_start':False}

def remove_queued(id):
    id=_short(id,36)
    with connection() as db:
        changed=db.execute('DELETE FROM queue WHERE id=?',(id,)).rowcount
    return {'ok':True,'deleted':bool(changed),'file_untouched':True}
