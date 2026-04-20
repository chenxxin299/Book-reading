"""
generate_concepts_page.py
────────────────────────────────────────────────
生成概念浏览页面 concepts.html
从 concepts_index.json 读取数据，生成交互式概念浏览界面
"""

import json
import sys
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def generate_concepts_page(output_dir: str = 'output') -> Path:
    """生成概念浏览页面"""
    output_path = Path(output_dir)
    concepts_file = output_path / 'concepts_index.json'

    if not concepts_file.exists():
        print(f"错误: {concepts_file} 不存在，请先运行 knowledge_graph.py --build")
        sys.exit(1)

    concepts = json.loads(concepts_file.read_text(encoding='utf-8'))

    # 按频率排序
    sorted_concepts = sorted(concepts.items(), key=lambda x: x[1]['frequency'], reverse=True)

    # 生成概念卡片
    cards_html = []
    for concept_name, data in sorted_concepts:
        books = data['books']
        definitions = data['definitions']
        freq = data['frequency']

        # 颜色根据频率
        if freq >= 3:
            color = '#c26a18'
            badge_class = 'high'
        elif freq == 2:
            color = '#2d6a8a'
            badge_class = 'medium'
        else:
            color = '#5a7a3a'
            badge_class = 'low'

        # 生成定义列表
        defs_html = []
        for book, definition in list(definitions.items())[:3]:
            if definition:
                defs_html.append(f'<div class="definition"><strong>{book}:</strong> {definition[:150]}{"…" if len(definition) > 150 else ""}</div>')

        cards_html.append(f'''
        <div class="concept-card">
            <div class="concept-header">
                <h3>{concept_name}</h3>
                <span class="badge {badge_class}">{freq} 本书</span>
            </div>
            <div class="concept-body">
                {''.join(defs_html) if defs_html else '<p class="no-def">暂无详细定义</p>'}
                <div class="books">
                    <span class="label">出现于:</span>
                    {' · '.join([f'<span class="book-tag">{b}</span>' for b in books[:4]])}
                    {f'<span class="more-tag">+{len(books)-4}</span>' if len(books) > 4 else ''}
                </div>
            </div>
        </div>''')

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>概念索引 · 读书知识库</title>
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
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}

  body {{
    font-family: "Helvetica Neue", "PingFang SC", "Microsoft YaHei", sans-serif;
    background: var(--bg);
    color: var(--ink);
    min-height: 100vh;
  }}

  .header {{
    background: var(--ink);
    color: #fff;
    padding: 40px 24px;
    text-align: center;
  }}
  .header h1 {{
    font-size: 2rem;
    margin-bottom: 8px;
  }}
  .header p {{
    color: #aaa;
    font-size: 0.95rem;
  }}
  .nav {{
    display: flex;
    justify-content: center;
    gap: 16px;
    margin-top: 20px;
  }}
  .nav a {{
    color: #fff;
    text-decoration: none;
    padding: 8px 16px;
    border-radius: 20px;
    background: rgba(255,255,255,.1);
    transition: background .2s;
  }}
  .nav a:hover {{ background: rgba(255,255,255,.2); }}
  .nav a.active {{ background: var(--accent); }}

  .main {{
    max-width: 1200px;
    margin: 0 auto;
    padding: 40px 24px 80px;
  }}

  .search-bar {{
    max-width: 600px;
    margin: 0 auto 32px;
    position: relative;
  }}
  .search-bar input {{
    width: 100%;
    padding: 14px 20px 14px 44px;
    border-radius: 40px;
    border: 1px solid var(--border);
    font-size: 0.95rem;
    outline: none;
    background: var(--paper);
  }}
  .search-icon {{
    position: absolute;
    left: 16px;
    top: 50%;
    transform: translateY(-50%);
    color: #bbb;
  }}

  .concepts-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
    gap: 20px;
  }}

  .concept-card {{
    background: var(--paper);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
    transition: box-shadow .2s, transform .2s;
  }}
  .concept-card:hover {{
    box-shadow: 0 6px 24px rgba(0,0,0,.14);
    transform: translateY(-2px);
  }}

  .concept-header {{
    padding: 16px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
  }}
  .concept-header h3 {{
    font-size: 1.1rem;
    font-weight: 700;
  }}
  .badge {{
    font-size: 12px;
    padding: 4px 10px;
    border-radius: 12px;
    font-weight: 600;
  }}
  .badge.high {{
    background: #fff1e2;
    color: #c26a18;
  }}
  .badge.medium {{
    background: #e3f2fd;
    color: #2d6a8a;
  }}
  .badge.low {{
    background: #f0f4f0;
    color: #5a7a3a;
  }}

  .concept-body {{
    padding: 20px;
  }}
  .definition {{
    font-size: 0.9rem;
    line-height: 1.6;
    margin-bottom: 12px;
    color: var(--ink);
  }}
  .definition strong {{
    color: var(--accent);
    font-weight: 600;
  }}
  .no-def {{
    font-size: 0.9rem;
    color: var(--ink-light);
    font-style: italic;
    margin-bottom: 12px;
  }}

  .books {{
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid var(--border);
    font-size: 0.85rem;
  }}
  .books .label {{
    color: var(--ink-light);
    margin-right: 8px;
  }}
  .book-tag {{
    color: var(--ink);
  }}
  .more-tag {{
    color: var(--accent);
    font-weight: 600;
  }}

  .footer {{
    text-align: center;
    padding: 32px;
    font-size: 12px;
    color: #bbb;
    border-top: 1px solid var(--border);
  }}

  @media (max-width: 640px) {{
    .concepts-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>🔑 概念索引</h1>
  <p>跨书核心概念 · {len(concepts)} 个概念</p>
  <div class="nav">
    <a href="index.html">首页</a>
    <a href="themes.html">主题</a>
    <a href="concepts.html" class="active">概念</a>
    <a href="graph.html">知识图谱</a>
  </div>
</div>

<div class="main">
  <div class="search-bar">
    <span class="search-icon">🔍</span>
    <input type="text" id="search" placeholder="搜索概念..." autocomplete="off">
  </div>

  <div class="concepts-grid" id="concepts-grid">
    {''.join(cards_html)}
  </div>
</div>

<div class="footer">
  生成于 {now} · Book Intelligence System
</div>

<script>
  const grid = document.getElementById('concepts-grid');
  const searchInput = document.getElementById('search');
  const allCards = Array.from(grid.querySelectorAll('.concept-card'));

  searchInput.addEventListener('input', () => {{
    const q = searchInput.value.trim().toLowerCase();
    let visible = 0;

    allCards.forEach(card => {{
      if (!q) {{
        card.style.display = '';
        visible++;
        return;
      }}

      const text = card.textContent.toLowerCase();
      const match = text.includes(q);

      card.style.display = match ? '' : 'none';
      if (match) visible++;
    }});
  }});
</script>
</body>
</html>'''

    output_file = output_path / 'concepts.html'
    output_file.write_text(html, encoding='utf-8')
    print(f"✓ 概念页面已生成: {output_file}")
    return output_file

if __name__ == "__main__":
    generate_concepts_page()
