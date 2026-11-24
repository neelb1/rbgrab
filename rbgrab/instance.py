"""Single instance: a second launch asks the running app to show its search bar."""
import socket
import threading

PORT = 47913


def signal_running() -> bool:
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.3) as s:
            s.sendall(b"show")
        return True
    except OSError:
        return False


def serve(on_show):
    try:
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", PORT))
        server.listen(2)
    except OSError:
        return  # port taken by something else: run without single-instance

    def loop():
        while True:
            conn, _ = server.accept()
            with conn:
                conn.settimeout(1)
                try:
                    if conn.recv(16) == b"show":
                        on_show()
                except OSError:
                    pass

    threading.Thread(target=loop, daemon=True, name="instance").start()
