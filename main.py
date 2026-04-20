"""
AI 读书工作流 - CLI 入口

用法：
    python main.py analyze mybook.pdf
    python main.py analyze mybook.epub --model claude-haiku-4-5 --fast
"""
import sys
from pathlib import Path

import click
import yaml
from dotenv import load_dotenv
from loguru import logger
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

# 加载环境变量
load_dotenv()

console = Console()


def load_config(config_path: str = "config.yaml") -> dict:
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}


def setup_logger(verbose: bool):
    logger.remove()
    level = "DEBUG" if verbose else "INFO"
    logger.add(
        sys.stderr,
        level=level,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
        colorize=True,
    )


@click.group()
def cli():
    """📚 AI 读书工作流 - 自动解析、分析并生成深度读书报告"""
    pass


@cli.command()
@click.argument("book_file", type=click.Path(exists=True))
@click.option("--model", default=None, help="Claude 模型（默认使用 config.yaml 设置）")
@click.option("--fast", is_flag=True, help="快速模式：使用 claude-haiku-4-5")
@click.option("--chunk-size", default=None, type=int, help="每块最大 token 数（默认 6000）")
@click.option("--concurrent", default=None, type=int, help="并发分析数（默认 3）")
@click.option("--no-cache", is_flag=True, help="禁用断点续跑缓存")
@click.option("--output-dir", default=None, help="报告输出目录（默认 output/）")
@click.option("--verbose", "-v", is_flag=True, help="显示详细日志")
def analyze(
    book_file: str,
    model: str,
    fast: bool,
    chunk_size: int,
    concurrent: int,
    no_cache: bool,
    output_dir: str,
    verbose: bool,
):
    """分析书籍并生成深度读书报告。

    BOOK_FILE: PDF 或 EPUB 文件路径

    示例：\n
        python main.py analyze 《原则》.pdf\n
        python main.py analyze book.epub --fast --no-cache
    """
    setup_logger(verbose)
    cfg = load_config()

    # 解析参数（CLI 优先于 config.yaml）
    if fast:
        final_model = "claude-haiku-4-5"
    elif model:
        final_model = model
    else:
        final_model = cfg.get("model", {}).get("chunk_analysis", "claude-opus-4-6")

    final_chunk_size = chunk_size or cfg.get("chunker", {}).get("max_tokens_per_chunk", 6000)
    final_concurrent = concurrent or cfg.get("concurrency", {}).get("max_concurrent_chunks", 3)
    final_output_dir = output_dir or cfg.get("output", {}).get("dir", "output")
    cache_enabled = not no_cache and cfg.get("cache", {}).get("enabled", True)
    cache_dir = cfg.get("cache", {}).get("dir", "cache")
    overlap_tokens = cfg.get("chunker", {}).get("overlap_tokens", 500)

    # 显示配置信息
    book_path = Path(book_file)
    console.print(Panel(
        Text.assemble(
            ("📖 文件：", "bold"), (book_path.name, "cyan"), "\n",
            ("🤖 模型：", "bold"), (final_model, "cyan"), "\n",
            ("📦 块大小：", "bold"), (f"{final_chunk_size} tokens", "cyan"), "\n",
            ("⚡ 并发数：", "bold"), (str(final_concurrent), "cyan"), "\n",
            ("💾 断点续跑：", "bold"), ("启用" if cache_enabled else "禁用", "green" if cache_enabled else "red"),
        ),
        title="AI 读书工作流",
        border_style="blue",
    ))

    # 检查 API Key（兼容 ANTHROPIC_API_KEY 和 ANTHROPIC_AUTH_TOKEN 两种变量名）
    import os
    if not os.getenv("ANTHROPIC_API_KEY") and not os.getenv("ANTHROPIC_AUTH_TOKEN"):
        console.print("[red]❌ 错误：未设置 ANTHROPIC_API_KEY 环境变量[/red]")
        console.print("请复制 .env.example 为 .env 并填入你的 API Key")
        sys.exit(1)

    # 运行工作流
    from core.pipeline import Pipeline

    pipeline = Pipeline(
        model=final_model,
        max_tokens_per_chunk=final_chunk_size,
        overlap_tokens=overlap_tokens,
        cache_dir=cache_dir,
        cache_enabled=cache_enabled,
        output_dir=final_output_dir,
        max_concurrent=final_concurrent,
    )

    try:
        report_path = pipeline.run(book_file)
        console.print(f"\n[bold green]✅ 报告已生成：{report_path}[/bold green]")
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️ 用户中断。已完成的章节分析已缓存，下次运行将从中断处继续。[/yellow]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]❌ 错误：{e}[/red]")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


@cli.command()
@click.argument("cache_dir", default="cache")
def clear_cache(cache_dir: str):
    """清除断点续跑缓存"""
    import diskcache
    setup_logger(False)
    cache = diskcache.Cache(cache_dir)
    size = len(cache)
    cache.clear()
    console.print(f"[green]✅ 已清除 {size} 条缓存记录[/green]")


@cli.command()
def info():
    """显示工具信息和支持格式"""
    console.print(Panel(
        "支持格式：[cyan]PDF[/cyan]、[cyan]EPUB[/cyan]\n"
        "输出内容：全书主题 | 章节概要 | 思维导图 | 关键概念 | 关键问题 | 启发应用\n"
        "核心特性：Prompt Caching（降低 API 成本）| 断点续跑 | 并发分析",
        title="AI 读书工作流",
        border_style="blue",
    ))


if __name__ == "__main__":
    cli()
