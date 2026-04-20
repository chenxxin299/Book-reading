# 知识图谱系统说明

## 功能概述

知识图谱系统为读书知识库提供跨书联结功能，支持按主题、概念浏览，并提供可视化图谱展示。

## 核心功能

### 1. 主题浏览 (themes.html)
- 自动从 HTML 报告中提取主题标签
- 显示每个主题关联的书籍列表
- 展示主题相关的核心概念
- 按主题出现频率排序

### 2. 概念索引 (concepts.html)
- 提取所有书籍的核心概念
- 显示概念在不同书籍中的定义
- 标注概念出现频率（高频/中频/低频）
- 支持概念搜索

### 3. 知识图谱 (graph.html)
- 使用 ECharts 力导向图可视化
- 节点：书籍（蓝色）+ 核心概念（红色）
- 连接：书籍与概念的关联关系
- 交互功能：缩放、拖拽、筛选

## 技术架构

### 数据提取 (knowledge_graph.py)
```python
# 从 HTML 报告提取结构化数据
extract_index_from_html(html_path) -> dict
  - 提取核心概念（.concept-box）
  - 提取主题标签（.tag + sec7）
  - 提取观点（.card-accent）
  - 提取金句（.quote）

# 聚合所有书籍数据
build_knowledge_graph(output_dir) -> dict
  - 生成 concepts_index.json（概念索引）
  - 生成 themes_index.json（主题索引）
  - 生成 graph_data.json（图谱数据）
```

### 页面生成
- `generate_themes_page.py` → themes.html
- `generate_concepts_page.py` → concepts.html
- `generate_graph_page.py` → graph.html

### 自动更新流程
```bash
# 每次分析新书后自动更新知识图谱
python auto_analyze.py --once
  ↓
1. 分析新书 → 生成 HTML 报告
2. 更新门户 index.html
3. 构建知识图谱 → 生成 JSON 索引
4. 生成可视化页面 → themes/concepts/graph.html
5. 推送到 GitHub Pages
```

## 数据文件

### output/concepts_index.json
```json
{
  "概念名称": {
    "books": ["书名1", "书名2"],
    "definitions": {
      "书名1": "概念定义...",
      "书名2": "概念定义..."
    },
    "frequency": 2
  }
}
```

### output/themes_index.json
```json
{
  "主题名称": {
    "books": ["书名1", "书名2"],
    "concepts": ["概念1", "概念2"],
    "frequency": 2
  }
}
```

### output/graph_data.json
```json
{
  "nodes": [
    {"id": "book_id", "name": "书名", "type": "book", "size": 10},
    {"id": "concept_id", "name": "概念", "type": "concept", "size": 20}
  ],
  "links": [
    {"source": "book_id", "target": "concept_id"}
  ]
}
```

## 使用方法

### 手动构建知识图谱
```bash
# 构建知识图谱
python knowledge_graph.py --build

# 查看统计信息
python knowledge_graph.py --stats

# 生成可视化页面
python generate_themes_page.py
python generate_concepts_page.py
python generate_graph_page.py
```

### 自动更新（推荐）
```bash
# 分析新书时自动更新知识图谱
python auto_analyze.py --once
```

## 在线访问

- 首页：https://chenxxin299.github.io/Book-reading/
- 主题浏览：https://chenxxin299.github.io/Book-reading/themes.html
- 概念索引：https://chenxxin299.github.io/Book-reading/concepts.html
- 知识图谱：https://chenxxin299.github.io/Book-reading/graph.html

## 当前数据统计

- 已分析书籍：26 本
- 提取概念：175 个
- 提取主题：57 个
- 图谱节点：33 个（书籍 + 高频概念）
- 图谱连接：14 条

## 未来优化方向

1. 增强概念提取准确性（目前依赖 HTML 结构）
2. 添加金句索引页面
3. 支持按作者、出版年份筛选
4. 添加概念关系图（概念之间的关联）
5. 支持全文搜索（需要后端支持）
