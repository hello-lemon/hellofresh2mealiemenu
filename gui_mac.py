#!/usr/bin/env python3
"""
Interface graphique macOS pour hellofresh2mealiemenu
Permet de coller le magic link et lancer le script facilement
"""

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import threading

# Chemin du script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPT_PATH = os.path.join(SCRIPT_DIR, "run.sh")

class HelloFreshGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("HelloFresh → Mealie")
        self.root.geometry("600x400")
        self.root.resizable(False, False)

        # Style macOS
        style = ttk.Style()
        style.theme_use('aqua')

        # Frame principal
        main_frame = ttk.Frame(root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        # Titre
        title = ttk.Label(main_frame, text="🍳 HelloFresh → Mealie",
                         font=('Helvetica', 24, 'bold'))
        title.grid(row=0, column=0, columnspan=2, pady=(0, 20))

        # Instructions
        instructions = ttk.Label(main_frame,
                                text="Copie le lien magique depuis ton email HelloFresh :",
                                font=('Helvetica', 12))
        instructions.grid(row=1, column=0, columnspan=2, pady=(0, 10))

        # Champ pour le magic link
        ttk.Label(main_frame, text="Magic Link:", font=('Helvetica', 11, 'bold')).grid(
            row=2, column=0, sticky=tk.W, pady=(0, 5))

        self.magic_link_var = tk.StringVar()
        self.magic_link_entry = ttk.Entry(main_frame, textvariable=self.magic_link_var,
                                          width=70, font=('Helvetica', 10))
        self.magic_link_entry.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        self.magic_link_entry.focus()

        # Sélection de la semaine
        week_frame = ttk.Frame(main_frame)
        week_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))

        ttk.Label(week_frame, text="Semaine:", font=('Helvetica', 11, 'bold')).pack(side=tk.LEFT, padx=(0, 10))

        self.week_var = tk.IntVar(value=0)
        weeks = [
            ("Actuelle (cette semaine)", 0),
            ("Prochaine (semaine suivante)", 1),
            ("Dans 2 semaines", 2),
        ]

        for text, value in weeks:
            ttk.Radiobutton(week_frame, text=text, variable=self.week_var,
                           value=value).pack(anchor=tk.W, pady=2)

        # Bouton de lancement
        self.run_button = ttk.Button(main_frame, text="▶️  Lancer le script",
                                     command=self.run_script)
        self.run_button.grid(row=5, column=0, columnspan=2, pady=(10, 10))

        # Zone de log
        ttk.Label(main_frame, text="Logs:", font=('Helvetica', 11, 'bold')).grid(
            row=6, column=0, sticky=tk.W, pady=(10, 5))

        log_frame = ttk.Frame(main_frame)
        log_frame.grid(row=7, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))

        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.log_text = tk.Text(log_frame, height=8, width=70,
                               font=('Monaco', 9),
                               yscrollcommand=scrollbar.set,
                               bg='#1e1e1e', fg='#d4d4d4')
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.log_text.yview)

        # Configurer le grid
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(7, weight=1)

    def log(self, message):
        """Ajouter un message au log"""
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)
        self.log_text.update()

    def run_script(self):
        """Lancer le script run.sh avec le magic link"""
        magic_link = self.magic_link_var.get().strip()

        if not magic_link:
            messagebox.showerror("Erreur", "Veuillez coller le magic link HelloFresh")
            return

        if not magic_link.startswith("https://click.bnlx.hellofresh.link/"):
            result = messagebox.askyesno("Avertissement",
                                        "Le lien ne ressemble pas à un magic link HelloFresh.\n\n"
                                        "Continuer quand même ?")
            if not result:
                return

        # Désactiver le bouton pendant l'exécution
        self.run_button.config(state='disabled', text="⏳ En cours...")
        self.log_text.delete(1.0, tk.END)

        # Lancer dans un thread séparé
        week = self.week_var.get()
        thread = threading.Thread(target=self._run_script_thread, args=(magic_link, week))
        thread.daemon = True
        thread.start()

    def _run_script_thread(self, magic_link, week):
        """Exécuter le script dans un thread séparé"""
        try:
            self.log(f"🚀 Lancement du script...\n")
            self.log(f"📅 Semaine: {week} (0=actuelle, 1=prochaine, etc.)\n")

            # Construire la commande
            cmd = [SCRIPT_PATH, "-m", magic_link, "-w", str(week)]

            # Lancer le processus
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                cwd=SCRIPT_DIR
            )

            # Lire la sortie en temps réel
            for line in process.stdout:
                self.log(line.rstrip())

            # Attendre la fin
            return_code = process.wait()

            if return_code == 0:
                self.log("\n✅ Script terminé avec succès !")
                self.root.after(0, lambda: messagebox.showinfo("Succès",
                    "Le meal plan a été créé dans Mealie ! 🎉"))
            else:
                self.log(f"\n❌ Le script a échoué avec le code {return_code}")
                self.root.after(0, lambda: messagebox.showerror("Erreur",
                    f"Le script a échoué. Vérifiez les logs."))

        except Exception as e:
            self.log(f"\n❌ Erreur: {str(e)}")
            self.root.after(0, lambda: messagebox.showerror("Erreur", str(e)))

        finally:
            # Réactiver le bouton
            self.root.after(0, lambda: self.run_button.config(state='normal', text="▶️  Lancer le script"))

def main():
    root = tk.Tk()
    app = HelloFreshGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()
