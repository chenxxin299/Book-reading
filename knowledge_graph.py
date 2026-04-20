"""
knowledge_graph.py
────────────────────────────────────────────────
从 HTML 报告中提取结构化数据，构建跨书知识图谱。

功能：
1. 从 HTML 提取核心概念、主题、观点、金句
2. 聚合所有书籍，构建概念索引、主题索引
3. 生成知识图谱数据（用于可视化）

用法：
  python knowledge_graph.py --build          # 构建知识图谱
  python knowledge_graph.py --stats          # 显示统计信息
"""

import sys
import json
import re
from pathlib import Path
from collections import defaultdict
from bs4 import BeautifulSoup

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from loguru import logger


def extract_index_from_html(html_path: Path) -> dict:
    """从 HTML 报告中提取结构化索引"""
    html = html_path.read_text(encoding='utf-8')
    soup = BeautifulSoup(html, 'html.parser')

    # 提取书名和作者
    book_title = soup.find('h1')
    book_title = book_title.text.strip() if book_title else html_path.stem

    # 提取核心概念（从 concept-box）
    concepts = []
    for box in soup.find_all('div', class_='concept-box'):
        title_elem = box.find('div', class_='concept-title')
        if title_elem:
            concept_name = title_elem.text.strip()
            # 去除编号（如 "1. 概念" → "概念"）
            concept_name = re.sub(r'^\d+\.?\s*', '', concept_name)

            # 提取概念描述（ul/li 或 p）
            desc_parts = []
            for li in box.find_all('li'):
                desc_parts.append(li.text.strip())
            for p in box.find_all('p'):
                desc_parts.append(p.text.strip())

            concepts.append({
                'name': concept_name,
                'description': ' '.join(desc_parts[:2]) if desc_parts else '',  # 取前两点
                'importance': 'high' if len(desc_parts) > 3 else 'medium'
            })

    # 提取主题（仅从标签提取，过滤掉问题式标题）
    themes = set()
    # 从 tag 提取
    for tag in soup.find_all('span', class_='tag'):
        theme_text = tag.text.strip()
        # 过滤掉问题式文本（包含"？"或以数字开头的长文本）
        if '？' not in theme_text and '?' not in theme_text:
            # 去除数字编号
            theme_text = re.sub(r'^\d+\.?\s*', '', theme_text)
            # 只保留简短的主题词（长度 2-15 字符）
            if 2 <= len(theme_text) <= 15:
                themes.add(theme_text)

    # 提取核心观点（从 card-accent）
    viewpoints = []
    for card in soup.find_all('div', class_='card-accent'):
        h3 = card.find('h3')
        if h3:
            viewpoint_title = h3.text.strip()
            # 提取观点内容
            points = []
            for li in card.find_all('li'):
                points.append(li.text.strip())

            viewpoints.append({
                'title': viewpoint_title,
                'points': points[:3]  # 取前3点
            })

    # 提取金句（从 quote）
    quotes = []
    for quote_elem in soup.find_all('div', class_='quote'):
        p = quote_elem.find('p')
        source = quote_elem.find('div', class_='source')
        if p:
            quotes.append({
                'text': p.text.strip(),
                'source': source.text.strip() if source else ''
            })

    # 提取关键词（从概念名称 + 主题）
    keywords = list(set([c['name'] for c in concepts] + list(themes)))

    return {
        'book_id': html_path.stem,
        'book_title': book_title,
        'concepts': concepts,
        'themes': list(themes),
        'viewpoints': viewpoints,
        'quotes': quotes[:10],  # 限制10条
        'keywords': keywords
    }


