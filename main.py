import sys
import os
import inspect
import json
import threading
from pathlib import Path
import subprocess
from datetime import datetime
import pystray
import webbrowser

from pydantic import BaseModel, ConfigDict
import uvicorn
from fastapi import Body, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from PIL import Image, ImageDraw
from typing import List, Optional, Any

from core.plugin_loader import PluginManager
from core.network import (
    load_network_config,
    get_all_valid_ips, 
    resolve_best_ip, 
    save_active_ip, 
    is_port_in_use,
    PORT
)
from core.shortcut_utils import (
    toggle_autostart, 
    enable_autostart, 
    disable_autostart, 
    is_autostart_enabled
)

class DummyWriter:
    def write(self, data):
        pass
    def flush(self):
        pass
    def isatty(self):
        return False

if sys.stdout is None or sys.stderr is None:
    dummy = DummyWriter()
    sys.stdout = dummy
    sys.stderr = dummy

    import builtins
    builtins.print = lambda *args, **kwargs: None

if getattr(sys, 'frozen', False):
    os.chdir(os.path.dirname(sys.executable))
else:
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

LOG_FILE = Path("app.log")

def log(message: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_message = f"[{timestamp}] {message}\n"
    
    if sys.stdout is not None and not isinstance(sys.stdout, DummyWriter):
        try:
            sys.stdout.write(formatted_message)
        except Exception:
            pass
            
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted_message)
    except Exception:
        pass

def get_resource_path(relative_path: str) -> str:
    if hasattr(sys, '_MEIPASS'):
        base_path = Path(sys._MEIPASS)
    else:
        base_path = Path(__file__).parent
        
    return str(base_path / relative_path)

plugin_manager = PluginManager()
plugin_manager.reload()

# ИСПРАВЛЕНИЕ: Базовая директория для конфигов (layout.json) зависит от того, запущен ли .exe
if getattr(sys, 'frozen', False):
    BASE_DIR = Path(sys.executable).parent
else:
    BASE_DIR = Path(__file__).resolve().parent

LAYOUT_FILE = BASE_DIR / "layout.json"

app = FastAPI(title="Kip Control Center")

app.mount("/static", StaticFiles(directory=get_resource_path("static")), name="static")
templates = Jinja2Templates(directory=get_resource_path("templates"))

class LayoutItem(BaseModel):
    model_config = ConfigDict(extra="allow")

    plugin: str
    action: str
    label: Optional[str] = None
    widget: Optional[str] = None

class LayoutTab(BaseModel):
    id: str
    title: str
    items: List[LayoutItem] = []

class LayoutConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    active_tab: Optional[str] = "main"
    tabs: List[LayoutTab] = []

def load_layout():
    if not LAYOUT_FILE.exists():
        default_layout = {
            "active_tab": "main", 
            "tabs": [{"id": "main", "title": "главная", "items": []}]
        }
        LAYOUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        LAYOUT_FILE.write_text(json.dumps(default_layout, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        return json.loads(LAYOUT_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log(f"Ошибка чтения layout.json: {e}")
        return {"active_tab": "main", "tabs": [{"id": "main", "title": "главная", "items": []}]}

def save_layout(data: dict):
    LAYOUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    LAYOUT_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

class ActionPayload(BaseModel):
    value: Optional[Any] = None

class NetworkConfigRequest(BaseModel):
    ip: str

@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.get("/welcome", response_class=HTMLResponse)
def welcome(request: Request):
    return templates.TemplateResponse(request=request, name="welcome.html")

@app.get('/icon.ico', include_in_schema=False)
async def favicon():
    return FileResponse(get_resource_path('static/img/favicon.png'))

@app.get("/guide/plugins", response_class=HTMLResponse)
def guide_plugins(request: Request):
    return templates.TemplateResponse(request=request, name="guide_plugins.html")

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc):
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "code": 404,
            "title": "Ой! Страница потерялась",
            "message": "Кажется, такой страницы в Kip Control Center не существует.",
            "image": "/static/img/404.jpg"
        },
        status_code=404
    )

@app.exception_handler(500)
async def custom_500_handler(request: Request, exc):
    return templates.TemplateResponse(
        request=request,
        name="error.html",
        context={
            "code": 500,
            "title": "Что-то пошло не так...",
            "message": "Сервер споткнулся. Мы уже выясняем, в чём дело.",
            "image": "/static/img/500.jpg"
        },
        status_code=500
    )

@app.get("/api/plugins")
def get_plugins():
    """Возвращает сгенерированные манифесты всех плагинов."""
    try:
        return plugin_manager.get_ui_config()
    except Exception as e:
        log(f"[API Error] /api/plugins: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/plugins/{plugin_id}/actions/{action_name}")
