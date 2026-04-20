"""
auto_analyze.py
────────────────────────────────────────────────
自动监控"书本"目录，发现新书后自动分析并推送到 GitHub。

用法：
  python auto_analyze.py              # 启动自动监控
  python auto_analyze.py --once       # 扫描一次后退出
  python auto_analyze.py --no-deploy  # 分析后不自动推送

工作流程：
  1. 扫描"书本"目录，找出所有 epub/pdf
  2. 过滤掉已分析过的书（检查 output/ 是否已有对应报告）
  3. 并发分析新书（最多 5 本同时进行）
  4. 分析完成后自动推送到 GitHub Pages

注意：
  - 不会重复分析同一本书（除非删除 output/ 中的报告）
  - 并发数固定为 5（避免 API 限流）
  - 推送需要配置 .env 中的 GITHUB_REPO
"""

import sys
import time
import argparse
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

BOOKS_DIR = "书本"
OUTPUT_DIR = "output"
SUPPORTED_EXTS = {".epub", ".pdf"}
MAX_WORKERS = 5  # 固定并发数


def collect_new_books(books_dir: str, output_dir: str) -> list[Path]:
    """收集未分析的新书"""
    import reading_skill

    bd = Path(books_dir)
    if not bd.exists():
        logger.warning(f"书本目录不存在: {bd.resolve()}")
        bd.mkdir(parents=True, exist_ok=True)
        return []

    all_books = [p for p in bd.iterdir() if p.suffix.lower() in SUPPORTED_EXTS]

    # 过滤掉已分析的
    new_books = []
    for book in all_books:
        if not reading_skill.is_already_analyzed(str(book), output_dir):
            new_books.append(book)
        else:
            logger.debug(f"已分析，跳过: {book.name}")

    return new_books


def analyze_one(book_path: Path, output_dir: str) -> dict:
    """分析单本书"""
    import reading_skill
    start = time.time()
    result = {"book": book_path.name, "status": "pending", "path": None, "elapsed": 0}
    try:
        report_path = reading_skill.run(str(book_path), output_dir, force=False)
        elapsed = time.time() - start
        result.update({"status": "ok", "path": report_path, "elapsed": elapsed})
        logger.success(f"✓ {book_path.name}  ({elapsed:.0f}s)")
    except Exception as e:
        elapsed = time.time() - start
        result.update({"status": "error", "error": str(e), "elapsed": elapsed})
        logger.error(f"✗ {book_path.name}  — {e}")
    return result


def run_auto_analysis(books_dir: str, output_dir: str, auto_deploy: bool = True) -> bool:
    """
    自动分析流程。
    返回 True 表示有新书被分析，False 表示没有新书。
    """
    logger.info(f"扫描目录: {Path(books_dir).resolve()}")
    new_books = collect_new_books(books_dir, output_dir)

    if not new_books:
        logger.info("没有发现新书，无需分析")
        return False

    logger.info(f"发现 {len(new_books)} 本新书，开始并发分析（最多 {MAX_WORKERS} 本同时进行）...\n")
    for b in new_books:
        logger.info(f"  📖 {b.name}")
    logger.info("")

    total_start = time.time()
    results = []

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
        futures = {
            pool.submit(analyze_one, book, output_dir): book
            for book in new_books
        }
        for future in as_completed(futures):
            results.append(future.result())

    # 汇总
    ok = [r for r in results if r["status"] == "ok"]
    err = [r for r in results if r["status"] == "error"]
    total_elapsed = time.time() - total_start

    logger.info(f"\n{'─'*50}")
    logger.info(f"完成 {len(ok)}/{len(new_books)} 本  总耗时 {total_elapsed:.0f}s")
    if err:
        logger.warning("失败列表：")
        for r in err:
            logger.warning(f"  {r['book']}: {r.get('error', '未知错误')}")

    # 更新门户
    if ok:
        logger.info("正在更新门户 index.html ...")
        try:
            import generate_portal
            generate_portal.generate(output_dir)
        except Exception as e:
            logger.error(f"门户更新失败: {e}")

        # 更新知识图谱
        logger.info("正在更新知识图谱 ...")
        try:
            import knowledge_graph
            import generate_themes_page
            import generate_concepts_page
            import generate_graph_page

            knowledge_graph.build_knowledge_graph(output_dir)
            generate_themes_page.generate_themes_page(output_dir)
            generate_concepts_page.generate_concepts_page(output_dir)
            generate_graph_page.generate_graph_page(output_dir)
        except Exception as e:
            logger.error(f"知识图谱更新失败: {e}")

        # 自动推送到 GitHub
        if auto_deploy:
            logger.info("\n正在推送到 GitHub Pages ...")
            try:
                import deploy
                deploy.deploy(output_dir, commit_message=f"📚 新增 {len(ok)} 本书")
            except Exception as e:
                logger.error(f"推送失败: {e}")
                logger.info("你可以稍后手动运行: python deploy.py")

    return len(ok) > 0


def watch_mode(books_dir: str, output_dir: str, auto_deploy: bool = True):
    """持续监控模式（每 5 分钟扫描一次）"""
    logger.info('[自动监控模式] 每 5 分钟扫描一次"书本"目录')
    logger.info(f"书本目录: {Path(books_dir).resolve()}")
    logger.info(f"报告输出: {Path(output_dir).resolve()}")
    logger.info("按 Ctrl+C 停止\n")

    try:
        while True:
            run_auto_analysis(books_dir, output_dir, auto_deploy)
            logger.info("\n等待 5 分钟后再次扫描...\n")
            time.sleep(300)  # 5 分钟
    except KeyboardInterrupt:
        logger.info("\n[自动监控] 已停止")


# ── CLI ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='自动分析"书本"目录中的新书')
    parser.add_argument("--books-dir",  "-b", default=BOOKS_DIR,  help=f"书本目录（默认 {BOOKS_DIR}/）")
    parser.add_argument("--output-dir", "-o", default=OUTPUT_DIR, help=f"报告输出目录（默认 {OUTPUT_DIR}/）")
    parser.add_argument("--once",             action="store_true", help="扫描一次后退出（不持续监控）")
    parser.add_argument("--no-deploy",        action="store_true", help="分析后不自动推送到 GitHub")
    parser.add_argument("--verbose",    "-v", action="store_true", help="显示详细日志")
    args = parser.parse_args()

    logger.remove()
    logger.add(
        sys.stderr,
        level="DEBUG" if args.verbose else "INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
        colorize=True,
    )

    auto_deploy = not args.no_deploy

    if args.once:
        logger.info("[一次性扫描模式]")
        has_new = run_auto_analysis(args.books_dir, args.output_dir, auto_deploy)
        if has_new:
            logger.info("\n✅ 分析完成")
        else:
            logger.info("\n✅ 无新书需要分析")
    else:
        watch_mode(args.books_dir, args.output_dir, auto_deploy)
