"""
generate_graph_page.py
────────────────────────────────────────────────
生成知识图谱可视化页面 graph.html
使用 ECharts 渲染交互式力导向图
"""

import json
import sys
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def generate_graph_page(output_dir: str = 'output') -> Path:
    """生成知识图谱可视化页面"""
    output_path = Path(output_dir)
    graph_file = output_path / 'graph_data.json'

    if not graph_file.exists():
        print(f"错误: {graph_file} 不存在，请先运行 knowledge_graph.py --build")
        sys.exit(1)

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>知识图谱 · 读书知识库</title>
<style>
  :root {{
    --bg: #f6f3ee;
    --paper: #fff;
    --ink: #1f2328;
    --ink-light: #5a6272;
    --accent: #c26a18;
    --border: #e8e4df;
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
    flex: 1;
    display: flex;
    flex-direction: column;
    padding: 24px;
    max-width: 1400px;
    width: 100%;
    margin: 0 auto;
  }}

  .controls {{
    display: flex;
    justify-content: center;
    gap: 12px;
    margin-bottom: 20px;
  }}
  .controls button {{
    padding: 8px 16px;
    border: 1px solid var(--border);
    background: var(--paper);
    color: var(--ink);
    border-radius: 20px;
    cursor: pointer;
    font-size: 0.9rem;
    transition: all .2s;
  }}
  .controls button:hover {{
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
  }}
  .controls button.active {{
    background: var(--accent);
    color: #fff;
    border-color: var(--accent);
  }}

  #graph {{
    flex: 1;
    background: var(--paper);
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0,0,0,.08);
    min-height: 600px;
  }}

  .legend {{
    display: flex;
    justify-content: center;
    gap: 24px;
    margin-top: 16px;
    font-size: 0.85rem;
  }}
  .legend-item {{
    display: flex;
    align-items: center;
    gap: 8px;
  }}
  .legend-dot {{
    width: 12px;
    height: 12px;
    border-radius: 50%;
  }}
  .legend-dot.book {{ background: #5470c6; }}
  .legend-dot.concept {{ background: #ee6666; }}

  .footer {{
    text-align: center;
    padding: 24px;
    font-size: 12px;
    color: #bbb;
  }}

  @media (max-width: 640px) {{
    .main {{ padding: 16px; }}
    #graph {{ min-height: 400px; }}
  }}
</style>
</head>
<body>

<div class="header">
  <h1>🕸️ 知识图谱</h1>
  <p>书籍与概念的关联网络</p>
  <div class="nav">
    <a href="index.html">首页</a>
    <a href="themes.html">主题</a>
    <a href="concepts.html">概念</a>
    <a href="graph.html" class="active">知识图谱</a>
  </div>
</div>

<div class="main">
  <div class="controls">
    <button id="btn-reset">重置视图</button>
    <button id="btn-books">仅显示书籍</button>
    <button id="btn-concepts">仅显示概念</button>
    <button id="btn-all" class="active">显示全部</button>
  </div>

  <div id="graph"></div>

  <div class="legend">
    <div class="legend-item">
      <div class="legend-dot book"></div>
      <span>书籍</span>
    </div>
    <div class="legend-item">
      <div class="legend-dot concept"></div>
      <span>核心概念</span>
    </div>
  </div>
</div>

<div class="footer">
  生成于 {now} · Book Intelligence System
</div>

<script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
<script>
  const chart = echarts.init(document.getElementById('graph'));

  // 加载图谱数据
  fetch('graph_data.json')
    .then(res => res.json())
    .then(data => {{
      const nodes = data.nodes.map(n => ({{
        id: n.id,
        name: n.name,
        symbolSize: Math.sqrt(n.size) * 8,
        category: n.type === 'book' ? 0 : 1,
        itemStyle: {{
          color: n.type === 'book' ? '#5470c6' : '#ee6666'
        }}
      }}));

      const links = data.links.map(l => ({{
        source: l.source,
        target: l.target
      }}));

      const option = {{
        tooltip: {{
          formatter: '{{b}}'
        }},
        series: [{{
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: links,
          categories: [
            {{ name: '书籍' }},
            {{ name: '概念' }}
          ],
          roam: true,
          label: {{
            show: true,
            position: 'right',
            formatter: '{{b}}',
            fontSize: 11
          }},
          labelLayout: {{
            hideOverlap: true
          }},
          force: {{
            repulsion: 200,
            edgeLength: 100,
            gravity: 0.1
          }},
          emphasis: {{
            focus: 'adjacency',
            lineStyle: {{
              width: 3
            }}
          }},
          lineStyle: {{
            color: '#ccc',
            width: 1.5,
            curveness: 0.2
          }}
        }}]
      }};

      chart.setOption(option);

      // 控制按钮
      let allNodes = nodes;
      let allLinks = links;

      document.getElementById('btn-reset').onclick = () => {{
        chart.setOption(option);
      }};

      document.getElementById('btn-books').onclick = () => {{
        const bookNodes = allNodes.filter(n => n.category === 0);
        chart.setOption({{
          series: [{{ data: bookNodes, links: [] }}]
        }});
        updateActiveBtn('btn-books');
      }};

      document.getElementById('btn-concepts').onclick = () => {{
        const conceptNodes = allNodes.filter(n => n.category === 1);
        chart.setOption({{
          series: [{{ data: conceptNodes, links: [] }}]
        }});
        updateActiveBtn('btn-concepts');
      }};

      document.getElementById('btn-all').onclick = () => {{
        chart.setOption({{
          series: [{{ data: allNodes, links: allLinks }}]
        }});
        updateActiveBtn('btn-all');
      }};

      function updateActiveBtn(id) {{
        document.querySelectorAll('.controls button').forEach(btn => {{
          btn.classList.remove('active');
        }});
        document.getElementById(id).classList.add('active');
      }}
    }})
    .catch(err => {{
      console.error('加载图谱数据失败:', err);
      document.getElementById('graph').innerHTML = '<div style="display:flex;align-items:center;justify-content:center;height:100%;color:#999;">加载失败，请检查 graph_data.json</div>';
    }});

  // 响应式
  window.addEventListener('resize', () => {{
    chart.resize();
  }});
</script>
</body>
</html>'''

    output_file = output_path / 'graph.html'
    output_file.write_text(html, encoding='utf-8')
    print(f"✓ 知识图谱页面已生成: {output_file}")
    return output_file

if __name__ == "__main__":
    generate_graph_page()