def build_knowledge_graph(output_dir: str = 'output') -> dict:
    """扫描所有 HTML，构建知识图谱"""
    output_path = Path(output_dir)

    # 收集所有书籍的索引
    all_books = []
    for html_file in output_path.glob('*.html'):
        if html_file.name == 'index.html':
            continue

        logger.info(f"提取索引: {html_file.name}")
        try:
            index = extract_index_from_html(html_file)
            all_books.append(index)

            # 保存单本书的索引
            index_file = html_file.with_suffix('.json').with_name(html_file.stem + '_index.json')
            index_file.write_text(json.dumps(index, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception as e:
            logger.error(f"提取失败 {html_file.name}: {e}")

    logger.info(f"共提取 {len(all_books)} 本书的索引")

    # 构建概念索引
    concepts_map = defaultdict(lambda: {'books': [], 'definitions': {}, 'frequency': 0})
    for book in all_books:
        for concept in book['concepts']:
            name = concept['name']
            concepts_map[name]['books'].append(book['book_title'])
            concepts_map[name]['definitions'][book['book_title']] = concept['description']
            concepts_map[name]['frequency'] += 1

    # 构建主题索引
    themes_map = defaultdict(lambda: {'books': [], 'concepts': set(), 'frequency': 0})
    for book in all_books:
        for theme in book['themes']:
            themes_map[theme]['books'].append(book['book_title'])
            themes_map[theme]['concepts'].update([c['name'] for c in book['concepts']])
            themes_map[theme]['frequency'] += 1

    # 转换 set 为 list（JSON 序列化）
    for theme in themes_map:
        themes_map[theme]['concepts'] = list(themes_map[theme]['concepts'])

    # 构建图谱数据（用于可视化）
    graph_data = {
        'nodes': [],
        'links': []
    }

    # 添加书籍节点
    for book in all_books:
        graph_data['nodes'].append({
            'id': book['book_id'],
            'name': book['book_title'],
            'type': 'book',
            'size': len(book['concepts']) + len(book['themes'])
        })

    # 添加概念节点和连接
    for concept_name, data in concepts_map.items():
        if data['frequency'] >= 2:  # 只显示出现2次以上的概念
            graph_data['nodes'].append({
                'id': f'concept_{concept_name}',
                'name': concept_name,
                'type': 'concept',
                'size': data['frequency'] * 10
            })

            for book_title in data['books']:
                # 找到对应的 book_id
                book_id = next((b['book_id'] for b in all_books if b['book_title'] == book_title), None)
                if book_id:
                    graph_data['links'].append({
                        'source': book_id,
                        'target': f'concept_{concept_name}'
                    })

    # 保存聚合索引
    (output_path / 'concepts_index.json').write_text(
        json.dumps(dict(concepts_map), ensure_ascii=False, indent=2), encoding='utf-8'
    )
    (output_path / 'themes_index.json').write_text(
        json.dumps(dict(themes_map), ensure_ascii=False, indent=2), encoding='utf-8'
    )
    (output_path / 'graph_data.json').write_text(
        json.dumps(graph_data, ensure_ascii=False, indent=2), encoding='utf-8'
    )

    logger.success(f"知识图谱构建完成:")
    logger.info(f"  - 概念: {len(concepts_map)} 个")
    logger.info(f"  - 主题: {len(themes_map)} 个")
    logger.info(f"  - 图谱节点: {len(graph_data['nodes'])} 个")
    logger.info(f"  - 图谱连接: {len(graph_data['links'])} 条")

    return {
        'concepts': dict(concepts_map),
        'themes': dict(themes_map),
        'graph': graph_data
    }


def show_stats(output_dir: str = 'output'):
    """显示知识图谱统计信息"""
    output_path = Path(output_dir)

    concepts_file = output_path / 'concepts_index.json'
    themes_file = output_path / 'themes_index.json'

    if not concepts_file.exists():
        logger.error("知识图谱未构建，请先运行: python knowledge_graph.py --build")
        return

    concepts = json.loads(concepts_file.read_text(encoding='utf-8'))
    themes = json.loads(themes_file.read_text(encoding='utf-8'))

    print("\n" + "="*50)
    print("📊 知识图谱统计")
    print("="*50)

    print(f"\n总概念数: {len(concepts)}")
    print("\n高频概念 Top 10:")
    sorted_concepts = sorted(concepts.items(), key=lambda x: x[1]['frequency'], reverse=True)
    for i, (name, data) in enumerate(sorted_concepts[:10], 1):
        print(f"  {i}. {name} — 出现 {data['frequency']} 次")

    print(f"\n总主题数: {len(themes)}")
    print("\n热门主题 Top 10:")
    sorted_themes = sorted(themes.items(), key=lambda x: x[1]['frequency'], reverse=True)
    for i, (name, data) in enumerate(sorted_themes[:10], 1):
        print(f"  {i}. {name} — {data['frequency']} 本书")

    print("\n" + "="*50 + "\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="知识图谱构建器")
    parser.add_argument("--build", action="store_true", help="构建知识图谱")
    parser.add_argument("--stats", action="store_true", help="显示统计信息")
    parser.add_argument("--output-dir", "-d", default="output", help="输出目录")
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="INFO",
               format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
               colorize=True)

    if args.build:
        build_knowledge_graph(args.output_dir)
    elif args.stats:
        show_stats(args.output_dir)
    else:
        parser.print_help()
