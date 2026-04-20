# 📚 Book Analyst — AI 驱动的深度读书报告生成器

基于 GPT-5.4 的自动化读书分析系统，将 epub/pdf 书籍转换为结构化的深度分析报告，并自动发布到 GitHub Pages。

## ✨ 核心特性

- **深度分析**：10 大板块（导读、问题意识、核心概念、结构拆解、观点分析、圆桌讨论、认知拓展、启发追问、金句、Takeaways）
- **交互式思维导图**：基于 markmap 的全书结构可视化
- **精美排版**：响应式 HTML 报告，支持移动端阅读
- **并行处理**：最多 5 本书同时分析，大幅缩短等待时间
- **自动发布**：一键推送到 GitHub Pages，在线访问知识库
- **智能去重**：自动跳过已分析的书籍

## 📦 安装

```bash
# 克隆仓库
git clone https://github.com/你的用户名/book-analyst.git
cd book-analyst

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入你的 API Key 和 GitHub 仓库地址
```

## 🚀 快速开始

### 方式一：自动监控模式（推荐）

```bash
# 1. 把书放进"书本"目录
cp 你的书.epub 书本/
cp 另一本书.pdf 书本/

# 2. 启动自动分析（会持续监控，发现新书自动分析并推送）
python auto_analyze.py
```

### 方式二：手动批量分析

```bash
# 分析"书本"目录下所有新书（最多 5 本并发）
python batch_analyze.py --dir 书本/ --workers 5

# 推送到 GitHub Pages
python deploy.py
```

### 方式三：单本书分析

```bash
# 分析单本书
python reading_skill.py "书名.epub" --output output

# 生成门户
python generate_portal.py

# 推送
python deploy.py
```

## 📂 项目结构

```
book-analyst/
├── 书本/                      # 放书的地方（epub/pdf）
├── output/                    # 生成的 HTML 报告
│   ├── index.html            # 知识库门户首页
│   ├── 书名.html             # 各书的分析报告
│   └── 书名_meta.json        # 元数据
├── reading_skill.py          # 核心分析引擎
├── analysis_prompt.md        # 分析 Prompt（可单独编辑）
├── batch_analyze.py          # 批量并行分析
├── auto_analyze.py           # 自动监控 + 分析 + 推送
├── deploy.py                 # GitHub Pages 部署
├── generate_portal.py        # 门户生成器
├── watcher.py                # 文件监控守护进程（备用）
└── .env                      # 环境变量配置
```

## ⚙️ 配置说明

编辑 `.env` 文件：

```bash
# OpenAI API
OPENAI_API_KEY=sk-your-key-here
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_MODEL=gpt-5.4

# GitHub Pages 部署（可选）
GITHUB_REPO=https://github.com/你的用户名/你的仓库名.git
```

## 🎯 使用场景

| 场景 | 命令 |
|---|---|
| 日常使用（推荐） | `python auto_analyze.py` |
| 一次性批量分析 10 本书 | `python batch_analyze.py --dir 书本/ --workers 5` |
| 分析单本书 | `python reading_skill.py 书名.epub` |
| 只推送不分析 | `python deploy.py` |
| 扫描一次后退出 | `python auto_analyze.py --once` |
| 分析但不推送 | `python auto_analyze.py --no-deploy` |

## 📊 报告示例

每份报告包含：

1. **导读** — 快速理解全书核心
2. **问题意识** — 作者要解决什么根本困境
3. **核心概念** — 5-8 个关键概念深度解析 + 概念张力对比
4. **结构拆解** — 交互式思维导图 + 章节功能分析
5. **观点分析** — 3-7 个核心观点的多维度剖析
6. **深度圆桌讨论** — 跨学科专家三轮对话
7. **认知拓展** — 与更大知识地图的连接
8. **启发追问** — 10 个高质量思考问题
9. **全书金句** — 20 条代表性金句 + 解读
10. **Final Takeaways** — 高密度总结

## 🌐 在线访问

推送后，你的知识库会发布到：

```
https://你的用户名.github.io/仓库名/
```

约 1 分钟后生效。

## 🔧 高级用法

### 修改分析 Prompt

编辑 `analysis_prompt.md` 文件，无需修改代码。

### 调整并发数

```bash
# 高速网络 + 付费账户可以提高到 5
python batch_analyze.py --dir 书本/ --workers 5

# 免费账户建议降到 2
python batch_analyze.py --dir 书本/ --workers 2
```

### 强制重新分析

```bash
# 单本书
python reading_skill.py 书名.epub --force

# 批量
python batch_analyze.py --dir 书本/ --force
```

## 📝 注意事项

1. **API 限流**：并发数不要超过 5，避免触发 rate limit
2. **文件命名**：支持中文书名，会自动生成对应的 HTML 文件
3. **去重机制**：已分析的书不会重复分析（除非用 `--force`）
4. **推送频率**：建议分析完一批书后统一推送，不要每本书推一次

## 🤝 贡献

欢迎提 Issue 和 PR！

## 📄 License

MIT

---

**Powered by GPT-5.4** | 生成时间：每本书约 5-6 分钟
