"""
主流水线调度器 - 串联所有模块，支持断点续跑
"""
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional

from loguru import logger
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from parsers import parse_book
from chunker import HybridChunker
from analyzer import ClaudeClient, ChunkAnalyzer, BookAnalyzer
from aggregator import ResultMerger
from reporter import MarkdownWriter


class Pipeline:
    def __init__(
        self,
        model: str = "claude-opus-4-6",
        max_tokens_per_chunk: int = 6000,
        overlap_tokens: int = 500,
        cache_dir: str = "cache",
        cache_enabled: bool = True,
        output_dir: str = "output",
        max_concurrent: int = 3,
    ):
        self.claude = ClaudeClient(model=model, max_tokens=4096)
        self.chunker = HybridChunker(
            max_tokens=max_tokens_per_chunk,
            overlap_tokens=overlap_tokens,
        )
        self.chunk_analyzer = ChunkAnalyzer(
            client=self.claude,
            cache_dir=cache_dir,
            cache_enabled=cache_enabled,
        )
        self.book_analyzer = BookAnalyzer(client=self.claude)
        self.merger = ResultMerger()
        self.writer = MarkdownWriter(output_dir=output_dir)
        self.max_concurrent = max_concurrent
        self.model = model

    def run(self, file_path: str) -> Path:
        """
        运行完整的读书工作流，返回报告文件路径。

        步骤：
        1. 解析书籍（PDF/EPUB → ParsedBook）
        2. 分块（ParsedBook → List[Chunk]）
        3. 逐块分析（含并发 + 断点续跑）
        4. 全书综合分析
        5. 生成 Markdown 报告
        """
        logger.info(f"=== 开始处理：{file_path} ===")

        # Step 1: 解析
        logger.info("[1/5] 解析书籍...")
        book = parse_book(file_path)
        logger.success(
            f"解析完成：《{book.title}》 | 作者：{book.author} | "
            f"章节数：{book.total_chapters} | 总字符：{book.total_chars:,}"
        )

        # Step 2: 分块
        logger.info("[2/5] 智能分块...")
        chunks = self.chunker.chunk_book(book)
        logger.success(f"分块完成：共 {len(chunks)} 个片段")

        # Step 3: 逐块分析（并发 + 进度条）
        logger.info(f"[3/5] 逐块分析（并发数：{self.max_concurrent}）...")
        chunk_analyses = self._analyze_chunks_concurrent(chunks)
        logger.success(f"逐块分析完成：{len(chunk_analyses)} 个片段")

        # Step 4: 全书综合分析
        logger.info("[4/5] 全书综合分析...")
        book_analysis = self.book_analyzer.analyze(book, chunk_analyses)
        logger.success("全书综合分析完成")

        # Step 5: 生成报告
        logger.info("[5/5] 生成 Markdown 报告...")
        report_path = self.writer.write(book_analysis, model_name=self.model)

        logger.success(f"=== 完成！报告已保存至：{report_path} ===")
        return report_path

    # ── 内部方法 ─────────────────────────────────────────────────────────────

    def _analyze_chunks_concurrent(self, chunks):
        """并发分析多个 chunk，带进度条"""
        results = [None] * len(chunks)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
            TimeElapsedColumn(),
        ) as progress:
            task = progress.add_task("分析章节片段", total=len(chunks))

            with ThreadPoolExecutor(max_workers=self.max_concurrent) as executor:
                future_to_idx = {
                    executor.submit(self.chunk_analyzer.analyze, chunk): i
                    for i, chunk in enumerate(chunks)
                }
                for future in as_completed(future_to_idx):
                    idx = future_to_idx[future]
                    try:
                        results[idx] = future.result()
                    except Exception as e:
                        logger.error(f"片段 {idx} 分析失败: {e}")
                        # 创建一个空的分析结果以防止整体失败
                        from analyzer.models import ChunkAnalysis
                        results[idx] = ChunkAnalysis(
                            chunk_id=chunks[idx].chunk_id,
                            chapter_index=chunks[idx].chapter_index,
                            chapter_title=chunks[idx].chapter_title,
                            sub_chunk_index=chunks[idx].sub_chunk_index,
                            chapter_summary=f"（分析失败：{str(e)[:50]}）",
                        )
                    progress.advance(task)

        return [r for r in results if r is not None]
