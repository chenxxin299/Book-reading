"""
generate_themes_page.py
────────────────────────────────────────────────
生成主题浏览页面 themes.html
从 themes_index.json 读取数据，生成交互式主题浏览界面
"""

import json
import sys
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def generate_themes_page(output_dir: str = 'output') -> Path:
    """生成主题浏览页面"""
    output_path = Path(output_dir)
    themes_file = output_path / 'themes_index.json'

    if not themes_file.exists():
        print(f"错误: {themes_file} 不存在，请先运行 knowledge_graph.py --build")
        sys.exit(1)

    themes = json.loads(themes_file.read_text(encoding='utf-8'))

    # 按频率排序
    sorted_themes = sorted(themes.items(), key=lambda x: x[1]['frequency'], reverse=True)

    # 生成主题卡片
    cards_html = []
    for theme_name, data in sorted_themes:
        books = data['books']
        concepts = data['concepts']
        freq = data['frequency']

        # 颜色根据频率
        if freq >= 3:
            color = '#c26a18'
        elif freq == 2:
            color = '#2d6a8a'
        else:
            color = '#5a7a3a'

        books_html = ''.join([f'<li>{book}</li>' for book in books[:5]])
        if len(books) > 5:
            books_html += f'<li class="more">+ {len(books) - 5} 本</li>'

        concepts_html = ''.join([f'<span class="concept-tag">{c}</span>' for c in concepts[:8]])
        if len(concepts) > 8:
            concepts_html += f'<span class="concept-tag more">+{len(concepts) - 8}</span>'

        cards_html.append(f'''
        <div class="theme-card">
            <div class="theme-header" style="border-left: 4px solid {color}">
                <h3>{theme_name}</h3>
                <span class="badge">{freq} 本书</span>
            </div>
            <div class="theme-body">
                <div class="section">
                    <h4>📚 相关书籍</h4>
                    <ul class="book-list">{books_html}</ul>
                </div>
                {f'<div class="section"><h4>🔑 关联概念</h4><div class="concepts">{concepts_html}</div></div>' if concepts else ''}
            </div>
        </div>''')

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>主题浏览 · 读书知识库</title>
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

  .themes-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 20px;
  }}

  .theme-card {{
    background: var(--paper);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    overflow: hidden;
    transition: box-shadow .2s, transform .2s;
  }}
  .theme-card:hover {{
    box-shadow: 0 6px 24px rgba(0,0,0,.14);
    transform: translateY(-2px);
  }}

  .theme-header {{
    padding: 16px 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid var(--border);
  }}
  .theme-header h3 {{
    font-size: 1.1rem;
    font-weight: 700;
  }}
  .badge {{
    font-size: 12px;
    padding: 4px 10px;
    background: var(--accent-soft);
    color: var(--accent);
    border-radius: 12px;
    font-weight: 600;
  }}

  .theme-body {{
    padding: 20px;
  }}
  .section {{
    margin-bottom: 16px;
  }}
  .section:last-child {{
    margin-bottom: 0;
  }}
  .section h4 {{
    font-size: 0.85rem;
    color: var(--ink-light);
    margin-bottom: 10px;
    font-weight: 600;
  }}

  .book-list {{
    list-style: none;
    font-size: 0.9rem;
    line-height: 1.8;
  }}
  .book-list li {{
    color: var(--ink);
    padding-left: 12px;
    position: relative;
  }}
  .book-list li::before {{
    content: "•";
    position: absolute;
    left: 0;
    color: var(--accent);
  }}
  .book-list li.more {{
    color: var(--ink-light);
    font-size: 0.85rem;
  }}

  .concepts {{
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }}
  .concept-tag {{
    font-size: 11px;
    padding: 4px 10px;
    background: #f0ece6;
    color: var(--ink);
    border-radius: 12px;
  }}
  .concept-tag.more {{
    background: var(--accent-soft);
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
    .themes-grid {{ grid-template-columns: 1fr; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>📑 主题浏览</h1>
  <p>跨书主题索引 · {len(themes)} 个主题</p>
  <div class="nav">
    <a href="index.html">首页</a>
    <a href="themes.html" class="active">主题</a>
    <a href="concepts.html">概念</a>
    <a href="graph.html">知识图谱</a>
  </div>
</div>

<div class="main">
  <div class="search-bar">
    <span class="search-icon">🔍</span>
    <input type="text" id="search" placeholder="搜索主题..." autocomplete="off">
  </div>

  <div class="themes-grid" id="themes-grid">
    {''.join(cards_html)}
  </div>
</div>

<div class="footer">
  生成于 {now} · Book Intelligence System
</div>

<script>
  const grid = document.getElementById('themes-grid');
  const searchInput = document.getElementById('search');
  const allCards = Array.from(grid.querySelectorAll('.theme-card'));

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

    output_file = output_path / 'themes.html'
    output_file.write_text(html, encoding='utf-8')
    print(f"✓ 主题页面已生成: {output_file}")
    return output_file

if __name__ == "__main__":
    generate_themes_page()
