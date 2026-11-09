"""PRINTBENCH desktop inbox for files prepared on the iPhone.

Explicit human action opens selected STL/3MF in the native slicer.
Does not publish MQTT commands, start prints or modify active jobs.
"""
from __future__ import annotations
import subprocess
import sys
import tkinter as tk
from tkinter import ttk,messagebox
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'printbench_collector'/'pi_ui'))
import mobile_workspace as workspace

ROOT=Path(__file__).resolve().parent.parent
EXE=ROOT/'app'/'orcaslicer'/'build-printbench-check'/'src'/'Release'/'135er-PRINTBENCH.exe'
UPLOADS=workspace.BASE/'uploads'
PROJECT_EXT={'.stl','.3mf'}
SUPPORTED_EXT=PROJECT_EXT|{'.gcode','.gco','.bgcode'}

class Inbox(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('135er-PRINTBENCH | iPhone Druckdateien')
        self.geometry('930x530')
        self.minsize(730,410)
        self.configure(bg='#071728')
        self.font=('Segoe UI',10)
        style=ttk.Style(self)
        style.theme_use('clam')
        style.configure('PB.Treeview',font=self.font,rowheight=34,
                        background='#0d2539',fieldbackground='#0d2539',
                        foreground='#e8f4fd',borderwidth=0)
        style.configure('PB.Treeview.Heading',font=('Segoe UI',10,'bold'),
                        background='#133650',foreground='#eaf7ff')
        style.map('PB.Treeview',background=[('selected','#125da4')])
        title=tk.Label(self,text='PRINTBENCH   /   DRUCKDATEIEN',font=('Segoe UI',17,'bold'),
                       bg='#071728',fg='#eff8ff',anchor='w')
        title.pack(fill='x',padx=24,pady=(22,4))
        tk.Label(self,text='Vom iPhone vorbereitete Druckdateien. Öffnen nur auf ausdrücklichen Klick; kein automatischer Druckstart.',
                 bg='#071728',fg='#96bad0',anchor='w',wraplength=820).pack(fill='x',padx=24,pady=(0,18))
        columns=('datei','status','groesse','zeit')
        self.tree=ttk.Treeview(self,columns=columns,show='headings',style='PB.Treeview',selectmode='browse')
        for key,label,w in [('datei','Datei',470),('status','Status',120),('groesse','Größe',100),('zeit','Hinzugefügt',150)]:
            self.tree.heading(key,text=label)
            self.tree.column(key,width=w,stretch=key=='datei')
        self.tree.pack(fill='both',expand=True,padx=22)
        footer=tk.Frame(self,bg='#071728')
        footer.pack(fill='x',padx=22,pady=17)
        for label,fn in [
            ('Aktualisieren',self.refresh),('Nach oben',lambda:self.move('up')),('Nach unten',lambda:self.move('down')),('Im Slicer öffnen',self.open_project),
            ('Aus Warteliste entfernen',self.remove_from_queue),('Eingangsordner öffnen',self.open_folder)
        ]:
            tk.Button(footer,text=label,command=fn,relief='flat',cursor='hand2',
                      bg='#114b7a',fg='white',activebackground='#176daa',
                      activeforeground='white',font=('Segoe UI',10,'bold'),
                      padx=13,pady=11).pack(side='left',padx=(0,9))
        self.status=tk.Label(self,text='',bg='#071728',fg='#8de1c7',anchor='w')
        self.status.pack(fill='x',padx=24,pady=(0,14))
        self.tree.bind('<Double-1>',lambda _:self.open_project())
        self.refresh()
        self._auto_refresh_id=None
        self.schedule_refresh()

    def schedule_refresh(self):
        # The native slicer inbox observes the same SQLite workspace as iOS.
        # Read-only refresh, no automatic project opening or printer actions.
        self._auto_refresh_id=self.after(5000,self._refresh_if_idle)

    def _refresh_if_idle(self):
        chosen=self.selected()
        selected_id=chosen['id'] if chosen else None
        self.refresh()
        if selected_id:
            for iid,row in self.rows.items():
                if row['id']==selected_id:
                    self.tree.selection_set(iid)
                    self.tree.focus(iid)
                    break
        self.schedule_refresh()

    def selected(self):
        selection=self.tree.selection()
        return self.rows.get(selection[0]) if selection else None

    def refresh(self):
        try:
            self.rows={}
            self.tree.delete(*self.tree.get_children())
            queue=workspace.list_queue()['items']
            import datetime
            for row in queue:
                path=UPLOADS/row['upload_name']
                size=(path.stat().st_size/1048576) if path.is_file() else None
                stamp=datetime.datetime.fromtimestamp(row['created']).strftime('%d.%m.%Y %H:%M')
                iid=self.tree.insert('',tk.END,values=(
                    row.get('display_name',row['upload_name']),'Bereit' if row.get('file_available') else 'Fehlt',
                    f'{size:.1f} MB' if size is not None else '-',stamp))
                self.rows[iid]=row
            self.status.config(text=f'{len(queue)} vorbereitete Dateien · kein automatischer Druckstart')
        except Exception as e:
            self.status.config(text=f'Warteliste nicht verfügbar: {e}')

    def move(self,direction):
        row=self.selected()
        if not row:return
        try:
            workspace.move_queued(row['id'],direction)
            self.refresh()
            for iid,item in self.rows.items():
                if item['id']==row['id']:
                    self.tree.selection_set(iid)
                    self.tree.focus(iid)
                    self.tree.see(iid)
                    break
        except ValueError as e:
            self.status.config(text=f'Reihenfolge konnte nicht geändert werden: {e}')

    def open_project(self):
        row=self.selected()
        if not row:
            messagebox.showinfo('PRINTBENCH','Bitte eine Datei auswählen.',parent=self);return
        path=UPLOADS/row['upload_name']
        if path.suffix.lower() not in PROJECT_EXT:
            messagebox.showinfo('PRINTBENCH',
                'Direkt im Slicer öffnen ist für 3MF und STL vorgesehen. G-Code bitte im Windows-Slicer prüfen.',
                parent=self)
            return
        if not path.is_file() or path.resolve().parent!=UPLOADS.resolve():
            messagebox.showerror('PRINTBENCH','Die Druckdatei ist nicht mehr vorhanden.',parent=self);return
        if not EXE.is_file():
            messagebox.showerror('PRINTBENCH','Die native PRINTBENCH-EXE wurde nicht gefunden. Bitte den Slicer installieren.',parent=self)
            return
        if not messagebox.askyesno('PRINTBENCH',f'Diese Datei im nativen Slicer öffnen?\n\n{path.name}\n\nDadurch wird kein Druck gestartet.',parent=self):
            return
        try:
            subprocess.Popen([str(EXE),str(path)],cwd=str(EXE.parent),close_fds=True)
            self.status.config(text=f'Datei an PRINTBENCH übergeben: {path.name}')
        except OSError as e:
            messagebox.showerror('PRINTBENCH',f'Native App konnte nicht geöffnet werden: {e}',parent=self)

    def remove_from_queue(self):
        row=self.selected()
        if not row:return
        if not messagebox.askyesno('PRINTBENCH',f'Nur den Wartelisteneintrag entfernen?\n\n{row["upload_name"]}\n\nDie hochgeladene Datei bleibt erhalten.',parent=self):
            return
        workspace.remove_queued(row['id'])
        self.refresh()

    def open_folder(self):
        UPLOADS.mkdir(parents=True,exist_ok=True)
        subprocess.Popen(['explorer.exe',str(UPLOADS)],close_fds=True)

if __name__=='__main__':
    Inbox().mainloop()