async def run_plugin_action(plugin_id: str, action_name: str, payload: Optional[ActionPayload] = Body(None)):
    """Основная точка вызова экшенов плагинов с фронтенда app.js."""
    try:
        val = payload.value if payload else None
        res = plugin_manager.execute_action(plugin_id, action_name, value=val)
        return {"status": "ok", "result": res}
    except ValueError as ve:
        raise HTTPException(status_code=404, detail=str(ve))
    except AttributeError as ae:
        raise HTTPException(status_code=404, detail=str(ae))
    except Exception as e:
        log(f"[Action Error] {plugin_id}.{action_name}: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@app.get("/api/layout")
def get_layout():
    return load_layout()

@app.post("/api/layout")
async def update_layout(config: LayoutConfig):
    try:
        data = config.model_dump()
        save_layout(data)
        log("[Layout] Конфигурация успешно сохранена.")
        return {"status": "success", "result": "ok"}
    except Exception as e:
        log(f"[Layout Error] Не удалось сохранить layout: {e}")
        raise HTTPException(status_code=400, detail=f"Ошибка сохранения: {e}")

@app.get("/api/config")
def get_config():
    return plugin_manager.get_ui_config()

@app.post("/api/reload")
def reload_sys():
    plugin_manager.reload()
    return {"status": "ok"}

@app.get("/api/network/interfaces")
async def list_interfaces():
    return {
        "interfaces": get_all_valid_ips(),
        "active_ip": resolve_best_ip()
    }

@app.post("/api/network/set-active")
async def set_active_ip(data: dict = Body(...)):
    selected_ip = data.get("ip")
    if selected_ip:
        save_active_ip(selected_ip)
        return {"status": "ok", "active_ip": selected_ip}
    return {"status": "error", "message": "IP не передан"}

@app.post("/api/network/apply-ip")
async def apply_ip(data: NetworkConfigRequest):
    save_active_ip(data.ip)
    return {"status": "success", "active_ip": data.ip, "message": "IP успешно применен"}

@app.get("/api/info")
async def get_info():
    best_ip = resolve_best_ip()
    return {
        "ip": best_ip,
        "port": PORT,
        "full_url": f"http://{best_ip}:{PORT}"
    }

@app.get("/api/system/settings")
async def get_system_settings():
    return {
        "autostart": is_autostart_enabled()
    }

@app.post("/api/system/autostart")
async def set_autostart_api(data: dict = Body(...)):
    enabled = data.get("enabled", False)
    success = enable_autostart() if enabled else disable_autostart()
    return {"status": "ok", "autostart": is_autostart_enabled(), "success": success}

def get_current_connection_info():
    return resolve_best_ip()

def start_fastapi():
    current_ip = load_network_config().get("selected_ip")

    if is_port_in_use(PORT):
        log(f"[Server Error] Порт {PORT} уже занят другим приложением!")
        return

    if current_ip == "127.0.0.1":
        webbrowser.open(f"http://{current_ip}:{PORT}/welcome")

    log(f"[Server] Запуск FastAPI сервера на http://{current_ip}:{PORT} (слушает 0.0.0.0)")
    
    log_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {},
        "loggers": {
            "uvicorn": {"handlers": [], "level": "CRITICAL"},
            "uvicorn.error": {"handlers": [], "level": "CRITICAL"},
            "uvicorn.access": {"handlers": [], "level": "CRITICAL"},
        },
    }
    
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=PORT,
        reload=False,
        log_config=log_config,
        access_log=False,
        workers=1
    )
    
    server = uvicorn.Server(config)
    server.run()

def open_connection_info():
    ip = get_current_connection_info()
    url = f"http://{ip}:{PORT}/welcome"
    webbrowser.open(url)

def get_ip_label(item):
    ip = get_current_connection_info()
    return f"🌐 IP: {ip}:{PORT}"

def copy_ip_to_clipboard(icon, item):
    ip = get_current_connection_info()
    url = f"http://{ip}:{PORT}"
    
    if sys.platform.startswith("win"):
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            process = subprocess.Popen(
                'clip',
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                text=True,
                encoding='utf-8'
            )
            process.communicate(input=url)
        except Exception as e:
            log(f"Ошибка копирования в буфер: {e}")
    else:
        log(f"Буфер обмена клипборда не поддерживается на этой ОС. Ссылка: {url}")
    
    icon.notify(
        f"Адрес {url} скопирован в буфер обмена!",
        title="Kip Remote"
    )

def on_toggle_autostart_click(icon, item):
    new_state = toggle_autostart()
    msg = "Автозапуск включен!" if new_state else "Автозапуск отключен!"
    icon.notify(msg, title="Kip Control Center")

def create_tray_icon():
    icon_path = Path(get_resource_path("static/img/favicon.png"))
    
    if icon_path.exists():
        try:
            image = Image.open(icon_path)
        except Exception:
            image = Image.new('RGB', (64, 64), color=(0, 0, 0))
    else:
        image = Image.new('RGB', (64, 64), color=(0, 0, 0))
        d = ImageDraw.Draw(image)
        d.rectangle([24, 24, 40, 40], fill=(230, 230, 230))

    def on_exit(icon, item):
        log("[Tray] Выход из приложения...")
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem("Подключить", lambda i, m: open_connection_info()),
        pystray.MenuItem(get_ip_label, copy_ip_to_clipboard),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Автозапуск с Windows", on_toggle_autostart_click, checked=lambda item: is_autostart_enabled()),
        pystray.MenuItem("Перезагрузить Kip", lambda i, m: plugin_manager.reload()),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("Выход", on_exit)
    )
    return pystray.Icon("SystemRemote", image, f"Kip Remote ({PORT})", menu)

if __name__ == "__main__":
    log("[Main] Старт приложения...")
    
    server_thread = threading.Thread(target=start_fastapi, daemon=True)
    server_thread.start()

    icon = create_tray_icon()
    icon.run()