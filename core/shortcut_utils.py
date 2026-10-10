import sys
import os
import winreg

APP_NAME = "KipRemote"

def get_exe_path() -> str:
    if getattr(sys, 'frozen', False):
        return sys.executable
    return os.path.abspath(sys.argv[0])

def set_autostart(enable: bool = True) -> bool:
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    exe_path = f'"{get_exe_path()}"'
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS)
        if enable:
            winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, exe_path)
        else:
            try:
                winreg.DeleteValue(key, APP_NAME)
            except FileNotFoundError:
                pass
        winreg.CloseKey(key)
        return True
    except Exception as e:
        return False


def enable_autostart() -> bool:
    return set_autostart(True)


def disable_autostart() -> bool:
    return set_autostart(False)


def toggle_autostart() -> bool:
    current_state = is_autostart_enabled()
    new_state = not current_state
    if set_autostart(new_state):
        return new_state
    return current_state


def is_autostart_enabled() -> bool:
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ)
        value, _ = winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        clean_reg_path = value.replace('"', '').strip().lower()
        clean_current_path = get_exe_path().replace('"', '').strip().lower()
        
        return clean_reg_path == clean_current_path
    except Exception:
        return False
