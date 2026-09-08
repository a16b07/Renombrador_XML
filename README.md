# Renombrador XML

Aplicación ligera para Windows y macOS que analiza archivos XML de controles volumétricos y corrige la fecha del nombre usando el atributo `fechaYHoraCorte`.

## Qué hace

Ejemplo:

`PL_25566_EXP_ES_202420260826.131323BPG1305233A4.xml`

Dentro del XML:

`fechaYHoraCorte="2026-08-25T23:59:59"`

Resultado:

`PL_25566_EXP_ES_202420260825.131323BPG1305233A4.xml`

**Importante:** el programa solamente cambia el nombre del archivo. No modifica el contenido del XML.

## Requisitos

Python 3.10+.

No necesita paquetes externos. La interfaz usa Tkinter y el análisis usa la librería XML incluida con Python.

## Ejecutar en Windows/macOS

Desde esta carpeta:

```bash
python app.py
```

En algunos equipos:

```bash
python3 app.py
```

## Probar

```bash
python tests/test_renombrador.py
```

Debe aparecer:

```text
Todos los tests pasaron.
```

## Cómo usar la aplicación

1. Abre `app.py`.
2. Pulsa **Seleccionar carpeta**.
3. Elige la carpeta que contiene los XML.
4. Revisa la tabla.
5. Pulsa **Renombrar archivos**.
6. Confirma.

La aplicación primero muestra una vista previa y no hace cambios hasta que se confirma.

## Crear una aplicación para distribuir

### Windows

Instala PyInstaller:

```bash
pip install pyinstaller
```

Después:

```bash
pyinstaller --onefile --windowed --name RenombradorXML app.py
```

El ejecutable estará en:

`dist/RenombradorXML.exe`

### macOS

En una Mac, instala PyInstaller:

```bash
python3 -m pip install pyinstaller
```

Después:

```bash
pyinstaller --windowed --name RenombradorXML app.py
```

Se generará una aplicación dentro de:

`dist/RenombradorXML.app`

> Para generar una aplicación macOS, lo más recomendable es ejecutar PyInstaller directamente en una Mac.

## Nota sobre el formato

El código está basado en los dos XML proporcionados como ejemplo. Ambos contienen `fechaYHoraCorte="2026-08-25T23:59:59"`; uno tiene `20260826` en el nombre y el otro `20260825`. Por eso la lógica toma la fecha de `fechaYHoraCorte` y reemplaza únicamente esos 8 dígitos del nombre.
