"""
单 Chunk 分析器 - 含断点续跑缓存
"""
import json
from pathlib import Path

import diskcache
from loguru import logger

from chunker.models import Chunk
from .claude_client import ClaudeClient
from .models import ChunkAnalysis, ConceptItem
from .prompts import CHUNK_ANALYSIS_SYSTEM, make_chunk_user_prompt


class ChunkAnalyzer:
    def __init__(
        self,
        client: ClaudeClient,
        cache_dir: str = "cache",
        cache_enabled: bool = True,
    ):
        self.client = client
        self.cache_enabled = cache_enabled
        self._disk_cache = diskcache.Cache(cache_dir) if cache_enabled else None

    def analyze(self, chunk: Chunk) -> ChunkAnalysis:
        """分析单个 Chunk，支持断点续跑"""
        cache_key = f"chunk:{chunk.chunk_id}"

        # 检查磁盘缓存
        if self.cache_enabled and cache_key in self._disk_cache:
            logger.info(f"[缓存命中] 章节 {chunk.chapter_index + 1} 片段 {chunk.sub_chunk_index + 1}")
            raw = self._disk_cache[cache_key]
            return self._parse_result(chunk, raw)

        logger.info(
            f"[分析中] 《{chunk.book_title}》 "
            f"第 {chunk.chapter_index + 1} 章《{chunk.chapter_title}》"
            f"（片段 {chunk.sub_chunk_index + 1}/{chunk.total_sub_chunks}）"
        )

        user_prompt = make_chunk_user_prompt(chunk.context_header, chunk.content)
        raw = self.client.call(
            system_prompt=CHUNK_ANALYSIS_SYSTEM,
            user_content=user_prompt,
            expect_json=True,
        )

        # 写入磁盘缓存
        if self.cache_enabled:
            self._disk_cache[cache_key] = raw

        return self._parse_result(chunk, raw)

    def _parse_result(self, chunk: Chunk, raw: dict) -> ChunkAnalysis:
        concepts = []
        for c in raw.get("key_concepts", []):
            if isinstance(c, dict):
                concepts.append(ConceptItem(
                    name=c.get("name", ""),
                    explanation=c.get("explanation", ""),
                    importance=int(c.get("importance", 3)),
                ))

        return ChunkAnalysis(
            chunk_id=chunk.chunk_id,
            chapter_index=chunk.chapter_index,
            chapter_title=chunk.chapter_title,
            sub_chunk_index=chunk.sub_chunk_index,
            chapter_summary=raw.get("chapter_summary", ""),
            key_concepts=concepts,
            key_arguments=raw.get("key_arguments", []),
            questions=raw.get("questions", []),
            insights=raw.get("insights", []),
            keywords=raw.get("keywords", []),
            raw=raw,
        )
