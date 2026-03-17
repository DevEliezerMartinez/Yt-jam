# YT Jam 🎵

Herramienta para que el equipo de la oficina pueda agregar videos de YouTube a una playlist compartida con un solo click, directamente desde el navegador.

## ¿Cómo funciona?

```
[Compañero] → Chrome Extension → Cloudflare Tunnel → FastAPI Server → YouTube API → Playlist
```

1. Cualquier compañero abre un video en YouTube
2. Hace click en la extensión de Chrome
3. El video se agrega automáticamente a la playlist de la oficina

---

## Estructura del proyecto

```
yt-jam/
├── server/
│   ├── main.py              ← Servidor FastAPI (endpoint POST /queue)
│   ├── requirements.txt     ← Dependencias de Python
│   ├── .env.example         ← Plantilla de variables de entorno
│   ├── credentials.json     ← OAuth2 de Google Cloud
│   └── token.json           ← Token generado al autenticar (auto-renovable)
├── extension/
│   ├── manifest.json        ← Manifest v3 para Chrome
│   ├── popup.html           ← UI del popup
│   ├── popup.js             ← Lógica: detecta videoId y llama al servidor
│   └── icons/               ← icon16.png, icon48.png, icon128.png
├── tray.py                  ← App de bandeja del sistema (Windows) con pystray
├── start.bat                ← Launcher: instala deps del tray y lo arranca
└── extension.zip            ← Extensión empaquetada para compartir
```

---

## Requisitos previos

- **Python 3.10+** con pip
- **Google Cloud Console** — Proyecto con YouTube Data API v3 habilitada
- **Cloudflare Tunnel** (`cloudflared`) instalado y autenticado
- **Google Chrome** (para la extensión)

---

## Paso 1 — Crear la playlist "Oficina" en YouTube

