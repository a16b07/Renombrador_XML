import tempfile
from pathlib import Path
from renombrador import read_cutoff_date, build_new_name, plan_renames

SAMPLE_XML = """<?xml version="1.0" encoding="utf-8"?>
<controlesvolumetricos:ControlesVolumetricos
    xmlns:controlesvolumetricos="http://www.sat.gob.mx/esquemas/controlesvolumetricos"
    version="1.2"
    fechaYHoraCorte="2026-08-25T23:59:59">
</controlesvolumetricos:ControlesVolumetricos>
"""

def test_date():
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "test.xml"
        p.write_text(SAMPLE_XML, encoding="utf-8")
        assert read_cutoff_date(p) == "20260825"

def test_name():
    old = "PL_25566_EXP_ES_202420260826.131323BPG1305233A4.xml"
    new = build_new_name(old, "20260825")
    assert new == "PL_25566_EXP_ES_202420260825.131323BPG1305233A4.xml"

def test_plan():
    with tempfile.TemporaryDirectory() as tmp:
        folder = Path(tmp)
        p = folder / "PL_25566_EXP_ES_202420260826.131323BPG1305233A4.xml"
        p.write_text(SAMPLE_XML, encoding="utf-8")
        result = plan_renames(folder)
        assert result[0]["new_name"] == "PL_25566_EXP_ES_202420260825.131323BPG1305233A4.xml"

if __name__ == "__main__":
    test_date()
    test_name()
    test_plan()
    print("Todos los tests pasaron.")
