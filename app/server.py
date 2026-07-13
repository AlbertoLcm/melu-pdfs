import os
import uuid
import tempfile
import threading
import time
from pathlib import Path
from flask import Flask, request, jsonify, render_template, send_file, abort

from app.compression import comprimir_pdf

app = Flask(__name__, template_folder="templates")

app.config["MAX_CONTENT_LENGTH"] = 400 * 1024 * 1024  # 400 MB máximo

_file_registry: dict[str, Path] = {}
_registry_lock = threading.Lock()


# ─────────────────────────── Limpieza automática ────────────────────────────

def _cleanup_file(token: str, delay_seconds: int = 600):
    """Elimina el archivo temporal comprimido después del tiempo indicado."""
    def _do_cleanup():
        time.sleep(delay_seconds)
        with _registry_lock:
            path = _file_registry.pop(token, None)
        if path and path.exists():
            path.unlink(missing_ok=True)

    threading.Thread(target=_do_cleanup, daemon=True).start()


# ─────────────────────────── Utilidades ─────────────────────────────────────

def _format_size(bytes_val: int) -> str:
    """Formatea bytes a una cadena legible (KB / MB)."""
    if bytes_val < 1024:
        return f"{bytes_val} B"
    if bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    return f"{bytes_val / (1024 * 1024):.2f} MB"


# ─────────────────────────── Rutas Flask ────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/compress", methods=["POST"])
def compress():
    if "pdf" not in request.files:
        return jsonify({"success": False, "error": "No se recibió ningún archivo."}), 400

    file = request.files["pdf"]
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        return jsonify({"success": False, "error": "El archivo debe ser un PDF válido."}), 400

    # Nivel de compresión (0-4)
    try:
        nivel = int(request.form.get("level", 3))
        if nivel not in range(5):
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Nivel de compresión inválido (0-4)."}), 400

    token = str(uuid.uuid4())
    original_stem = Path(file.filename).stem

    input_fd, input_path = tempfile.mkstemp(suffix="_input.pdf")
    output_fd, output_path = tempfile.mkstemp(suffix="_output.pdf")
    os.close(input_fd)
    os.close(output_fd)

    try:
        file.save(input_path)

        resultado = comprimir_pdf(input_path, output_path, nivel)

        if not resultado["success"]:
            return jsonify({"success": False, "error": resultado["error"]}), 500

        with _registry_lock:
            _file_registry[token] = Path(output_path)
        _cleanup_file(token)

        return jsonify({
            "success": True,
            "token": token,
            "original_name": original_stem,
            "original_size": resultado["original_size"],
            "compressed_size": resultado["compressed_size"],
            "savings_pct": resultado["savings_pct"],
            "original_size_str": _format_size(resultado["original_size"]),
            "compressed_size_str": _format_size(resultado["compressed_size"]),
        })

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

    finally:
        if os.path.exists(input_path):
            os.unlink(input_path)


@app.route("/download/<token>")
def download(token: str):
    with _registry_lock:
        path = _file_registry.get(token)

    if not path or not path.exists():
        abort(404)

    original_name = request.args.get("name", "archivo")
    download_name = f"comprimido_{original_name}.pdf"

    return send_file(
        str(path),
        as_attachment=True,
        download_name=download_name,
        mimetype="application/pdf",
    )
