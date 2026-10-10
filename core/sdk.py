from typing import Any, Dict, Optional


def action(name: str, label: str, widget: str = "button", props: Optional[Dict[str, Any]] = None):
    def decorator(func):
        func._is_action = True
        func._action_name = name
        func._action_meta = {
            "name": name,
            "label": label,
            "widget": widget,
            "props": props or {}
        }
        return func
    return decorator


class BasePlugin:
    INFO: Dict[str, Any] = {
        "id": "",
        "name": "",
        "version": "1.0.0",
        "author": "",
        "description": ""
    }

    def __init__(self):
        info = getattr(self, "INFO", {})
        self.id = info.get("id") or self.__class__.__name__
        self.name = info.get("name") or self.__class__.__name__
        self.version = info.get("version", "1.0.0")
        self.author = info.get("author", "")
        self.description = info.get("description", "")

    def on_load(self):
        pass

    def on_unload(self):
        pass

    def get_manifest(self) -> Dict[str, Any]:
        actions_dict = {}

        for attr_name in dir(self):
            attr = getattr(self, attr_name, None)
            if callable(attr) and getattr(attr, "_is_action", False):
                meta = attr._action_meta.copy()
                props = dict(meta.get("props", {}))

                if "options" in props and isinstance(props["options"], str):
                    method_name = props["options"]
                    method = getattr(self, method_name, None)
                    if callable(method):
                        try:
                            props["options"] = method()
                        except Exception as e:
                            props["options"] = [{"label": f"Ошибка: {e}", "value": ""}]
                    else:
                        props["options"] = []

                actions_dict[meta["name"]] = {
                    "label": meta["label"],
                    "widget": meta["widget"],
                    "props": props
                }

        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "author": self.author,
            "description": self.description,
            "actions": actions_dict
        }