from pathlib import Path
from datetime import datetime
import os
import re
import xml.etree.ElementTree as ET


# Formato observado en los archivos de ejemplo:
# PL_25566_EXP_ES_202420260825.131323BPG1305233A4.xml
#
# La fecha que debe aparecer en el nombre es YYYYMMDD y proviene de
# fechaYHoraCorte del elemento raíz.
DATE_PATTERN = re.compile(
    r"^(?P<prefix>PL_\d+_EXP_ES_2024)(?P<date>\d{8})(?P<suffix>\..+)$",
    re.IGNORECASE,
)


def read_cutoff_date(xml_path: Path) -> str:
    """Lee fechaYHoraCorte del elemento raíz y devuelve YYYYMMDD."""
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as exc:
        raise ValueError(f"XML inválido: {exc}") from exc

    value = root.attrib.get("fechaYHoraCorte")
    if not value:
        raise ValueError("No se encontró el atributo fechaYHoraCorte.")

    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"fechaYHoraCorte no tiene un formato de fecha válido: {value}"
        ) from exc

    return dt.strftime("%Y%m%d")


def build_new_name(filename: str, date_yyyymmdd: str) -> str:
    """Reemplaza únicamente la fecha de 8 dígitos del nombre observado."""
    match = DATE_PATTERN.match(filename)
    if not match:
        raise ValueError(
            "El nombre no coincide con el formato esperado: "
            "PL_25566_EXP_ES_2024YYYYMMDD....xml"
        )

    return f"{match.group('prefix')}{date_yyyymmdd}{match.group('suffix')}"


def plan_renames(folder: Path):
    """Analiza todos los XML de una carpeta sin modificar nada."""
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError("La carpeta seleccionada no existe.")

    results = []

    for xml_path in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
        if not xml_path.is_file() or xml_path.suffix.lower() != ".xml":
            continue

        try:
            date = read_cutoff_date(xml_path)
            new_name = build_new_name(xml_path.name, date)
            status = "Listo"
        except ValueError as exc:
            date = "-"
            new_name = xml_path.name
            status = f"Error: {exc}"

        results.append({
            "old_name": xml_path.name,
            "date": date,
            "new_name": new_name,
            "status": status,
        })

    return results


def execute_renames(folder: Path, changes):
    """Ejecuta los cambios usando una fase temporal para evitar colisiones."""
    folder = Path(folder)

    # Solo usamos cambios reales.
    changes = [
        x for x in changes
        if x["old_name"] != x["new_name"] and x["status"] == "Listo"
    ]

    if not changes:
        return

    # Primero movemos a nombres temporales únicos.
    temp_moves = []
    try:
        for index, item in enumerate(changes):
            old_path = folder / item["old_name"]
            if not old_path.exists():
                raise FileNotFoundError(f"No existe: {item['old_name']}")

            temp_path = folder / f".xmlrenamer_tmp_{index}_{old_path.name}"
            while temp_path.exists():
                index += 1
                temp_path = folder / f".xmlrenamer_tmp_{index}_{old_path.name}"

            os.replace(old_path, temp_path)
            temp_moves.append((temp_path, folder / item["new_name"]))

        # Finalmente aplicamos los nombres definitivos.
        for temp_path, new_path in temp_moves:
            if new_path.exists():
                raise FileExistsError(
                    f"Ya existe un archivo con el nombre destino: {new_path.name}"
                )
            os.replace(temp_path, new_path)

    except Exception:
        # Intentar restaurar cualquier archivo que siga con nombre temporal.
        for temp_path, original_or_new_path in reversed(temp_moves):
            if temp_path.exists():
                # Recuperamos el nombre original a partir del listado de cambios.
                for item in changes:
                    if folder / item["new_name"] == original_or_new_path:
                        original_path = folder / item["old_name"]
                        if not original_path.exists():
                            os.replace(temp_path, original_path)
                        break
        raise
