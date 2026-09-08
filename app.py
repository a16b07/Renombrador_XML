import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from renombrador import plan_renames, execute_renames


class XMLRenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Renombrador de XML")
        self.root.geometry("850x560")
        self.root.minsize(720, 480)

        self.folder = None
        self.plan = []

        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame, text="Renombrador de XML",
            font=("Arial", 20, "bold")
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text="Selecciona una carpeta. El programa leerá fechaYHoraCorte de cada XML "
                 "y corregirá la fecha dentro del nombre del archivo.",
            wraplength=780
        ).pack(anchor="w", pady=(8, 18))

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")

        ttk.Button(
            buttons, text="Seleccionar carpeta", command=self.select_folder
        ).pack(side="left")

        self.rename_button = ttk.Button(
            buttons, text="Renombrar archivos", command=self.rename_files,
            state="disabled"
        )
        self.rename_button.pack(side="left", padx=10)

        self.status = ttk.Label(frame, text="Ninguna carpeta seleccionada.")
        self.status.pack(anchor="w", pady=12)

        columns = ("actual", "fecha", "nuevo", "estado")
        self.tree = ttk.Treeview(frame, columns=columns, show="headings")
        self.tree.heading("actual", text="Nombre actual")
        self.tree.heading("fecha", text="Fecha encontrada")
        self.tree.heading("nuevo", text="Nuevo nombre")
        self.tree.heading("estado", text="Estado")

        self.tree.column("actual", width=250)
        self.tree.column("fecha", width=130)
        self.tree.column("nuevo", width=300)
        self.tree.column("estado", width=100)

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def select_folder(self):
        folder = filedialog.askdirectory(title="Selecciona la carpeta con los XML")
        if not folder:
            return

        self.folder = Path(folder)
        self.refresh_preview()

    def refresh_preview(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

        try:
            self.plan = plan_renames(self.folder)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self.plan = []
            return

        changes = 0
        errors = 0

        for item in self.plan:
            self.tree.insert(
                "", "end",
                values=(item["old_name"], item["date"], item["new_name"], item["status"])
            )
            if item["status"] == "Listo":
                if item["old_name"] != item["new_name"]:
                    changes += 1
            else:
                errors += 1

        self.status.config(
            text=f"{len(self.plan)} XML encontrados | {changes} necesitan cambio | {errors} con error"
        )
        self.rename_button.config(
            state="normal" if changes and not errors else "disabled"
        )

    def rename_files(self):
        if not self.folder or not self.plan:
            return

        changes = [
            x for x in self.plan
            if x["status"] == "Listo" and x["old_name"] != x["new_name"]
        ]

        if not changes:
            messagebox.showinfo("Sin cambios", "Todos los nombres ya son correctos.")
            return

        ok = messagebox.askyesno(
            "Confirmar",
            f"Se renombrarán {len(changes)} archivo(s).\n\n"
            "El contenido de los XML no será modificado.\n\n"
            "¿Continuar?"
        )
        if not ok:
            return

        try:
            execute_renames(self.folder, changes)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self.refresh_preview()
            return

        self.refresh_preview()
        messagebox.showinfo("Listo", f"Se renombraron {len(changes)} archivo(s).")


if __name__ == "__main__":
    root = tk.Tk()
    XMLRenamerApp(root)
    root.mainloop()
