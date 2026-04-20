"""
generate_portal.py
────────────────────────────────────────────────
扫描 output/ 目录，聚合所有读书报告 + _meta.json，
生成完整的知识库门户首页 index.html。

用法：
  python generate_portal.py                # 默认读取 output/, 写入 output/index.html
  python generate_portal.py --output-dir output --portal output/index.html
"""

import json
import os
import re
import sys
import argparse
from pathlib import Path
from datetime import datetime


# ── 扫描已分析书目 ──────────────────────────────────────────
def collect_books(output_dir: str = "output") -> list[dict]:
    out = Path(output_dir)
    books = []
    for meta_file in sorted(out.glob("*_meta.json"), key=lambda p: p.stat().st_mtime, reverse=True):
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            # 确认对应 HTML 真实存在
            html_path = out / meta["filename"]
            if html_path.exists():
                meta["exists"] = True
                books.append(meta)
        except Exception:
            pass
    return books


# ── 提取摘要（从 HTML 第一段卡片里取前 200 字）──────────────
def extract_summary(html_path: Path) -> str:
    try:
        html = html_path.read_text(encoding="utf-8", errors="ignore")
        # 找第一个 <p> 内容
        match = re.search(r"<p[^>]*>(.*?)</p>", html, re.DOTALL | re.IGNORECASE)
        if match:
            text = re.sub(r"<[^>]+>", "", match.group(1)).strip()
            return text[:200] + ("…" if len(text) > 200 else "")
    except Exception:
        pass
    return "深度读书分析报告，涵盖核心概念、结构拆解、观点分析等十大板块。"


# ── 生成首页 HTML ─────────────────────────────────────────────
def build_portal_html(books: list[dict]) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # 书籍卡片 HTML
    if not books:
        cards_html = """
        <div class="empty">
            <div class="empty-icon">📚</div>
            <p>暂无读书报告</p>
            <p class="sub">将 epub / pdf 放入 <code>books/</code> 目录，系统将自动分析并在此展示</p>
        </div>"""
    else:
        cards = []
        for b in books:
            title = b.get("title", b.get("book_name", "未知书目"))
            book_name = b.get("book_name", title)
            filename = b.get("filename", "")
            analyzed_at = b.get("analyzed_at", "")
            chars = b.get("chars", 0)
            chars_str = f"{chars // 1000}k 字" if chars > 1000 else ""

            # 颜色 hash（让每本书卡片顶部颜色不同）
            colors = ["#c26a18", "#2d6a8a", "#5a7a3a", "#7a4a8a", "#8a5a2a", "#3a6a6a"]
            color = colors[hash(book_name) % len(colors)]

            cards.append(f"""
        <a class="book-card" href="{filename}" target="_blank">
            <div class="card-accent" style="background:{color}"></div>
            <div class="card-body">
                <h3 class="card-title">{title}</h3>
                <div class="card-meta">
                    <span>📅 {analyzed_at}</span>
                    {f'<span>📄 {chars_str}</span>' if chars_str else ''}
                </div>
                <p class="card-desc">深度分析报告 · 十大板块</p>
                <div class="card-tags">
                    <span class="tag">导读</span>
                    <span class="tag">核心概念</span>
                    <span class="tag">圆桌讨论</span>
                    <span class="tag">金句</span>
                </div>
            </div>
            <div class="card-arrow">→</div>
        </a>""")
        cards_html = "\n".join(cards)

    book_count = len(books)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>读书知识库 · Book Intelligence</title>
