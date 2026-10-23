# SSH Server Backup Tool

[English](#english) | [Español](#español)

---

## Español

Herramienta de escritorio sencilla en Python (Tkinter) para realizar copias de seguridad de carpetas o discos duros externos montados en un servidor Linux remoto, empaquetándolos y comprimiéndolos en el almacenamiento interno a través de SSH con `tar.gz`.

### Características
- Interfaz gráfica básica con barra de porcentaje real (0-100%), velocidad (MB/s) y tiempo restante estimado (ETA).
- Medición de flujo en tiempo real mediante `pv` (Pipe Viewer) en el servidor.
- Conexión por SSH mediante Paramiko.
- Verificación previa del punto de montaje en el servidor antes de lanzar la compresión.
- Soporte para ejecutar comandos mediante `sudo` de forma no interactiva.
- Carga de credenciales y rutas mediante archivo `.env` para no exponer datos sensibles en Git.

---

### Requisitos e instalación

#### En Debian / Ubuntu
Puedes instalar las librerías directamente desde los repositorios del sistema:
```bash
sudo apt update
sudo apt install python3-paramiko python3-dotenv python3-tk
```

#### Con entorno virtual (venv)
Si prefieres aislar dependencias con Python:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### Configuración

1. Crea tu archivo `.env` a partir de la plantilla:
```bash
cp .env.example .env
```

2. Edita las variables en `.env`:
```env
SERVER_IP=192.168.1.100
SERVER_PORT=22
SERVER_USER=tu_usuario
SERVER_PASSWORD=tu_contraseña

# Ruta del disco externo o directorio a respaldar
SOURCE_DIR=/media/usuario/DiscoExterno

# Directorio de destino en el almacenamiento interno del servidor
BACKUP_DIR=/home/usuario/backups

# Nombre del archivo resultante
BACKUP_FILENAME=backup_disco.tar.gz

# Habilitar sudo para comandos remotos (necesario si el usuario no es root)
USE_SUDO=true

# Salida detallada en consola (dejar en false para backups grandes)
VERBOSE=false
```

Nota: el archivo `.env` está incluido en `.gitignore` para que tus credenciales nunca se suban a un repositorio público.

---

### Permisos en el servidor

Si el usuario configurado no es root y el disco externo o el directorio de destino requieren permisos elevados:

- `sudo su -` no es adecuado para scripts remotos porque abre una shell interactiva que bloquea la ejecución.
- Con `USE_SUDO=true`, el script utiliza `sudo -S` pasando la contraseña por entrada estándar de forma automática.
- Alternativamente, puedes permitir a tu usuario ejecutar `tar`, `mkdir` y `test` sin contraseña añadiendo una regla en `/etc/sudoers.d/backups`:
```bash
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/mkdir, /usr/bin/tar, /usr/bin/test" | sudo tee /etc/sudoers.d/backups
```

---

### Uso

Lanza el script desde tu terminal:
```bash
python3 Backup.py
```

Pulsa "Conectar y Respaldar". El proceso se ejecutará en segundo plano mostrando los eventos en el área de texto.

---

### Subir a GitHub

Si quieres publicar este proyecto en tu cuenta:
```bash
git init -b main
git status
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/TU_USUARIO/TU_REPOSITORIO.git
git push -u origin main
```

---

## English

Simple Python desktop utility (Tkinter) to back up folders or external hard drives mounted on a remote Linux server, compressing them into the internal storage over SSH using `tar.gz`.

### Features
- Minimal desktop UI with real-time percentage progress bar (0-100%), transfer speed (MB/s), and estimated time remaining (ETA).
- Real-time stream monitoring using `pv` (Pipe Viewer) on the server.
- SSH connectivity powered by Paramiko.
- Pre-check to verify the mount point or directory exists before running compression.
- Non-interactive `sudo` support for remote execution.
- Configuration loaded via `.env` to keep credentials and paths out of version control.

---

### Requirements and Installation

#### On Debian / Ubuntu
Install the required packages directly from system repositories:
```bash
sudo apt update
sudo apt install python3-paramiko python3-dotenv python3-tk
```

#### Using a virtual environment (venv)
If you prefer an isolated Python environment:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

### Configuration

1. Create your `.env` file from the example template:
```bash
cp .env.example .env
```

2. Adjust the variables inside `.env`:
```env
SERVER_IP=192.168.1.100
SERVER_PORT=22
SERVER_USER=your_username
SERVER_PASSWORD=your_password

# External drive or folder to back up
SOURCE_DIR=/media/user/ExternalDrive

# Destination directory on the server's internal drive
BACKUP_DIR=/home/user/backups

# Output archive name
BACKUP_FILENAME=backup_external_drive.tar.gz

# Enable sudo for remote operations (recommended if not root)
USE_SUDO=true

# Verbose tar output (keep false for large backups to save memory)
VERBOSE=false
```

Note: `.env` is listed in `.gitignore` to prevent secret leakage.

---

### Server Permissions

When using a non-root account that needs elevated permissions:

- Running `sudo su -` does not work in headless SSH scripts because it waits for an interactive login terminal.
- With `USE_SUDO=true`, the script uses `sudo -S` and supplies the password through standard input automatically.
- Alternatively, you can allow passwordless execution for required utilities in `/etc/sudoers.d/backups`:
```bash
echo "$USER ALL=(ALL) NOPASSWD: /usr/bin/mkdir, /usr/bin/tar, /usr/bin/test" | sudo tee /etc/sudoers.d/backups
```

---

### Usage

Run the program:
```bash
python3 Backup.py
```

Click "Conectar y Respaldar". The backup runs in the background and prints logs to the console window.

---

### Pushing to GitHub

To publish this repository:
```bash
git init -b main
git status
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USER/YOUR_REPO.git
git push -u origin main
```
