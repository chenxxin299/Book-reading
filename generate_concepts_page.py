"""
generate_concepts_page.py
────────────────────────────────────────────────
生成概念浏览页面 concepts.html（左侧索引 + 右侧详情）
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

    # 生成侧边栏索引
    sidebar_items = []
    for i, (concept_name, data) in enumerate(sorted_concepts):
        freq = data['frequency']
        badge_class = 'high' if freq >= 3 else 'medium' if freq == 2 else 'low'
        sidebar_items.append(f'''
        <div class="sidebar-item" data-concept-id="concept-{i}">
            <span class="concept-name">{concept_name}</span>
            <span class="concept-badge {badge_class}">{freq}</span>
        </div>''')

    # 生成详情数据（JSON）
    concepts_data = {}
    for i, (concept_name, data) in enumerate(sorted_concepts):
        concepts_data[f'concept-{i}'] = {
            'name': concept_name,
            'books': data['books'],
            'definitions': data['definitions'],
            'frequency': data['frequency']
        }

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
    display: flex;
    flex-direction: column;
  }}

  .header {{
    background: var(--ink);
    color: #fff;
    padding: 32px 24px;
    text-align: center;
  }}
  .header h1 {{
    font-size: 1.8rem;
    margin-bottom: 8px;
  }}
  .header p {{
    color: #aaa;
    font-size: 0.9rem;
  }}
  .nav {{
    display: flex;
    justify-content: center;
    gap: 16px;
    margin-top: 16px;
  }}
  .nav a {{
    color: #fff;
    text-decoration: none;
    padding: 8px 16px;
    border-radius: 20px;
    background: rgba(255,255,255,.1);
    transition: background .2s;
    font-size: 0.9rem;
  }}
  .nav a:hover {{ background: rgba(255,255,255,.2); }}
  .nav a.active {{ background: var(--accent); }}

  .container {{
    flex: 1;
    display: flex;
    max-width: 1400px;
    width: 100%;
    margin: 0 auto;
    padding: 24px;
    gap: 24px;
  }}

  /* 左侧索引栏 */
  .sidebar {{
    width: 280px;
    background: var(--paper);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 20px 0;
    max-height: calc(100vh - 200px);
    overflow-y: auto;
    position: sticky;
    top: 24px;
  }}
  .sidebar-header {{
    padding: 0 20px 16px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 12px;
  }}
  .sidebar-header h3 {{
    font-size: 1rem;
    font-weight: 700;
    color: var(--ink);
  }}
  .sidebar-item {{
    padding: 12px 20px;
    cursor: pointer;
    display: flex;
    justify-content: space-between;
    align-items: center;
    transition: background .2s;
  }}
  .sidebar-item:hover {{
    background: var(--accent-soft);
  }}
  .sidebar-item.active {{
    background: var(--accent-soft);
    border-left: 3px solid var(--accent);
  }}
  .concept-name {{
    font-size: 0.9rem;
    color: var(--ink);
    flex: 1;
  }}
  .concept-badge {{
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: 600;
  }}
  .concept-badge.high {{
    background: #fff1e2;
    color: #c26a18;
  }}
  .concept-badge.medium {{
    background: #e3f2fd;
    color: #2d6a8a;
  }}
  .concept-badge.low {{
    background: #f0f4f0;
    color: #5a7a3a;
  }}

  /* 右侧详情区 */
  .content {{
    flex: 1;
    background: var(--paper);
    border-radius: var(--radius);
    box-shadow: var(--shadow);
    padding: 32px;
    min-height: 400px;
  }}
  .content-empty {{
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--ink-light);
    font-size: 0.95rem;
  }}
  .detail-header {{
    margin-bottom: 24px;
    padding-bottom: 16px;
    border-bottom: 2px solid var(--border);
  }}
  .detail-title {{
    font-size: 1.6rem;
    font-weight: 700;
    color: var(--ink);
    margin-bottom: 8px;
  }}
  .detail-meta {{
    font-size: 0.85rem;
    color: var(--ink-light);
  }}
  .detail-section {{
    margin-bottom: 28px;
  }}
  .detail-section h4 {{
    font-size: 1rem;
    font-weight: 700;
    color: var(--ink);
    margin-bottom: 12px;
  }}
  .definition-item {{
    margin-bottom: 16px;
    padding: 16px;
    background: #f9f8f6;
    border-radius: 8px;
    border-left: 3px solid var(--accent);
  }}
  .definition-book {{
    font-size: 0.85rem;
    font-weight: 600;
    color: var(--accent);
    margin-bottom: 6px;
  }}
  .definition-text {{
    font-size: 0.9rem;
    line-height: 1.6;
    color: var(--ink);
  }}
  .no-definition {{
    color: var(--ink-light);
    font-style: italic;
    font-size: 0.9rem;
  }}
  .book-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
  }}
  .book-tag {{
    font-size: 0.85rem;
    padding: 6px 14px;
    background: #f0ece6;
    color: var(--ink);
    border-radius: 16px;
  }}

  .footer {{
    text-align: center;
    padding: 24px;
    font-size: 12px;
    color: #bbb;
  }}

  @media (max-width: 768px) {{
    .container {{
      flex-direction: column;
    }}
    .sidebar {{
      width: 100%;
      position: static;
      max-height: 300px;
    }}
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

<div class="container">
  <div class="sidebar">
    <div class="sidebar-header">
      <h3>概念列表</h3>
    </div>
    {''.join(sidebar_items)}
  </div>

  <div class="content">
    <div class="content-empty">← 点击左侧概念查看详情</div>
  </div>
</div>

<div class="footer">
  生成于 {now} · Book Intelligence System
</div>

<script>
const conceptsData = {json.dumps(concepts_data, ensure_ascii=False)};

const sidebar = document.querySelector('.sidebar');
const content = document.querySelector('.content');
const sidebarItems = document.querySelectorAll('.sidebar-item');

sidebarItems.forEach(item => {{
  item.addEventListener('click', () => {{
    const conceptId = item.dataset.conceptId;
    const concept = conceptsData[conceptId];

    // 更新激活状态
    sidebarItems.forEach(i => i.classList.remove('active'));
    item.classList.add('active');

    // 渲染定义
    let definitionsHtml = '';
    const defs = Object.entries(concept.definitions);
    if (defs.length > 0 && defs.some(([_, def]) => def)) {{
      definitionsHtml = defs
        .filter(([_, def]) => def)
        .map(([book, def]) => `
          <div class="definition-item">
            <div class="definition-book">${{book}}</div>
            <div class="definition-text">${{def}}</div>
          </div>
        `).join('');
    }} else {{
      definitionsHtml = '<div class="no-definition">暂无详细定义</div>';
    }}

    // 渲染书籍标签
    const booksHtml = concept.books.map(book => `<span class="book-tag">${{book}}</span>`).join('');

    content.innerHTML = `
      <div class="detail-header">
        <div class="detail-title">${{concept.name}}</div>
        <div class="detail-meta">出现于 ${{concept.frequency}} 本书</div>
      </div>
      <div class="detail-section">
        <h4>📖 概念定义</h4>
        ${{definitionsHtml}}
      </div>
      <div class="detail-section">
        <h4>📚 出现于</h4>
        <div class="book-tags">${{booksHtml}}</div>
      </div>
    `;
  }});
}});

// 默认选中第一个
if (sidebarItems.length > 0) {{
  sidebarItems[0].click();
}}
</script>
</body>
</html>'''

    output_file = output_path / 'concepts.html'
    output_file.write_text(html, encoding='utf-8')
    print(f"✓ 概念页面已生成: {output_file}")
    return output_file

if __name__ == "__main__":
    generate_concepts_page()
