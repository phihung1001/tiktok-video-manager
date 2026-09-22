import json
import os
import tempfile
from pathlib import Path

from .paths import CONFIG, STATE, ensure_data_root


def _read(path, fallback):
    ensure_data_root()
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return fallback


def _write_atomic(path, data):
    ensure_data_root()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        try:
            path.replace(path.with_suffix(path.suffix + ".bak"))
        except OSError:
            pass
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        Path(temporary).replace(path)
    finally:
        try:
            Path(temporary).unlink(missing_ok=True)
        except OSError:
            pass


def load_config():
    return _read(CONFIG, {})


def save_config(data):
    old = load_config()
    old.update(data)
    _write_atomic(CONFIG, old)


def load_state():
    return _read(STATE, {"version": 2, "completed": {}, "uploads": {}})


def _save_state(state):
    state.setdefault("version", 2)
    state.setdefault("completed", {})
    state.setdefault("uploads", {})
    _write_atomic(STATE, state)


def save_state(state):
    _save_state(state)


def _key(file_path):
    return str(Path(file_path).resolve())


def mark_uploading(file_path, size, mtime):
    state = load_state()
    state.setdefault("uploads", {})[_key(file_path)] = {"status": "uploading", "size": size, "mtime": mtime}
    _save_state(state)


def mark_unknown(file_path, size, mtime, reason=""):
    state = load_state()
    state.setdefault("uploads", {})[_key(file_path)] = {"status": "unknown", "size": size, "mtime": mtime, "reason": reason}
    _save_state(state)


def mark_completed(file_path, size, mtime):
    state = load_state()
    key = _key(file_path)
    state.setdefault("completed", {})[key] = {"size": size, "mtime": mtime}
    state.setdefault("uploads", {}).pop(key, None)
    _save_state(state)


def upload_status(file_path, size, mtime):
    return upload_status_from_state(load_state(), file_path, size, mtime)


def upload_status_from_state(state, file_path, size, mtime):
    key = _key(file_path)
    completed = state.get("completed", {}).get(key)
    if completed and completed.get("size") == size and completed.get("mtime") == mtime:
        return "success"
    upload = state.get("uploads", {}).get(key, {})
    if upload.get("size") == size and upload.get("mtime") == mtime:
        return upload.get("status", "")
    return "new"


def already_completed(file_path, size, mtime):
    return upload_status(file_path, size, mtime) == "success"


def mark_uploading_in_state(state, file_path, size, mtime):
    state.setdefault("uploads", {})[_key(file_path)] = {"status": "uploading", "size": size, "mtime": mtime}


def mark_unknown_in_state(state, file_path, size, mtime, reason=""):
    state.setdefault("uploads", {})[_key(file_path)] = {"status": "unknown", "size": size, "mtime": mtime, "reason": reason}


def mark_completed_in_state(state, file_path, size, mtime):
    key = _key(file_path)
    state.setdefault("completed", {})[key] = {"size": size, "mtime": mtime}
    state.setdefault("uploads", {}).pop(key, None)
