import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from renombrador import plan_renames_tree, execute_renames


class XMLRenamerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Renombrador de XML")
        self.root.geometry("950x600")
        self.root.minsize(760, 480)

        self.root_folder = None
        self.tree_data = []  # [{"folder": Path, "items": [...]}, ...]

        frame = ttk.Frame(root, padding=20)
        frame.pack(fill="both", expand=True)

        ttk.Label(
            frame, text="Renombrador de XML",
            font=("Arial", 20, "bold")
        ).pack(anchor="w")

        ttk.Label(
            frame,
            text="Selecciona una carpeta principal. Puede contener los XML directamente, "
                 "o varias subcarpetas con XML dentro: se revisan todas. El programa lee "
                 "fechaYHoraCorte de cada XML y corrige solo la fecha dentro del nombre.",
            wraplength=880
        ).pack(anchor="w", pady=(8, 18))

        buttons = ttk.Frame(frame)
        buttons.pack(fill="x")

        ttk.Button(
            buttons, text="Seleccionar carpeta principal", command=self.select_folder
        ).pack(side="left")

        self.rename_button = ttk.Button(
            buttons, text="Renombrar archivos", command=self.rename_files,
            state="disabled"
        )
        self.rename_button.pack(side="left", padx=10)

        self.status = ttk.Label(frame, text="Ninguna carpeta seleccionada.")
        self.status.pack(anchor="w", pady=12)

        columns = ("fecha", "nuevo", "estado")
        self.tree = ttk.Treeview(frame, columns=columns, show="tree headings")
        self.tree.heading("#0", text="Carpeta / Archivo")
        self.tree.heading("fecha", text="Fecha encontrada")
        self.tree.heading("nuevo", text="Nuevo nombre")
        self.tree.heading("estado", text="Estado")

        self.tree.column("#0", width=320)
        self.tree.column("fecha", width=120)
        self.tree.column("nuevo", width=320)
        self.tree.column("estado", width=140)

        self.tree.tag_configure("folder", font=("Arial", 10, "bold"))
        self.tree.tag_configure("error", foreground="#b00020")
        self.tree.tag_configure("nochange", foreground="#888888")

        scrollbar = ttk.Scrollbar(frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def select_folder(self):
        folder = filedialog.askdirectory(
            title="Selecciona la carpeta principal (puede tener subcarpetas)"
        )
        if not folder:
            return

        self.root_folder = Path(folder)
        self.refresh_preview()

    def _folder_label(self, folder: Path) -> str:
        try:
            rel = folder.relative_to(self.root_folder)
        except ValueError:
            return str(folder)
        return str(rel) if str(rel) != "." else f"{folder.name}  (carpeta principal)"

    def refresh_preview(self):
        self.tree.delete(*self.tree.get_children())

        try:
            self.tree_data = plan_renames_tree(self.root_folder)
        except Exception as exc:
            messagebox.showerror("Error", str(exc))
            self.tree_data = []
            return

        if not self.tree_data:
            self.status.config(text="No se encontraron archivos .xml en esta carpeta ni en sus subcarpetas.")
            self.rename_button.config(state="disabled")
            return

        total_files = 0
        total_changes = 0
        total_errors = 0

        for group in self.tree_data:
            items = group["items"]
            label = self._folder_label(group["folder"])

            folder_changes = sum(
                1 for it in items if it["status"] == "Listo" and it["old_name"] != it["new_name"]
            )
            folder_errors = sum(1 for it in items if it["status"] != "Listo")

            folder_id = self.tree.insert(
                "", "end",
                text=f"\U0001F4C1 {label}  —  {len(items)} archivo(s), {folder_changes} cambio(s), {folder_errors} error(es)",
                open=True,
                tags=("folder",),
            )

            for item in items:
                if item["status"] != "Listo":
                    tag = "error"
                elif item["old_name"] == item["new_name"]:
                    tag = "nochange"
                else:
                    tag = ""

                self.tree.insert(
                    folder_id, "end",
                    text=item["old_name"],
                    values=(item["date"], item["new_name"], item["status"]),
                    tags=(tag,) if tag else (),
                )

            total_files += len(items)
            total_changes += folder_changes
            total_errors += folder_errors

        self.status.config(
            text=(
                f"{len(self.tree_data)} carpeta(s) con XML  |  {total_files} archivo(s)  |  "
                f"{total_changes} necesitan cambio  |  {total_errors} con error"
            )
        )
        self.rename_button.config(state="normal" if total_changes else "disabled")

    def rename_files(self):
        if not self.tree_data:
            return

        total_planned = sum(
            1 for g in self.tree_data for it in g["items"]
            if it["status"] == "Listo" and it["old_name"] != it["new_name"]
        )

        if not total_planned:
            messagebox.showinfo("Sin cambios", "No hay archivos para renombrar.")
            return

        folders_with_changes = sum(
            1 for g in self.tree_data
            if any(it["status"] == "Listo" and it["old_name"] != it["new_name"] for it in g["items"])
        )

        ok = messagebox.askyesno(
            "Confirmar",
            f"Se renombrarán {total_planned} archivo(s) en {folders_with_changes} carpeta(s).\n\n"
            "El contenido de los XML no será modificado.\n"
            "Los archivos marcados como error se dejarán sin tocar.\n\n"
            "¿Continuar?"
        )
        if not ok:
            return

        renamed = 0
        failed_folders = []

        for group in self.tree_data:
            changes = [
                it for it in group["items"]
                if it["status"] == "Listo" and it["old_name"] != it["new_name"]
            ]
            if not changes:
                continue
            try:
                execute_renames(group["folder"], changes)
                renamed += len(changes)
            except Exception as exc:
                failed_folders.append((self._folder_label(group["folder"]), str(exc)))

        self.refresh_preview()

        if failed_folders:
            details = "\n".join(f"- {label}: {err}" for label, err in failed_folders)
            messagebox.showwarning(
                "Terminado con errores",
                f"Se renombraron {renamed} archivo(s).\n\nHubo problemas en:\n{details}"
            )
        else:
            messagebox.showinfo("Listo", f"Se renombraron {renamed} archivo(s) en total.")


if __name__ == "__main__":
    root = tk.Tk()
    XMLRenamerApp(root)
    root.mainloop()