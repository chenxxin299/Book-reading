"""
batch_analyze.py
────────────────────────────────────────────────
并行分析多本书籍，最后统一生成门户。

用法：
  # 分析指定文件
  python batch_analyze.py 书A.epub 书B.pdf 书C.epub

  # 扫描目录下所有书籍
  python batch_analyze.py --dir books/

  # 控制并发数（默认 3，避免 API 限流）
  python batch_analyze.py --dir books/ --workers 5

  # 强制重新分析（忽略已有缓存）
  python batch_analyze.py --dir books/ --force

并发原理：
  每本书的 GPT 调用是网络 IO，用 ThreadPoolExecutor 并行发请求。
  GPT API 本身无状态，多线程安全。
  建议 workers=3~5，过高会触发 API rate limit。
"""

import sys
import argparse
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from loguru import logger

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

SUPPORTED_EXTS = {".epub", ".pdf"}


def collect_books(paths: list[str], book_dir: str | None) -> list[Path]:
    """收集所有待分析的书籍路径"""
    books = []

    # 从命令行指定的文件
    for p in paths:
        path = Path(p)
        if not path.exists():
            logger.warning(f"文件不存在，跳过: {p}")
            continue
        if path.suffix.lower() not in SUPPORTED_EXTS:
            logger.warning(f"不支持的格式，跳过: {p}")
            continue
        books.append(path)

    # 从目录扫描
    if book_dir:
        d = Path(book_dir)
        if not d.exists():
            logger.warning(f"目录不存在: {book_dir}")
        else:
            found = [p for p in d.iterdir() if p.suffix.lower() in SUPPORTED_EXTS]
            books.extend(found)
            logger.info(f"从 {d} 扫描到 {len(found)} 本书")

    # 去重（按绝对路径）
    seen = set()
    unique = []
    for b in books:
        key = b.resolve()
        if key not in seen:
            seen.add(key)
            unique.append(b)

    return unique


def analyze_one(book_path: Path, output_dir: str, force: bool) -> dict:
    """单本书分析任务，返回结果字典"""
    import reading_skill
    start = time.time()
    result = {"book": book_path.name, "status": "pending", "path": None, "elapsed": 0}
    try:
        report_path = reading_skill.run(str(book_path), output_dir, force=force)
        elapsed = time.time() - start
        result.update({"status": "ok", "path": report_path, "elapsed": elapsed})
        logger.success(f"✓ {book_path.name}  ({elapsed:.0f}s)")
    except Exception as e:
        elapsed = time.time() - start
        result.update({"status": "error", "error": str(e), "elapsed": elapsed})
        logger.error(f"✗ {book_path.name}  — {e}")
    return result


def run_batch(
    books: list[Path],
    output_dir: str = "output",
    workers: int = 3,
    force: bool = False,
) -> list[dict]:
    """并行分析，返回所有结果"""
    if not books:
        logger.info("没有找到待分析的书籍")
        return []

    logger.info(f"共 {len(books)} 本书，并发数 {workers}，开始分析...\n")
    total_start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(analyze_one, book, output_dir, force): book
            for book in books
        }
        for future in as_completed(futures):
            results.append(future.result())

    # 汇总
    ok = [r for r in results if r["status"] == "ok"]
    err = [r for r in results if r["status"] == "error"]
    total_elapsed = time.time() - total_start

    logger.info(f"\n{'─'*50}")
    logger.info(f"完成 {len(ok)}/{len(books)} 本  总耗时 {total_elapsed:.0f}s")
    if err:
        logger.warning("失败列表：")
        for r in err:
            logger.warning(f"  {r['book']}: {r.get('error', '未知错误')}")

    # 生成/更新门户
    if ok:
        logger.info("正在更新门户 index.html ...")
        try:
            import generate_portal
            generate_portal.generate(output_dir)
        except Exception as e:
            logger.error(f"门户更新失败: {e}")

    return results


# ── CLI ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="批量并行分析书籍")
    parser.add_argument("books", nargs="*", help="直接指定书籍文件路径")
    parser.add_argument("--dir",     "-d", default=None,   help="扫描目录（与直接指定可并用）")
    parser.add_argument("--output",  "-o", default="output", help="报告输出目录")
    parser.add_argument("--workers", "-w", type=int, default=3, help="并发线程数（默认 3）")
    parser.add_argument("--force",   "-f", action="store_true", help="强制重新分析（忽略缓存）")
    parser.add_argument("--verbose", "-v", action="store_true", help="显示详细日志")
    args = parser.parse_args()

    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG" if args.verbose else "INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
        colorize=True,
    )

    books = collect_books(args.books, args.dir)
    if not books:
        logger.error("没有找到任何可分析的书籍文件，退出")
        sys.exit(1)

    logger.info("待分析书目：")
    for b in books:
        logger.info(f"  {b.name}")
    logger.info("")

    run_batch(books, args.output, args.workers, args.force)