1. Ve a [youtube.com](https://youtube.com) → tu cuenta → **Playlists → Nueva playlist**
2. Nómbrala como quieras (ej. `Oficina 🎵`)
3. Copia el ID de la URL:
   ```
   https://www.youtube.com/playlist?list=PL_ESTE_ES_EL_ID
   ```

---

## Paso 2 — Google Cloud Console (solo una vez, ~10 min)

1. Ve a [console.cloud.google.com](https://console.cloud.google.com)
2. Crea un proyecto nuevo (ej. `yt-jam`)
3. En el menú: **APIs y servicios → Biblioteca**
4. Busca **"YouTube Data API v3"** → Habilitar
5. Ve a **APIs y servicios → Credenciales → Crear credenciales → ID de cliente OAuth 2.0**
   - Tipo de aplicación: **Aplicación de escritorio**
   - Nombre: `yt-jam server`
6. Descarga el JSON → guárdalo como `server/credentials.json`
7. En **Pantalla de consentimiento OAuth** → agrega tu email como usuario de prueba

---

## Paso 3 — Configurar el servidor

```powershell
cd yt-jam\server

# Crear entorno virtual
python -m venv venv
venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt
```

Las dependencias instaladas son:

| Paquete                  | Versión |
| ------------------------ | ------- |
| fastapi                  | 0.111.0 |
| uvicorn[standard]        | 0.29.0  |
| google-auth              | 2.29.0  |
| google-auth-oauthlib     | 1.2.0   |
| google-api-python-client | 2.127.0 |
| python-dotenv            | 1.0.1   |
| pydantic                 | 2.7.1   |

Crea el archivo `.env` copiando el ejemplo:

```powershell
copy .env.example .env
```

Edita `.env` con tus valores reales:

```env
# ID de tu playlist "Oficina" en YouTube
YT_PLAYLIST_ID=PLxxxxxxxxxxxxxxxxxxxxxxxxx

# Clave secreta que la extensión manda en cada request
# Ponla también en extension/popup.js → SECRET_KEY
SECRET_KEY=contraseña_aqui
```

---

## Paso 4 — Primera autenticación (solo una vez)

```powershell
# Desde server/, con el venv activado
python -c "from main import get_youtube_client; get_youtube_client()"
```

Esto abre el navegador para que autorices con tu cuenta de Google.  
Se genera `token.json` automáticamente y se renueva solo cuando expira.

---

## Paso 5 — Levantar el servidor

```powershell
# Con el venv activado, dentro de server/
uvicorn main:app --host 0.0.0.0 --port 8000
```

Verifica que responde: [http://localhost:8000](http://localhost:8000)

```json
{ "status": "ok", "playlist": "TU_PLAYLIST_ID" }
```

### Endpoint disponible

| Método | Ruta     | Descripción                   |
| ------ | -------- | ----------------------------- |
| `GET`  | `/`      | Health check                  |
| `POST` | `/queue` | Agrega un video a la playlist |

**Body del POST `/queue`:**

```json
{
  "videoId": "dQw4w9WgXcQ",
  "title": "Título del video (opcional)",
  "secret": "tu-secret-key"
}
```

---

## Paso 6 — Cloudflare Tunnel (URL pública permanente)

El proyecto ya tiene un tunnel configurado en `jam.demail.store`.

Si necesitas configurarlo desde cero:

```powershell
# Autenticar (solo una vez)
cloudflared tunnel login

# Crear tunnel permanente
cloudflared tunnel create yt-jam

# Apuntar el dominio al tunnel
cloudflared tunnel route dns yt-jam jam.tudominio.com

# Correr el tunnel
cloudflared tunnel run yt-jam
```

---

## Paso 7 — Configurar la extensión

La extensión ya apunta al servidor en producción. Si cambias la URL o el secret, edita `extension/popup.js` líneas 3 y 6:

```js
const SERVER_URL = "https://jam.demail.store"; // ← URL del Cloudflare Tunnel
const SECRET_KEY = "contraseña_aqui"; // ← Debe coincidir con el .env
```

La extensión soporta:

- URLs del tipo `youtube.com/watch?v=...`
- URLs del tipo `youtu.be/...`

Detecta automáticamente el video activo en la pestaña actual.

---

## Paso 8 — Instalar la extensión en Chrome

1. Chrome → `chrome://extensions`
2. Activa **"Modo desarrollador"** (toggle arriba a la derecha)
3. Click **"Cargar descomprimida"**
4. Selecciona la carpeta `extension/`
5. ¡Listo! El ícono aparece en la barra de Chrome

También puedes compartir el archivo `extension.zip` con tus compañeros.

**Permisos que solicita la extensión:**

- `activeTab` — leer la URL de la pestaña activa
- `storage` — guardar configuración local
- `host_permissions`: `*.youtube.com` y `jam.demail.store`

---

## Arranque automático en Windows

### Opción A — `start.bat` (recomendado)

Doble click en `start.bat` o agrégalo a **shell:startup** para que arranque solo al iniciar sesión.

El `.bat` hace lo siguiente:

1. Instala `pystray`, `pillow` y `requests` en el venv si no están
2. Lanza `tray.py` en segundo plano (sin ventana de consola)

### Opción B — Tray app (`tray.py`)

La app de bandeja del sistema ofrece:

- **Ícono verde** 🟢 → servidor corriendo
- **Ícono rojo** 🔴 → servidor detenido
- **Ícono gris** ⚫ → iniciando

**Menú de clic derecho:**

- ▶ Iniciar — arranca `uvicorn` + `cloudflared tunnel run yt-jam`
- ⏹ Detener — detiene ambos procesos
- 🌐 Abrir servidor — abre `http://localhost:8000` en el navegador
- ✖ Salir — detiene todo y cierra el tray

**Dependencias extra del tray** (se instalan con `start.bat`):

```
pystray
pillow
requests
```

---

## Uso diario

1. Ejecutar `start.bat` (o que arranque automáticamente)
2. El ícono en la bandeja confirma que el servidor está activo
3. Un compañero abre un video en YouTube
4. Click en el ícono de la extensión
5. Click en **"Agregar a la cola"**
6. El video aparece en la playlist al instante 🎵

---

## Archivos sensibles (no subir a git)

El `.gitignore` excluye:

```
server/.env
server/credentials.json
server/token.json
server/venv/
```
