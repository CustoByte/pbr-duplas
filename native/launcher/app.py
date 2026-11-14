"""Windows desktop launcher. Run with Python 3.11+ (Tk included on Windows)."""
from pathlib import Path
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import webbrowser
import core

BG, PANEL, TEXT, MUTED, ACCENT = '#0a101c', '#141e30', '#eef4ff', '#9badc9', '#58dbc2'
HOME = Path(__file__).resolve().parents[1] / 'user-data'


class Launcher:
    def __init__(self, root):
        self.root, self.events, self.busy, self.feed = root, queue.Queue(), False, None
        root.title('PBR Native • Launcher')
        root.geometry('1000x680')
        root.minsize(850, 620)
        root.configure(bg=BG)
        root.option_add('*Font', ('Segoe UI', 11))
        style = ttk.Style(root)
        style.theme_use('clam')
        style.configure('TProgressbar', background=ACCENT, troughcolor=PANEL, borderwidth=0)
        shell = tk.Frame(root, bg=BG)
        shell.pack(fill='both', expand=True, padx=34, pady=26)
        self.label(shell, 'PBR  /  NATIVE', 12, ACCENT).pack(anchor='w')
        self.label(shell, 'Uma nova base para batalhar.', 29).pack(anchor='w', pady=(15, 6))
        self.label(shell, 'Windows  •  Canal experimental  •  Atualizações pelo GitHub', 11, MUTED).pack(anchor='w')
        hero = tk.Frame(shell, bg=PANEL, padx=24, pady=22)
        hero.pack(fill='x', pady=24)
        self.label(hero, 'PROJETO EM DESENVOLVIMENTO', 10, ACCENT, PANEL).pack(anchor='w')
        self.label(hero, 'O próximo passo é o motor nativo.', 20, bg=PANEL).pack(anchor='w', pady=(8, 10))
        self.label(hero, 'O launcher já prepara sua biblioteca. Ainda não executa batalhas sem Dolphin.',
                   11, MUTED, PANEL).pack(anchor='w')
        self.play = self.button(hero, 'Jogar versão nativa', self.launch, primary=True)
        self.play.pack(anchor='w', pady=(18, 0))
        self.play.config(state='disabled')
        card = tk.Frame(shell, bg=PANEL, padx=20, pady=18)
        card.pack(fill='x')
        self.label(card, 'SUA IMAGEM DO JOGO', 10, ACCENT, PANEL).pack(anchor='w')
        self.source = self.label(card, 'Nenhuma imagem selecionada', 12, bg=PANEL)
        self.source.pack(anchor='w', pady=(8, 3))
        self.detail = self.label(card, 'Pode escolher sua ISO/RVZ com as modificações.', 10, MUTED, PANEL)
        self.detail.pack(anchor='w')
        self.pick = self.button(card, 'Selecionar imagem modificada', self.select)
        self.pick.pack(anchor='w', pady=(12, 0))
        actions = tk.Frame(shell, bg=BG)
        actions.pack(fill='x', pady=(18, 8))
        self.check = self.button(actions, 'Verificar atualizações', self.check_updates)
        self.check.pack(side='left')
        self.install = self.button(actions, 'Instalar atualização', self.install_update)
        self.install.pack(side='left', padx=10)
        self.install.config(state='disabled')
        self.revert = self.button(actions, 'Restaurar versão', self.revert_version)
        self.revert.pack(side='left')
        self.button(actions, 'GitHub ↗', lambda: webbrowser.open('https://github.com/CustoByte/pbr-duplas')).pack(side='right')
        self.bar = ttk.Progressbar(shell, mode='determinate')
        self.bar.pack(fill='x', pady=(10, 8))
        self.status = self.label(shell, 'Pronto para selecionar sua imagem. O arquivo original será apenas lido.', 10, MUTED)
        self.status.pack(anchor='w')
        self.refresh()
        root.after(80, self.poll)

    def label(self, parent, text, size, color=TEXT, bg=BG):
        return tk.Label(parent, text=text, bg=bg, fg=color, font=('Segoe UI', size), anchor='w', wraplength=890, justify='left')

    def button(self, parent, text, action, primary=False):
        return tk.Button(parent, text=text, command=action, bg=ACCENT if primary else '#24334c',
                         fg=BG if primary else TEXT, activebackground='#80edda', activeforeground=BG,
                         relief='flat', bd=0, padx=15, pady=10, cursor='hand2', disabledforeground='#718199')

    def refresh(self):
        try:
            source = core.load_json(HOME / 'source.json')
            if source:
                self.source.config(text=Path(source['path']).name)
                self.detail.config(text=f"{source['format']} • {source['bytes'] / 1024**3:.2f} GiB • Registrada; arquivos ainda não extraídos")
            executable = core.runtime_path(HOME)
            self.play.config(state='normal' if executable and not self.busy else 'disabled')
        except Exception as error:
            self.status.config(text=str(error))

    def run(self, operation, on_done):
        if self.busy:
            return
        self.busy = True
        for button in (self.pick, self.check, self.install, self.play, self.revert):
            button.config(state='disabled')
        self.status.config(text='Processando…')
        def worker():
            try:
                self.events.put(('done', on_done, operation()))
            except Exception as error:
                self.events.put(('error', str(error)))
        threading.Thread(target=worker, daemon=True).start()

    def progress(self, done, total):
        self.events.put(('progress', done, total))

    def poll(self):
        try:
            while True:
                event = self.events.get_nowait()
                if event[0] == 'progress':
                    _, done, total = event
                    self.bar.config(value=done / total * 100 if total else 0)
                    self.status.config(text=f"Lendo {done / 1024**2:.0f} MiB…")
                else:
                    self.busy = False
                    for button in (self.pick, self.check, self.revert):
                        button.config(state='normal')
                    self.install.config(state='normal' if self.feed and self.feed.get('runtime_available') else 'disabled')
                    if event[0] == 'error':
                        self.status.config(text=event[1])
                        messagebox.showerror('PBR Native', event[1], parent=self.root)
                    else:
                        event[1](event[2])
                    self.refresh()
        except queue.Empty:
            pass
        self.root.after(80, self.poll)

    def select(self):
        path = filedialog.askopenfilename(parent=self.root, title='Escolha seu Battle Revolution modificado',
                                          filetypes=[('Imagem do jogo', '*.iso *.rvz')])
        if path:
            self.run(lambda: core.register_image(Path(path), HOME, self.progress),
                     lambda result: self.status.config(text='Imagem registrada. O arquivo foi preservado; o motor nativo ainda está em desenvolvimento.'))

    def check_updates(self):
        def finished(feed):
            self.feed = feed
            available = feed.get('runtime_available', False)
            self.install.config(state='normal' if available else 'disabled')
            self.status.config(text=f"Versão disponível: {feed['version']}" if available else feed.get('message', 'Nenhum motor nativo publicado.'))
        self.run(core.fetch_feed, finished)

    def install_update(self):
        if self.feed:
            self.run(lambda: core.install_runtime(HOME, self.feed, self.progress),
                     lambda receipt: self.status.config(text=f"Instalada: {receipt['version']}"))

    def revert_version(self):
        self.run(lambda: core.rollback(HOME), lambda receipt: self.status.config(text=f"Restaurada: {receipt['version']}"))

    def launch(self):
        try:
            executable = core.runtime_path(HOME)
            if executable:
                subprocess.Popen([str(executable), '--data-dir', str(HOME)], cwd=executable.parent)
        except Exception as error:
            messagebox.showerror('PBR Native', str(error), parent=self.root)


if __name__ == '__main__':
    Launcher(tk.Tk()).root.mainloop()
