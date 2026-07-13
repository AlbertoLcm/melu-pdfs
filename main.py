import socket
import threading
import time
import webbrowser

from app.server import app


def _find_free_port(start: int = 5000, end: int = 5100) -> int:
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("", port))
                return port
            except OSError:
                continue
    raise OSError(f"No hay puertos libres entre {start} y {end}.")


if __name__ == "__main__":
    port = _find_free_port()
    url = f"http://localhost:{port}"

    def _open_browser():
        time.sleep(1)
        webbrowser.open(url)

    threading.Thread(target=_open_browser, daemon=True).start()

    print("\nPDF Compressor — Servidor iniciado")
    print(f"Abriendo navegador en: {url}\n")
    app.run(debug=False, host="0.0.0.0", port=port)