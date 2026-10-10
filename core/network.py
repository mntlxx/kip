import json
import socket
import psutil
from pathlib import Path

PORT = 8008
CONFIG_PATH = Path("core/network_config.json")


def is_port_in_use(port: int = PORT, host: str = "0.0.0.0") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def get_all_valid_ips() -> list[dict]:
    interfaces = []
    try:
        for iface_name, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET and not addr.address.startswith("127."):
                    interfaces.append({
                        "name": iface_name,
                        "ip": addr.address,
                        "netmask": addr.netmask
                    })
    except Exception:
        pass
    return interfaces


def load_network_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"selected_ip": None, "priority_interfaces": []}


def save_active_ip(ip: str) -> dict:
    cfg = load_network_config()
    cfg["selected_ip"] = ip
    
    priority = cfg.get("priority_interfaces", [])
    if ip not in priority:
        priority.append(ip)
    cfg["priority_interfaces"] = priority

    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")
    return cfg


def resolve_best_ip() -> str:
    all_ifaces = get_all_valid_ips()
    active_ips = [item["ip"] for item in all_ifaces]

    cfg = load_network_config()

    selected_ip = cfg.get("selected_ip")
    if selected_ip and selected_ip in active_ips:
        return selected_ip

    for p_ip in cfg.get("priority_interfaces", []):
        if p_ip in active_ips:
            return p_ip

    for ip in active_ips:
        if (
            ip.startswith("192.168.") or 
            ip.startswith("10.") or 
            any(ip.startswith(f"172.{i}.") for i in range(16, 32))
        ):
            return ip

    return active_ips[0] if active_ips else "127.0.0.1"