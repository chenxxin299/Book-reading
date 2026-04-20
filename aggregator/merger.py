"""
结果聚合器 - 合并多章分析，去重概念
"""
from collections import defaultdict

from analyzer.models import BookAnalysis, ChunkAnalysis, ConceptItem


class ResultMerger:
    """合并和去重多个 ChunkAnalysis 的结果"""

    def dedupe_concepts(self, concepts: list[ConceptItem], top_n: int = 8) -> list[ConceptItem]:
        """按概念名称去重，保留 importance 最高的版本，取 top_n"""
        seen: dict[str, ConceptItem] = {}
        for c in concepts:
            key = c.name.strip().lower()
            if key not in seen or c.importance > seen[key].importance:
                seen[key] = c
        # 按重要性排序
        return sorted(seen.values(), key=lambda x: x.importance, reverse=True)[:top_n]

    def merge_keywords(self, analyses: list[ChunkAnalysis], top_n: int = 20) -> list[str]:
        """统计关键词频率，返回 top_n"""
        freq: dict[str, int] = defaultdict(int)
        for a in analyses:
            for kw in a.keywords:
                freq[kw.strip()] += 1
        return [kw for kw, _ in sorted(freq.items(), key=lambda x: x[1], reverse=True)][:top_n]

    def collect_all_questions(self, analyses: list[ChunkAnalysis]) -> list[str]:
        """收集所有章节的关键问题（去重）"""
        seen = set()
        questions = []
        for a in analyses:
            for q in a.questions:
                if q.strip() not in seen:
                    seen.add(q.strip())
                    questions.append(q)
        return questions[:10]  # 最多返回 10 个

    def collect_all_insights(self, analyses: list[ChunkAnalysis]) -> list[str]:
        """收集所有章节的启发（去重）"""
        seen = set()
        insights = []
        for a in analyses:
            for ins in a.insights:
                if ins.strip() not in seen:
                    seen.add(ins.strip())
                    insights.append(ins)
        return insights[:12]
