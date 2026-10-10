import importlib.util
import inspect
from pathlib import Path
import sys
from typing import Any, Dict, List

from core.sdk import BasePlugin


class PluginManager:
    def __init__(self, plugins_dir: str = "./plugins"):
        self.plugins_dir = Path(plugins_dir)
        self.loaded_plugins: Dict[str, BasePlugin] = {}

    def reload(self):
        for plugin in list(self.loaded_plugins.values()):
            if hasattr(plugin, "on_unload") and callable(plugin.on_unload):
                try:
                    plugin.on_unload()
                except Exception as e:
                    pass

        self.loaded_plugins.clear()

        if not self.plugins_dir.exists():
            self.plugins_dir.mkdir(parents=True, exist_ok=True)
            return

        candidates = []
        for path in self.plugins_dir.iterdir():
            if path.is_file() and path.suffix == ".py" and not path.name.startswith("_"):
                candidates.append((path.stem, path))
            elif path.is_dir():
                script_file = path / "plugin.py"
                if script_file.exists():
                    candidates.append((path.name, script_file))

        for plugin_key, script_file in candidates:
            module_fullname = f"plugins.{plugin_key}"

            try:
                spec = importlib.util.spec_from_file_location(module_fullname, script_file)
                if not spec or not spec.loader:
                    continue

                module = importlib.util.module_from_spec(spec)
                sys.modules[module_fullname] = module
                spec.loader.exec_module(module)

                for attr in dir(module):
                    obj = getattr(module, attr)
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, BasePlugin)
                        and obj is not BasePlugin
                    ):
                        instance = obj()
                        if hasattr(instance, "on_load") and callable(instance.on_load):
                            try:
                                instance.on_load()
                            except Exception as load_err:
                                pass

                        manifest = instance.get_manifest()
                        plugin_id = manifest.get("id", obj.__name__)
                        self.loaded_plugins[plugin_id] = instance
                        break
            except Exception as e:
                pass

    def execute_action(self, plugin_name: str, action_name: str, **kwargs) -> Any:
        plugin = self.loaded_plugins.get(plugin_name)
        if not plugin:
            raise ValueError(f"Плагин '{plugin_name}' не найден")

        target_method = None
        for attr_name in dir(plugin):
            attr = getattr(plugin, attr_name, None)
            if callable(attr) and getattr(attr, "_is_action", False):
                if getattr(attr, "_action_name", None) == action_name:
                    target_method = attr
                    break

        if not target_method:
            target_method = getattr(plugin, action_name, None)

        if not target_method or not callable(target_method):
            raise AttributeError(f"Действие '{action_name}' не найдено в '{plugin_name}'")

        sig = inspect.signature(target_method)
        params = [p for p in sig.parameters.values() if p.name != "self"]

        if not params:
            return target_method()

        raw_val = kwargs.get("value", kwargs.get("cmd"))
        if raw_val is not None:
            first_param = params[0]
            try:
                if first_param.annotation == str:
                    return target_method(str(raw_val))
                elif first_param.annotation == int:
                    return target_method(int(float(raw_val)))
                elif first_param.annotation == float:
                    return target_method(float(raw_val))
                elif first_param.annotation == bool:
                    return target_method(bool(raw_val))
            except Exception:
                pass
            return target_method(raw_val)

        return target_method()

    def get_ui_config(self) -> List[Dict[str, Any]]:
        configs = []
        for plugin_id, instance in self.loaded_plugins.items():
            try:
                configs.append(instance.get_manifest())
            except Exception as e:
                configs.append({
                    "id": plugin_id,
                    "name": getattr(instance, "name", plugin_id),
                    "actions": {}
                })
        return configs