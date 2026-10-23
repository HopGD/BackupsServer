#!/usr/bin/env python3
"""
Herramienta de Backup Remoto por SSH con Interfaz Gráfica Tkinter.
Copia un directorio o disco duro externo montado en el servidor hacia su disco interno
mostrando porcentaje real, velocidad y tiempo restante estimado (ETA).
"""

import os
import sys
import time
import threading
from pathlib import Path
import tkinter as tk
from tkinter import scrolledtext, messagebox, ttk
import paramiko

# ==========================================
# CARGA DE VARIABLES DE ENTORNO (.env)
# ==========================================
ENV_PATH = Path(__file__).resolve().parent / ".env"

def load_env_fallback(filepath):
    """Fallback manual para leer .env si python-dotenv no está instalado."""
    if not filepath.exists():
        return
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, val = line.split("=", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if key not in os.environ:
                    os.environ[key] = val

try:
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=ENV_PATH)
except ImportError:
    load_env_fallback(ENV_PATH)

# ==========================================
# CONFIGURACIÓN (.env con valores por defecto)
# ==========================================
SERVER_IP = os.getenv("SERVER_IP", "192.168.1.100")
SERVER_PORT = int(os.getenv("SERVER_PORT", "22"))
SERVER_USER = os.getenv("SERVER_USER", "tu_usuario")
SERVER_PASSWORD = os.getenv("SERVER_PASSWORD", "")

# ORIGEN: Directorio o disco externo montado
SOURCE_DIR = os.getenv("SOURCE_DIR", "/media/daevon/TuDiscoExterno")

# DESTINO: Carpeta interna donde guardar el .tar.gz
BACKUP_DIR = os.getenv("BACKUP_DIR", "/home/tu_usuario/backups")
BACKUP_FILENAME = os.getenv("BACKUP_FILENAME", "backup_disco_externo.tar.gz")
BACKUP_FILE = f"{BACKUP_DIR.rstrip('/')}/{BACKUP_FILENAME}"

# USE_SUDO: Recomendado si el usuario no es root
USE_SUDO = os.getenv("USE_SUDO", "true").lower() in ("true", "1", "yes")

# Intentar instalar 'pv' automáticamente en el servidor si no está instalado
AUTO_INSTALL_PV = os.getenv("AUTO_INSTALL_PV", "true").lower() in ("true", "1", "yes")
# ==========================================


def format_bytes(num_bytes):
    """Formatea bytes a B, KB, MB, GB o TB legible."""
    if num_bytes is None or num_bytes < 0:
        return "0 B"
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if num_bytes < 1024.0:
            return f"{num_bytes:.2f} {unit}"
        num_bytes /= 1024.0
    return f"{num_bytes:.2f} PB"


def format_seconds(seconds):
    """Formatea segundos a formato HH:MM:SS."""
    if seconds is None or seconds < 0 or seconds > 86400 * 30:
        return "--:--:--"
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


