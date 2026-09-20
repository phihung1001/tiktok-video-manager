import json, subprocess
from pathlib import Path

DEFAULT_RULES = {
    "max_file_size_mb": 500,
    "min_duration_seconds": 5,
    "max_duration_seconds": 600,
    "aspect_tolerance": 0.005,
    "supported_extensions": [".mp4", ".mov", ".mpeg", ".avi"],
}

def inspect_video(file_path: Path, config=None):
    try:
        rules = {**DEFAULT_RULES, **(config or {}).get("video_rules", {})}
        extensions = {str(value).lower() for value in rules["supported_extensions"]}
        stat = file_path.stat()
        if file_path.suffix.lower() not in extensions:
            return False, f"Định dạng {file_path.suffix} không hỗ trợ", None
        max_size = float(rules["max_file_size_mb"])
        if stat.st_size > max_size * 1024 * 1024:
            return False, f"Video vượt quá {max_size:g} MB", None

        p = subprocess.run([
            "ffprobe", "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=width,height,duration,codec_name",
            "-of", "json", str(file_path)
        ], capture_output=True, text=True, check=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        stream = json.loads(p.stdout).get("streams", [{}])[0]
        w, h = int(stream.get("width", 0)), int(stream.get("height", 0))
        duration = float(stream.get("duration") or 0)
        if not w or not h:
            return False, "Không đọc được kích thước video", None
        min_duration = float(rules["min_duration_seconds"])
        max_duration = float(rules["max_duration_seconds"])
        if duration < min_duration or duration > max_duration:
            return False, f"Thời lượng {duration:.1f}s; quy tắc hiện tại là từ {min_duration:g}s đến {max_duration:g}s", None

        ratio = w / h
        allowed = (16/9, 1, 9/16)
        if not any(abs(ratio-x)/x <= float(rules["aspect_tolerance"]) for x in allowed):
            return False, f"Sai tỷ lệ {w}x{h}; chỉ nhận 16:9, 1:1, 9:16", None

        return True, "OK", {
            "width": w, "height": h, "size": stat.st_size,
            "mtime": stat.st_mtime, "duration": duration,
            "codec": stream.get("codec_name")
        }
    except FileNotFoundError:
        return False, "Không tìm thấy ffprobe trong PATH", None
    except Exception as e:
        return False, f"ffprobe lỗi: {e}", None
