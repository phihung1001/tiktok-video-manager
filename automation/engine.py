import json
import threading, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from datetime import datetime
from .browser import create_driver
from .seller_center import SellerCenter
from .validator import inspect_video
from .state import (
    load_config, load_state, mark_completed_in_state, mark_unknown_in_state,
    mark_uploading_in_state, save_state, upload_status_from_state,
)
from .paths import LOGS, PROJECT_ROOT

ROOT = PROJECT_ROOT

class AutomationEngine:
    def __init__(self, config, emit):
        self.config = config
        self.emit = emit
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self.pause_event.set()
        self.driver = None

    def pause(self):
        self.pause_event.clear()

    def resume(self):
        self.pause_event.set()

    def stop(self):
        self.stop_event.set()
        self.pause_event.set()

    def _wait_control(self):
        while not self.pause_event.is_set():
            if self.stop_event.is_set():
                raise RuntimeError("STOP_REQUESTED")
            time.sleep(.2)
        if self.stop_event.is_set():
            raise RuntimeError("STOP_REQUESTED")

    def _screenshot(self, name):
        try:
            LOGS.mkdir(exist_ok=True)
            stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            path = LOGS / f"{stamp}-{name}.png"
            self.driver.save_screenshot(str(path))
            return str(path)
        except Exception:
            return None

    def _clear_logs(self):
        """Start each session with a clean set of diagnostic screenshots."""
        try:
            LOGS.mkdir(exist_ok=True)
            for item in LOGS.iterdir():
                if item.is_file():
                    item.unlink()
        except Exception:
            # Failure to clean old diagnostics must not stop the upload session.
            pass

    def run(self):
        self._clear_logs()
        cfg_file = load_config()
        seller_url = cfg_file.get("seller_center_url", "https://seller-vn.tiktok.com/account/login")
        manage_url = cfg_file.get("video_manager_url", "https://seller-vn.tiktok.com/ads-creation/manage-analyze?mpa=1&reporting_type=video")
        folder = Path(self.config["folder"])

        videos = sorted(
            [p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in {".mp4",".mov",".mpeg",".avi"}],
            key=lambda p: p.name.lower()
        )
        self.emit({"type":"scan","total":len(videos)})
        if not videos:
            self.emit({"type":"error","message":"Không tìm thấy video trong thư mục."})
            self.emit({"type":"finished","stopped":False})
            return

        state = load_state()
        validation_cache = state.setdefault("validation_cache", {})
        rules_key = json.dumps(cfg_file.get("video_rules", {}), sort_keys=True, ensure_ascii=False)

        def inspect_cached(path):
            stat = path.stat()
            key = str(path.resolve())
            cached = validation_cache.get(key, {})
            if (
                cached.get("size") == stat.st_size and
                cached.get("mtime") == stat.st_mtime and
                cached.get("rules") == rules_key
            ):
                return path, cached.get("ok", False), cached.get("reason", ""), cached.get("meta")
            ok, reason, meta = inspect_video(path, cfg_file)
            validation_cache[key] = {
                "size": stat.st_size, "mtime": stat.st_mtime, "rules": rules_key,
                "ok": ok, "reason": reason, "meta": meta,
            }
            return path, ok, reason, meta

        worker_count = min(max(int(self.config.get("validation_workers", 4)), 1), 4, len(videos))
        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            validation_results = list(executor.map(inspect_cached, videos))
        save_state(state)

        queue = []
        pre_done = 0
        for p, ok, reason, meta in validation_results:
            self._wait_control()
            if not ok:
                pre_done += 1
                self.emit({"type":"result","file":p.name,"status":"invalid","message":f"Bỏ qua trước upload: {reason}"})
                self.emit({"type":"progress","done":pre_done,"total":len(videos),"percent":pre_done/len(videos)*100})
                continue
            status = upload_status_from_state(state, p, meta["size"], meta["mtime"])
            if status == "success":
                pre_done += 1
                self.emit({"type":"result","file":p.name,"status":"info","message":"Đã upload thành công ở phiên trước — bỏ qua."})
                self.emit({"type":"progress","done":pre_done,"total":len(videos),"percent":pre_done/len(videos)*100})
                continue
            if status in {"uploading", "unknown"}:
                pre_done += 1
                self.emit({"type":"result","file":p.name,"status":"error","message":"Trạng thái upload chưa xác định từ phiên trước — bỏ qua để tránh upload trùng."})
                self.emit({"type":"progress","done":pre_done,"total":len(videos),"percent":pre_done/len(videos)*100})
                continue
            queue.append((p, meta))

        if not queue:
            self.emit({"type":"finished","stopped":False})
            return

        try:
            self.driver = create_driver(ROOT)
            seller = SellerCenter(self.driver, self.emit, self._wait_control, bool(self.config.get("diagnostic_mode", False)))
            seller.open(seller_url)
            seller.ensure_logged_in()
            seller.open_video_manager(manage_url)

            done = pre_done
            batch_size = min(max(int(self.config.get("batch_size", 50)), 1), 50)
            batches = [queue[i:i + batch_size] for i in range(0, len(queue), batch_size)]
            for batch_number, batch in enumerate(batches, 1):
                self._wait_control()
                self.emit({"type":"info","message":f"Đang tải batch {batch_number}/{len(batches)}: {len(batch)} video"})
                try:
                    for p, meta in batch:
                        mark_uploading_in_state(state, p, meta["size"], meta["mtime"])
                    save_state(state)
                    statuses = seller.upload_many(
                        [p for p, _ in batch], self.config["account_name"],
                        self.config.get("product_name", ""), self.config.get("description", ""),
                        bool(self.config.get("public_profile", False)),
                        int(self.config.get("upload_timeout_seconds", 900)),
                        self.config.get("product_mode", "name"),
                        self.config.get("account_mode", "name")
                    )
                    for (p, meta), (status, msg) in zip(batch, statuses):
                        if status == "success":
                            mark_completed_in_state(state, p, meta["size"], meta["mtime"])
                        self.emit({"type":"result","file":p.name,"status":status,"message":msg})
                        done += 1
                        self.emit({"type":"progress","done":done,"total":len(videos),"percent":done/len(videos)*100})
                    save_state(state)
                except RuntimeError as e:
                    if str(e) == "STOP_REQUESTED":
                        break
                    raise
                except Exception as e:
                    screenshot = self._screenshot("error")
                    message = f"{type(e).__name__}: {e}. Đã chụp screenshot để xem trên màn hình tool."
                    for p, meta in batch:
                        mark_unknown_in_state(state, p, meta["size"], meta["mtime"], message)
                    save_state(state)
                    if screenshot:
                        self.emit({"type": "screenshot", "path": screenshot, "message": "Ảnh lỗi của batch"})
                    for p, _ in batch:
                        self.emit({"type":"result","file":p.name,"status":"error","message":message})
                    break

        except RuntimeError as e:
            if str(e) != "STOP_REQUESTED":
                self.emit({"type":"error","message":str(e)})
        except Exception as e:
            screenshot = self._screenshot("fatal")
            self.emit({"type":"error","message":f"{type(e).__name__}: {e}"})
            if screenshot:
                self.emit({"type": "screenshot", "path": screenshot, "message": "Ảnh lỗi nghiêm trọng"})
        finally:
            try:
                if self.driver:
                    self.driver.quit()
            except Exception:
                pass
            self.emit({"type":"finished","stopped":self.stop_event.is_set()})
