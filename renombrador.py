from pathlib import Path
from datetime import datetime
import os
import re
import xml.etree.ElementTree as ET


# Formato observado en los archivos de ejemplo (puede variar el separador
# antes del folio final, y el año dentro del número de permiso):
#   PL_25566_EXP_ES_202420260825.131323BPG1305233A4.xml
#   PL_9065_EXP_ES_201520260826_131156BPG1305233A4.xml
#
# La fecha que debe aparecer en el nombre es YYYYMMDD y proviene del
# atributo fechaYHoraCorte del elemento raíz. El resto del nombre (prefijo,
# separador, folio final, extensión) nunca se toca: solo se reemplazan los
# 8 dígitos de la fecha.

# Respaldo genérico: ya no asume un año fijo (antes decía "2024" literal,
# por eso fallaban permisos de otros años como 2015). Ahora acepta
# cualquier año de 4 dígitos como parte del número de permiso.
GENERIC_DATE_PATTERN = re.compile(
    r"^(?P<prefix>PL_\d+_EXP_ES_\d{4})(?P<date>\d{8})(?P<suffix>.+)$",
    re.IGNORECASE,
)

# Último respaldo: un bloque de 8 dígitos "aislado" (no pegado a más
# dígitos por ningún lado), en caso de que el nombre no siga ni siquiera
# el formato genérico anterior.
ISOLATED_8DIGIT_PATTERN = re.compile(r"(?<!\d)\d{8}(?!\d)")


class RenameError(ValueError):
    """Error de negocio al planear un renombrado (no es un bug, es un dato inválido)."""


def read_xml_info(xml_path: Path) -> dict:
    """Lee del elemento raíz: fechaYHoraCorte (-> YYYYMMDD) y numeroPermisoCRE."""
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError as exc:
        raise RenameError(f"XML inválido: {exc}") from exc

    value = root.attrib.get("fechaYHoraCorte")
    if not value:
        raise RenameError("No se encontró el atributo fechaYHoraCorte.")

    try:
        dt = datetime.fromisoformat(value)
    except ValueError as exc:
        raise RenameError(
            f"fechaYHoraCorte no tiene un formato de fecha válido: {value}"
        ) from exc

    return {
        "date": dt.strftime("%Y%m%d"),
        "numero_permiso": root.attrib.get("numeroPermisoCRE"),
    }


def read_cutoff_date(xml_path: Path) -> str:
    """Compatibilidad hacia atrás: solo la fecha."""
    return read_xml_info(xml_path)["date"]


def _replace_using_numero_permiso(filename: str, numero_permiso: str, date_yyyymmdd: str):
    """Ubica la fecha en el nombre usando el numeroPermisoCRE del propio XML
    como ancla (p.ej. 'PL/9065/EXP/ES/2015' -> 'PL_9065_EXP_ES_2015'), y
    reemplaza solo los 8 dígitos que le siguen. No modifica nada más del
    nombre, sin importar el separador o folio que venga después.
    Devuelve None si no se puede ubicar de esta forma.
    """
    if not numero_permiso:
        return None

    anchor = numero_permiso.replace("/", "_")
    lower_name = filename.lower()
    lower_anchor = anchor.lower()

    idx = lower_name.find(lower_anchor)
    if idx == -1:
        return None

    date_start = idx + len(anchor)
    date_end = date_start + 8
    candidate = filename[date_start:date_end]
    if not (len(candidate) == 8 and candidate.isdigit()):
        return None

    return filename[:date_start] + date_yyyymmdd + filename[date_end:]


def _replace_using_generic_pattern(filename: str, date_yyyymmdd: str):
    match = GENERIC_DATE_PATTERN.match(filename)
    if not match:
        return None
    return (
        filename[: match.start("date")]
        + date_yyyymmdd
        + filename[match.end("date") :]
    )


def _replace_using_isolated_block(filename: str, date_yyyymmdd: str):
    matches = list(ISOLATED_8DIGIT_PATTERN.finditer(filename))
    if len(matches) != 1:
        # 0 o más de 1 candidato: es ambiguo o no existe, mejor no adivinar.
        return None
    match = matches[0]
    return filename[: match.start()] + date_yyyymmdd + filename[match.end() :]


def build_new_name(filename: str, date_yyyymmdd: str, numero_permiso: str = None) -> str:
    """Reemplaza únicamente la fecha de 8 dígitos del nombre, probando
    varias estrategias de la más precisa a la más general."""

    for strategy in (
        lambda: _replace_using_numero_permiso(filename, numero_permiso, date_yyyymmdd),
        lambda: _replace_using_generic_pattern(filename, date_yyyymmdd),
        lambda: _replace_using_isolated_block(filename, date_yyyymmdd),
    ):
        result = strategy()
        if result is not None:
            return result

    raise RenameError(
        "No se pudo identificar de forma confiable la fecha dentro del nombre "
        "del archivo. Revísalo manualmente."
    )


def plan_renames(folder: Path):
    """Analiza los XML directamente dentro de una carpeta (sin subcarpetas)."""
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError("La carpeta seleccionada no existe.")

    results = []

    for xml_path in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
        if not xml_path.is_file() or xml_path.suffix.lower() != ".xml":
            continue

        try:
            info = read_xml_info(xml_path)
            new_name = build_new_name(
                xml_path.name, info["date"], info["numero_permiso"]
            )
            date = info["date"]
            status = "Listo"
        except RenameError as exc:
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


def find_folders_with_xml(root_folder: Path):
    """Recorre root_folder y todas sus subcarpetas, devolviendo (ordenadas)
    las que contienen al menos un .xml directamente dentro de ellas."""
    root_folder = Path(root_folder)
    folders = []
    for dirpath, _dirnames, filenames in os.walk(root_folder):
        if any(name.lower().endswith(".xml") for name in filenames):
            folders.append(Path(dirpath))
    return sorted(folders, key=lambda p: str(p).lower())


def plan_renames_tree(root_folder: Path):
    """Como plan_renames, pero recursivo: analiza la carpeta seleccionada y
    todas sus subcarpetas. Devuelve una lista de grupos:
        [{"folder": Path, "items": [...]}, ...]
    Cada grupo corresponde a una carpeta (con al menos un XML dentro)."""
    root_folder = Path(root_folder)
    if not root_folder.is_dir():
        raise ValueError("La carpeta seleccionada no existe.")

    tree = []
    for folder in find_folders_with_xml(root_folder):
        tree.append({"folder": folder, "items": plan_renames(folder)})
    return tree


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