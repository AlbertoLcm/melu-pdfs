import subprocess
import os
import sys


def _get_gs_command() -> str:
    """
    Detecta el comando correcto de Ghostscript.
    Si corre como .exe (PyInstaller), usa el binario empaquetado.
    Si corre en local, usa el del sistema (PATH).
    """
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
        
        gs_bundled_path = os.path.join(base_path, "ghostscript_bin", "gswin64c.exe")
        return gs_bundled_path
    
    return "gswin64c" if sys.platform == "win32" else "gs"

def comprimir_pdf(ruta_entrada: str, ruta_salida: str, nivel_compresion: int = 3) -> dict:
    """
    Comprime un archivo PDF utilizando Ghostscript.

    Niveles de compresión:
    0: /default   - Calidad general, tamaño moderado.
    1: /prepress  - Alta calidad (preimpresión), tamaño grande.
    2: /printer   - Alta calidad (impresora), tamaño medio.
    3: /ebook     - Calidad media (vectores y texto claros, imágenes a 150 dpi).
    4: /screen    - Baja calidad (solo pantalla, imágenes a 72 dpi). Máximo ahorro.

    Returns:
        dict con 'success', 'original_size', 'compressed_size', 'savings_pct', 'error'
    """
    perfiles = {
        0: "/default",
        1: "/prepress",
        2: "/printer",
        3: "/ebook",
        4: "/screen",
    }

    calidad = perfiles.get(nivel_compresion, "/ebook")
    gs_cmd = _get_gs_command()

    comando = [
        gs_cmd,
        "-sDEVICE=pdfwrite",
        "-dCompatibilityLevel=1.4",
        f"-dPDFSETTINGS={calidad}",
        "-dNOPAUSE",
        "-dQUIET",
        "-dBATCH",
        f"-sOutputFile={ruta_salida}",
        ruta_entrada,
    ]

    try:
        tamaño_original = os.path.getsize(ruta_entrada)
        subprocess.run(comando, check=True, capture_output=True)
        tamaño_final = os.path.getsize(ruta_salida)
        ahorro_pct = ((tamaño_original - tamaño_final) / tamaño_original) * 100

        return {
            "success": True,
            "original_size": tamaño_original,
            "compressed_size": tamaño_final,
            "savings_pct": round(ahorro_pct, 1),
            "error": None,
        }

    except subprocess.CalledProcessError as e:
        return {"success": False, "original_size": 0, "compressed_size": 0,
                "savings_pct": 0, "error": f"Error al comprimir el PDF: {e}"}
    except FileNotFoundError:
        return {"success": False, "original_size": 0, "compressed_size": 0,
                "savings_pct": 0,
                "error": "Ghostscript no está instalado o no está en el PATH del sistema."}
