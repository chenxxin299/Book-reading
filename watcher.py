"""
watcher.py
────────────────────────────────────────────────
监控 books/ 目录，自动分析新增的 epub/pdf 书籍，
并在每次分析完成后重新生成门户 index.html。

用法：
  python watcher.py                     # 监控 ./books/，输出到 ./output/
  python watcher.py --books-dir books --output-dir output
  python watcher.py --once              # 扫描一次后退出（适合 cron/CI）

依赖：
  pip install watchdog loguru
"""

import os
import sys
import time
import argparse
import threading
from pathlib import Path
from datetime import datetime

from loguru import logger

# Windows 控制台 UTF-8 输出
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# 延迟导入（确保 .env 先加载）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# ── 配置 ──────────────────────────────────────────────────
SUPPORTED_EXTS = {".epub", ".pdf"}
DEBOUNCE_SEC   = 3      # 等待文件写入完成后再处理（秒）

# ── 分析单本书 ───────────────────────────────────────────
def analyze_one(book_path: str, output_dir: str) -> bool:
    """调用 reading_skill.run()，返回是否成功"""
    try:
        import reading_skill
        report = reading_skill.run(book_path, output_dir)
        logger.success(f"分析完成: {book_path} → {report}")
        return True
    except Exception as e:
        logger.error(f"分析失败: {book_path} — {e}")
        return False


# ── 更新门户 ─────────────────────────────────────────────
def refresh_portal(output_dir: str):
    try:
        import generate_portal
        generate_portal.generate(output_dir)
    except Exception as e:
        logger.error(f"门户更新失败: {e}")


# ── 扫描全量（启动时 / --once 模式）──────────────────────
def scan_all(books_dir: str, output_dir: str):
    bd = Path(books_dir)
    if not bd.exists():
        logger.warning(f"books 目录不存在，将自动创建: {bd.resolve()}")
        bd.mkdir(parents=True, exist_ok=True)

    files = [p for p in bd.iterdir() if p.suffix.lower() in SUPPORTED_EXTS]
    if not files:
        logger.info("books/ 目录为空，等待新书籍投入...")
        return

    logger.info(f"发现 {len(files)} 本书，开始批量分析...")
    any_new = False
    for f in files:
        ok = analyze_one(str(f), output_dir)
        if ok:
            any_new = True

    if any_new:
        refresh_portal(output_dir)


# ── watchdog 事件处理器 ───────────────────────────────────
class BookHandler:
    def __init__(self, output_dir: str):
        self.output_dir = output_dir
        self._timers: dict[str, threading.Timer] = {}

    def _schedule(self, path: str):
        """防抖：文件稳定后再处理"""
        if path in self._timers:
            self._timers[path].cancel()

        t = threading.Timer(DEBOUNCE_SEC, self._process, args=(path,))
        self._timers[path] = t
        t.start()

    def _process(self, path: str):
        self._timers.pop(path, None)
        ext = Path(path).suffix.lower()
        if ext not in SUPPORTED_EXTS:
            return
        logger.info(f"检测到新书籍: {Path(path).name}")
        ok = analyze_one(path, self.output_dir)
        if ok:
            refresh_portal(self.output_dir)

    # watchdog 回调
    def on_created(self, event):
        if not event.is_directory:
            self._schedule(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._schedule(event.dest_path)


# ── 启动监控 ─────────────────────────────────────────────
def start_watching(books_dir: str, output_dir: str):
    try:
        from watchdog.observers import Observer
        from watchdog.events import FileSystemEventHandler
    except ImportError:
        logger.error("请先安装 watchdog: pip install watchdog")
        sys.exit(1)

    # 确保目录存在
    Path(books_dir).mkdir(parents=True, exist_ok=True)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    handler_obj = BookHandler(output_dir)

    # 适配 watchdog 事件接口
    class _WatchdogAdapter(FileSystemEventHandler):
        def on_created(self, event): handler_obj.on_created(event)
        def on_moved(self, event):   handler_obj.on_moved(event)

    observer = Observer()
    observer.schedule(_WatchdogAdapter(), path=books_dir, recursive=False)
    observer.start()

    logger.info(f"[watcher] 已启动，监控目录: {Path(books_dir).resolve()}")
    logger.info(f"[watcher] 报告输出到:   {Path(output_dir).resolve()}")
    logger.info("[watcher] 按 Ctrl+C 停止\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("[watcher] 已停止")

    observer.join()


# ── CLI ─────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="书籍自动分析守护进程")
    parser.add_argument("--books-dir",  "-b", default="books",  help="监控的书籍目录（默认 books/）")
    parser.add_argument("--output-dir", "-o", default="output", help="报告输出目录（默认 output/）")
    parser.add_argument("--once",             action="store_true",
                        help="扫描一次现有书籍后退出（不持续监控）")
    parser.add_argument("--verbose",    "-v", action="store_true", help="显示详细日志")
    args = parser.parse_args()

    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG" if args.verbose else "INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
        colorize=True,
    )

    if args.once:
        logger.info("[watcher] 一次性扫描模式")
        scan_all(args.books_dir, args.output_dir)
        logger.info("[watcher] 扫描完成，退出")
    else:
        # 先扫描存量书籍
        scan_all(args.books_dir, args.output_dir)
        # 再持续监控
        start_watching(args.books_dir, args.output_dir)