class BackupApp:
    def __init__(self, root):
        self.root = root
        self.root.title("SSH Backup - Progreso en Tiempo Real")
        self.root.geometry("720x570")
        self.root.minsize(640, 480)

        self.start_time = 0
        self.total_bytes = 0

        # Frame superior para info del servidor y botón
        top_frame = tk.Frame(root, pady=10, padx=12, bg="#202020")
        top_frame.pack(fill=tk.X)

        sudo_tag = " [sudo]" if USE_SUDO and SERVER_USER != "root" else ""
        info_header = f"Servidor: {SERVER_USER}@{SERVER_IP}:{SERVER_PORT}{sudo_tag}"
        info_routes = f"Origen:  {SOURCE_DIR}\nDestino: {BACKUP_FILE}"

        info_frame = tk.Frame(top_frame, bg="#202020")
        info_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(info_frame, text=info_header, font=("Arial", 10, "bold"), fg="#ffffff", bg="#202020", anchor="w").pack(fill=tk.X)
        tk.Label(info_frame, text=info_routes, font=("Consolas", 8), fg="#b0bec5", bg="#202020", justify=tk.LEFT, anchor="w").pack(fill=tk.X, pady=(3, 0))

        self.btn_connect = tk.Button(
            top_frame,
            text="Conectar y Respaldar",
            bg="#2e7d32",
            fg="white",
            font=("Arial", 10, "bold"),
            relief=tk.RAISED,
            padx=12,
            pady=6,
            command=self.start_process
        )
        self.btn_connect.pack(side=tk.RIGHT, padx=5)

        # Frame de métricas de progreso (Porcentaje, velocidad, tiempo restante)
        progress_frame = tk.Frame(root, padx=12, pady=6, bg="#eceff1")
        progress_frame.pack(fill=tk.X)

        self.lbl_progress_left = tk.Label(
            progress_frame,
            text="Listo para iniciar",
            font=("Arial", 9, "bold"),
            fg="#263238",
            bg="#eceff1"
        )
        self.lbl_progress_left.pack(side=tk.LEFT)

        self.lbl_progress_right = tk.Label(
            progress_frame,
            text="Velocidad: -- | Restante: --:--:-- | Tiempo: 00:00:00",
            font=("Consolas", 8),
            fg="#37474f",
            bg="#eceff1"
        )
        self.lbl_progress_right.pack(side=tk.RIGHT)

        # Barra de progreso
        self.progress = ttk.Progressbar(root, orient=tk.HORIZONTAL, length=100, mode='determinate', maximum=100)
        self.progress.pack(fill=tk.X, padx=12, pady=(0, 6))

        # Consola de logs
        self.log_area = scrolledtext.ScrolledText(
            root, wrap=tk.WORD, height=18, bg="#121212", fg="#a6e22e", font=("Consolas", 9)
        )
        self.log_area.pack(fill=tk.BOTH, expand=True, padx=12, pady=5)

        # Mensajes de arranque inicial
        self.log(f"Listo para conectar a {SERVER_IP}:{SERVER_PORT} como '{SERVER_USER}'")
        self.log(f"  • Origen:  {SOURCE_DIR}")
        self.log(f"  • Destino: {BACKUP_FILE}")

        if not ENV_PATH.exists():
            self.log("\n[!] AVISO: No se encontró el archivo .env.")
            self.log("    Copia .env.example como .env y edita tus datos reales.")
        else:
            self.log("[+] Configuración cargada desde .env")

    def log(self, message):
        """Thread-safe log para actualizar la consola desde cualquier hilo."""
        self.root.after(0, self._append_log, message)

    def _append_log(self, message):
        self.log_area.insert(tk.END, message + "\n")
        self.log_area.see(tk.END)

    def update_progress_ui(self, percent, processed_bytes, total_bytes, speed, eta_seconds, elapsed_seconds):
        """Actualiza la barra y etiquetas de progreso de forma thread-safe."""
        def _update():
            str_proc = format_bytes(processed_bytes)
            str_spd = f"{format_bytes(speed)}/s" if speed > 0 else "--/s"
            str_elp = format_seconds(elapsed_seconds)

            if total_bytes > 0:
                p = max(0.0, min(100.0, percent))
                self.progress.config(mode='determinate')
                self.progress['value'] = p
                str_tot = format_bytes(total_bytes)
                str_eta = format_seconds(eta_seconds)
                self.lbl_progress_left.config(text=f"{p:.1f}% ({str_proc} de {str_tot})")
                self.lbl_progress_right.config(text=f"Velocidad: {str_spd} | Restante: {str_eta} | Tiempo: {str_elp}")
            else:
                # Si el total no se conoce, barra animada mostrando bytes copiados
                self.lbl_progress_left.config(text=f"Copiando... {str_proc} transferidos")
                self.lbl_progress_right.config(text=f"Velocidad: {str_spd} | Tiempo: {str_elp}")

        self.root.after(0, _update)

    def reset_progress_ui(self, status_text="Listo"):
        def _reset():
            self.progress.stop()
            self.progress.config(mode='determinate')
            self.progress['value'] = 0
            self.lbl_progress_left.config(text=status_text)
            self.lbl_progress_right.config(text="Velocidad: -- | Restante: --:--:-- | Tiempo: 00:00:00")
        self.root.after(0, _reset)

    def show_info(self, title, message):
        self.root.after(0, lambda: messagebox.showinfo(title, message))

    def show_error(self, title, message):
        self.root.after(0, lambda: messagebox.showerror(title, message))

    def start_process(self):
        self.btn_connect.config(state=tk.DISABLED)
        self.reset_progress_ui("Iniciando conexión...")
        self.log("\n[!] Iniciando hilo de conexión SSH...")
        threading.Thread(target=self.ssh_and_backup, daemon=True).start()

    def run_cmd(self, client, command):
        """Ejecuta comando remoto con sudo si USE_SUDO está activo.
        Usa bash -c para que pipes (|), redirecciones (>) y (&&) se ejecuten íntegramente con root.
        """
        if USE_SUDO:
            # Escapar comillas dobles y variables para bash -c
            escaped = command.replace('"', '\\"')
            full_command = f'sudo -S -p "" bash -c "{escaped}"'
        else:
            full_command = command

        stdin, stdout, stderr = client.exec_command(full_command)

        if USE_SUDO and SERVER_PASSWORD:
            stdin.write(f"{SERVER_PASSWORD}\n")
            stdin.flush()

        return stdin, stdout, stderr

    def get_source_size(self, client):
        """Calcula el tamaño en bytes del origen en el servidor de forma robusta."""
        self.log("[*] Calculando tamaño de datos en el origen...")

        # 1. Intentar du -sk (estándar POSIX, funciona en subcarpetas y puntos de montaje)
        cmd_du = f"du -sk '{SOURCE_DIR}' 2>/dev/null | awk '{{print $1 * 1024}}'"
        stdin, stdout, stderr = self.run_cmd(client, cmd_du)
        out = stdout.read().decode().strip()
        try:
            val = int(out.split()[-1])
            if val > 0:
                return val
        except Exception:
            pass

        # 2. Alternativa con df si fuera punto de montaje
        cmd_df = f"df -kP '{SOURCE_DIR}' 2>/dev/null | awk 'NR==2 {{print $3 * 1024}}'"
        stdin, stdout, stderr = self.run_cmd(client, cmd_df)
        out = stdout.read().decode().strip()
        try:
            val = int(out.split()[-1])
            if val > 0:
                return val
        except Exception:
            pass

        return 0

    def ensure_pv_installed(self, client):
        """Verifica si 'pv' (Pipe Viewer) está en el servidor o intenta instalarlo."""
        stdin, stdout, stderr = self.run_cmd(client, "which pv")
        if stdout.channel.recv_exit_status() == 0:
            return True

        if AUTO_INSTALL_PV and USE_SUDO:
            self.log("[*] Herramienta 'pv' no encontrada en el servidor.")
            self.log("[*] Instalando 'pv' con sudo para visualización de progreso...")
            # Intentar instalación directa o con update si falla
            cmd_install = "DEBIAN_FRONTEND=noninteractive apt-get install -y -qq pv || (apt-get update -qq && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq pv)"
            stdin, stdout, stderr = self.run_cmd(client, cmd_install)
            _ = stdout.channel.recv_exit_status()

            # Comprobar si se instaló
            chk_in, chk_out, _ = self.run_cmd(client, "which pv")
            if chk_out.channel.recv_exit_status() == 0:
                self.log("[+] 'pv' instalada correctamente en el servidor.")
                return True
            else:
                self.log("[!] No se pudo instalar 'pv' automáticamente.")
                self.log("    (Consejo: ejecuta 'sudo apt install pv' en el servidor para porcentaje y tiempo restante exactos)")
        return False

    def ssh_and_backup(self):
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        try:
            self.log(f"[*] Conectando a {SERVER_IP}:{SERVER_PORT} como {SERVER_USER}...")
            client.connect(
                hostname=SERVER_IP,
                port=SERVER_PORT,
                username=SERVER_USER,
                password=SERVER_PASSWORD,
                timeout=12
            )
            self.log("[+] Conexión SSH establecida con éxito.")

            # 1. Comprobar que el origen existe y está accesible
            self.log(f"[*] Verificando origen: {SOURCE_DIR}")
            stdin, stdout, stderr = self.run_cmd(client, f"test -d '{SOURCE_DIR}'")
            if stdout.channel.recv_exit_status() != 0:
                raise RuntimeError(
                    f"El directorio '{SOURCE_DIR}' NO existe o no es accesible.\n"
                    f"¿Está el disco externo conectado y montado en el servidor?"
                )

            # 2. Comprobar o crear directorio de destino
            self.log(f"[*] Verificando directorio de destino: {BACKUP_DIR}")
            stdin, stdout, stderr = self.run_cmd(client, f"mkdir -p '{BACKUP_DIR}'")
            if stdout.channel.recv_exit_status() != 0:
                err = stderr.read().decode().strip()
                raise RuntimeError(f"Error creando directorio destino {BACKUP_DIR}: {err}")

            # 3. Comprobar tamaño y herramienta de progreso 'pv'
            self.total_bytes = self.get_source_size(client)
            if self.total_bytes > 0:
                self.log(f"[+] Tamaño total a procesar: {format_bytes(self.total_bytes)}")
            else:
                self.log("[!] No se pudo determinar el tamaño exacto; se monitorizarán los bytes generados.")

            has_pv = self.ensure_pv_installed(client)

            # 4. Lanzar la compresión
            self.start_time = time.time()
            self.log(f"[*] Iniciando empaquetado y compresión hacia {BACKUP_FILE}...")

            if has_pv and self.total_bytes > 0:
                # PIPELINE CON PROGRESO EXACTO MEDIANTE PV
                backup_pipeline = (
                    f"set -o pipefail; "
                    f"tar -cf - '{SOURCE_DIR}' --exclude='{BACKUP_DIR}' --exclude='*lost+found*' "
                    f"| pv -n -i 1 -s {self.total_bytes} "
                    f"| gzip > '{BACKUP_FILE}'"
                )

                stdin, stdout, stderr = self.run_cmd(client, backup_pipeline)

                for raw_line in iter(stderr.readline, ""):
                    line = raw_line.strip()
                    if not line:
                        continue

                    # Si es un número, es la señal de progreso de pv
                    try:
                        percent = float(line)
                        elapsed = time.time() - self.start_time
                        processed = self.total_bytes * (percent / 100.0)
                        speed = processed / elapsed if elapsed > 0 else 0
                        remaining = (self.total_bytes - processed) / speed if speed > 0 else 0

                        self.update_progress_ui(
                            percent=percent,
                            processed_bytes=processed,
                            total_bytes=self.total_bytes,
                            speed=speed,
                            eta_seconds=remaining,
                            elapsed_seconds=elapsed
                        )
                    except ValueError:
                        self.log(f"[remoto] {line}")

                exit_status = stdout.channel.recv_exit_status()

            else:
                # MONITOR ALTERNATIVO SI NO HAY PV O NO SE DETERMINÓ EL TAMAÑO
                self.root.after(0, lambda: self.progress.config(mode='indeterminate'))
                self.root.after(0, self.progress.start, 10)

                tar_cmd = (
                    f"tar -czpf '{BACKUP_FILE}' "
                    f"--exclude='{BACKUP_DIR}' --exclude='*lost+found*' "
                    f"'{SOURCE_DIR}'"
                )
                stdin, stdout, stderr = self.run_cmd(client, tar_cmd)

                while not stdout.channel.exit_status_ready():
                    time.sleep(2)
                    _, s_out, _ = self.run_cmd(client, f"stat -c %s '{BACKUP_FILE}' 2>/dev/null || echo 0")
                    try:
                        current_size = int(s_out.read().decode().strip().split()[-1])
                    except Exception:
                        current_size = 0

                    elapsed = time.time() - self.start_time
                    speed = current_size / elapsed if elapsed > 0 else 0

                    if self.total_bytes > 0:
                        est_percent = min(99.0, (current_size / (self.total_bytes * 0.6)) * 100.0)
                    else:
                        est_percent = 0.0

                    self.update_progress_ui(
                        percent=est_percent,
                        processed_bytes=current_size,
                        total_bytes=self.total_bytes,
                        speed=speed,
                        eta_seconds=0,
                        elapsed_seconds=elapsed
                    )

                self.root.after(0, self.progress.stop)
                exit_status = stdout.channel.recv_exit_status()

            total_elapsed = time.time() - self.start_time

            # Comprobar resultado final
            if exit_status in (0, 1):
                self.update_progress_ui(100.0, self.total_bytes, self.total_bytes, 0, 0, total_elapsed)
                self.log(f"\n[+] ¡ÉXITO! Copia completada en {format_seconds(total_elapsed)}.")
                self.log(f"[+] Archivo guardado en: {BACKUP_FILE}")
                self.show_info(
                    "Copia completada",
                    f"Copia de seguridad guardada con éxito en:\n{BACKUP_FILE}\n\nTiempo total: {format_seconds(total_elapsed)}"
                )
            else:
                err_msg = stderr.read().decode().strip()
                self.log(f"\n[-] ERROR en el backup. Código de salida: {exit_status}")
                if err_msg:
                    self.log(f"Detalle: {err_msg}")
                self.show_error("Error", f"Falló el backup (código {exit_status}).\nRevisa la consola.")

        except paramiko.AuthenticationException:
            self.log("\n[-] ERROR: Fallo de autenticación SSH. Revisa usuario y contraseña en .env.")
            self.show_error("Error SSH", "Fallo de autenticación SSH.")
        except Exception as e:
            self.log(f"\n[-] ERROR: {str(e)}")
            self.show_error("Error", f"Ocurrió un error:\n{str(e)}")
        finally:
            client.close()
            self.log("[*] Conexión SSH cerrada.")
            self.root.after(0, lambda: self.btn_connect.config(state=tk.NORMAL))


if __name__ == "__main__":
    root = tk.Tk()
    app = BackupApp(root)
    root.mainloop()