<style>
  :root {{
    --bg: #f6f3ee;
    --paper: #fff;
    --ink: #1f2328;
    --ink-light: #5a6272;
    --accent: #c26a18;
    --accent-soft: #fff1e2;
    --border: #e8e4df;
    --radius: 12px;
    --shadow: 0 2px 12px rgba(0,0,0,.08);
    --shadow-hover: 0 6px 24px rgba(0,0,0,.14);
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg);
    color: var(--ink);
    min-height: 100vh;
  }}

  /* ── 顶部 Hero ── */
  .hero {{
    background: var(--ink);
    color: #fff;
    padding: 60px 40px 48px;
    text-align: center;
  }}
  .hero-label {{
    font-size: 12px;
    letter-spacing: 3px;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 16px;
    font-weight: 600;
  }}
  .hero h1 {{
    font-size: 2.6rem;
    font-weight: 700;
    margin-bottom: 12px;
    letter-spacing: -.5px;
  }}
  .hero p {{
    color: #aaa;
    font-size: 1.05rem;
    max-width: 540px;
    margin: 0 auto 24px;
    line-height: 1.7;
  }}
  .hero-stats {{
    display: flex;
    justify-content: center;
    gap: 40px;
    margin-top: 8px;
  }}
  .stat {{
    text-align: center;
  }}
  .stat-num {{
    font-size: 2rem;
    font-weight: 700;
    color: var(--accent);
  }}
  .stat-label {{
    font-size: 12px;
    color: #888;
    margin-top: 4px;
  }}

  /* ── 搜索栏 ── */
  .search-bar {{
    max-width: 600px;
    margin: -24px auto 0;
    padding: 0 20px;
    position: relative;
    z-index: 10;
  }}
  .search-bar input {{
    width: 100%;
    padding: 16px 20px 16px 48px;
    border-radius: 40px;
    border: none;
    box-shadow: var(--shadow-hover);
    font-size: 1rem;
    color: var(--ink);
    outline: none;
    background: var(--paper);
  }}
  .search-bar input::placeholder {{ color: #bbb; }}
  .search-icon {{
    position: absolute;
    left: 36px;
    top: 50%;
    transform: translateY(-50%);
    color: #bbb;
    font-size: 1.1rem;
  }}

  /* ── 主内容区 ── */
  .main {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 48px 24px 80px;
  }}

  .section-header {{
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 28px;
  }}
  .section-title {{
    font-size: 1.2rem;
    font-weight: 700;
    color: var(--ink);
  }}
  .section-count {{
    font-size: 13px;
    color: var(--ink-light);
    background: var(--border);
    padding: 4px 12px;
    border-radius: 20px;
  }}

  /* ── 书籍卡片网格 ── */
  .books-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: 20px;
  }}

  .book-card {{
    background: var(--paper);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    text-decoration: none;
    color: var(--ink);
    display: flex;
    flex-direction: column;
    transition: box-shadow .2s, transform .2s;
    overflow: hidden;
    position: relative;
  }}
  .book-card:hover {{
    box-shadow: var(--shadow-hover);
    transform: translateY(-3px);
  }}
  .card-accent {{
    height: 5px;
    width: 100%;
  }}
  .card-body {{
    padding: 20px 22px 16px;
    flex: 1;
  }}
  .card-title {{
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 10px;
    line-height: 1.4;
    color: var(--ink);
  }}
  .card-meta {{
    display: flex;
    gap: 16px;
    font-size: 12px;
    color: var(--ink-light);
    margin-bottom: 12px;
  }}
  .card-desc {{
    font-size: 13px;
    color: var(--ink-light);
    line-height: 1.6;
    margin-bottom: 14px;
  }}
  .card-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }}
  .tag {{
    font-size: 11px;
    padding: 3px 10px;
    background: var(--accent-soft);
    color: var(--accent);
    border-radius: 20px;
    font-weight: 500;
  }}
  .card-arrow {{
    position: absolute;
    right: 18px;
    bottom: 18px;
    font-size: 1.1rem;
    color: #ccc;
    transition: color .2s, transform .2s;
  }}
  .book-card:hover .card-arrow {{
    color: var(--accent);
    transform: translateX(4px);
  }}

  /* ── 空状态 ── */
  .empty {{
    text-align: center;
    padding: 80px 20px;
    color: var(--ink-light);
  }}
  .empty-icon {{ font-size: 3rem; margin-bottom: 16px; }}
  .empty p {{ font-size: 1.05rem; margin-bottom: 8px; }}
  .empty .sub {{ font-size: 14px; color: #bbb; }}
  .empty code {{
    background: #f0ece6;
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
    font-size: 13px;
  }}

  /* ── 底部 ── */
  .footer {{
    text-align: center;
    padding: 32px;
    font-size: 12px;
    color: #bbb;
    border-top: 1px solid var(--border);
  }}
  .footer a {{ color: var(--accent); text-decoration: none; }}

  /* ── 响应式 ── */
  @media (max-width: 640px) {{
    .hero h1 {{ font-size: 1.8rem; }}
    .hero-stats {{ gap: 24px; }}
    .main {{ padding: 32px 16px 60px; }}
    .books-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<div class="hero">
  <div class="hero-label">Book Intelligence</div>
  <h1>读书知识库</h1>
  <p>基于 GPT-5.4 深度分析的读书报告集合，涵盖导读、核心概念、结构拆解、跨学科讨论等十大板块。</p>
  <div class="hero-stats">
    <div class="stat">
      <div class="stat-num">{book_count}</div>
      <div class="stat-label">本书已分析</div>
    </div>
    <div class="stat">
      <div class="stat-num">10</div>
      <div class="stat-label">深度板块</div>
    </div>
    <div class="stat">
      <div class="stat-num">GPT‑5.4</div>
      <div class="stat-label">驱动模型</div>
    </div>
  </div>
</div>

<div class="search-bar">
  <span class="search-icon">🔍</span>
  <input type="text" id="search" placeholder="搜索书名、作者、关键词…（Ctrl+K）" autocomplete="off">
</div>

<div class="main">
  <div class="section-header">
    <span class="section-title">全部读书报告</span>
    <span class="section-count" id="count-label">{book_count} 本</span>
  </div>

  <div style="display: flex; justify-content: center; gap: 12px; margin-bottom: 32px;">
    <a href="themes.html" style="padding: 10px 20px; background: #fff; border: 1px solid #e8e4df; border-radius: 20px; text-decoration: none; color: #1f2328; font-size: 0.9rem; transition: all .2s;">📑 主题浏览</a>
    <a href="concepts.html" style="padding: 10px 20px; background: #fff; border: 1px solid #e8e4df; border-radius: 20px; text-decoration: none; color: #1f2328; font-size: 0.9rem; transition: all .2s;">🔑 概念索引</a>
    <a href="graph.html" style="padding: 10px 20px; background: #fff; border: 1px solid #e8e4df; border-radius: 20px; text-decoration: none; color: #1f2328; font-size: 0.9rem; transition: all .2s;">🕸️ 知识图谱</a>
  </div>

  <div class="books-grid" id="books-grid">
    {cards_html}
  </div>
</div>

<div class="footer">
  自动生成于 {now} &nbsp;·&nbsp;
  由 <a href="https://github.com/openai/openai-python" target="_blank">GPT‑5.4</a> 驱动
  &nbsp;·&nbsp; Book Intelligence System
</div>

<script>
  const grid = document.getElementById('books-grid');
  const countLabel = document.getElementById('count-label');
  const searchInput = document.getElementById('search');
  const allCards = Array.from(grid.querySelectorAll('.book-card'));

  // 增强搜索：支持书名、作者、标签、描述的模糊匹配
  searchInput.addEventListener('input', () => {{
    const q = searchInput.value.trim().toLowerCase();
    let visible = 0;

    allCards.forEach(card => {{
      if (!q) {{
        card.style.display = '';
        visible++;
        return;
      }}

      // 提取卡片中的所有文本内容
      const title = card.querySelector('.card-title')?.textContent.toLowerCase() || '';
      const meta = card.querySelector('.card-meta')?.textContent.toLowerCase() || '';
      const desc = card.querySelector('.card-desc')?.textContent.toLowerCase() || '';
      const tags = Array.from(card.querySelectorAll('.tag')).map(t => t.textContent.toLowerCase()).join(' ');

      // 组合所有可搜索内容
      const searchText = [title, meta, desc, tags].join(' ');

      // 支持多关键词搜索（空格分隔）
      const keywords = q.split(/\\s+/).filter(k => k);
      const match = keywords.every(keyword => searchText.includes(keyword));

      card.style.display = match ? '' : 'none';
      if (match) visible++;
    }});

    countLabel.textContent = visible + ' 本';

    // 无结果提示
    if (visible === 0 && q) {{
      if (!document.getElementById('no-results')) {{
        const noResults = document.createElement('div');
        noResults.id = 'no-results';
        noResults.className = 'empty';
        noResults.innerHTML = '<div class="empty-icon">🔍</div><p>未找到匹配的书籍</p><p class="sub">试试其他关键词</p>';
        grid.appendChild(noResults);
      }}
    }} else {{
      document.getElementById('no-results')?.remove();
    }}
  }});

  // 搜索框快捷键：Ctrl/Cmd + K 聚焦搜索框
  document.addEventListener('keydown', (e) => {{
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {{
      e.preventDefault();
      searchInput.focus();
      searchInput.select();
    }}
  }});
</script>
</body>
</html>"""


# ── 主流程 ──────────────────────────────────────────────────
def generate(output_dir: str = "output", portal_path: str = None) -> Path:
    books = collect_books(output_dir)
    html = build_portal_html(books)

    if portal_path is None:
        portal_path = str(Path(output_dir) / "index.html")

    p = Path(portal_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(html, encoding="utf-8")
    print(f"[portal] index.html 已生成: {p}  ({len(books)} 本书)")
    return p


# ── CLI ─────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="生成读书知识库门户 index.html")
    parser.add_argument("--output-dir", "-d", default="output", help="报告目录（默认 output/）")
    parser.add_argument("--portal",     "-p", default=None,     help="门户输出路径（默认 output/index.html）")
    args = parser.parse_args()

    path = generate(args.output_dir, args.portal)
    print(f"\n门户已生成: {path}")
