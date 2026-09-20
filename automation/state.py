import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config.json"
STATE = ROOT / "state.json"

def load_config():
    try:
        return json.loads(CONFIG.read_text(encoding="utf-8"))
    except Exception:
        return {}

def save_config(data):
    old = load_config()
    old.update(data)
    CONFIG.write_text(json.dumps(old, ensure_ascii=False, indent=2), encoding="utf-8")

def load_state():
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception:
        return {"completed": {}}

def mark_completed(file_path, size, mtime):
    state = load_state()
    state.setdefault("completed", {})[str(file_path)] = {"size": size, "mtime": mtime}
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")

def already_completed(file_path, size, mtime):
    item = load_state().get("completed", {}).get(str(file_path))
    return bool(item and item.get("size") == size and item.get("mtime") == mtime)
