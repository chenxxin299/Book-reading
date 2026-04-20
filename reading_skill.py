"""
reading_skill.py
────────────────────────────────────────────────
核心工作流：
  epub/pdf  →  提取全文  →  GPT-5.4 深度分析  →  HTML 报告
用法：
  python reading_skill.py path/to/book.epub
  python reading_skill.py path/to/book.pdf
"""

import os
import sys
import re
import json
import hashlib
import argparse
from pathlib import Path
from datetime import datetime

from dotenv import load_dotenv
from loguru import logger
from openai import OpenAI

# ── 环境变量 ─────────────────────────────────────────────────
load_dotenv()
_client = None

def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        )
    return _client

MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4")

# ── 系统 Prompt ───────────────────────────────────────────────
# ── 系统 Prompt ───────────────────────────────────────────────
def _load_system_prompt() -> str:
    """从外部文件加载 SYSTEM_PROMPT，减少主文件体积"""
    prompt_file = Path(__file__).parent / "analysis_prompt.md"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8")
    # 兜底：如果文件不存在，返回简化版
    return "你是一位深度阅读分析师。请按照十大板块输出完整的 HTML 读书报告。"

SYSTEM_PROMPT = _load_system_prompt()


# ── 文本提取 ──────────────────────────────────────────────────

def extract_text_epub(path: str) -> str:
    import ebooklib
    from ebooklib import epub
    from bs4 import BeautifulSoup
    import warnings
    warnings.filterwarnings("ignore")

    book = epub.read_epub(path)
    chapters = []
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            html = item.get_content().decode("utf-8", errors="ignore")
            soup = BeautifulSoup(html, "lxml")
            text = soup.get_text(separator="\n", strip=True)
            if len(text.strip()) > 100:
                chapters.append(text)
    return "\n\n".join(chapters)


def extract_text_pdf(path: str) -> str:
    try:
        import pdfplumber
        text_parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                t = page.extract_text()
                if t:
                    text_parts.append(t)
        return "\n\n".join(text_parts)
    except ImportError:
        import pypdf
        reader = pypdf.PdfReader(path)
        return "\n\n".join(
            p.extract_text() for p in reader.pages if p.extract_text()
        )


def extract_book_text(path: str) -> tuple[str, str]:
    """返回 (书名, 全文)"""
    p = Path(path)
    stem = p.stem  # 文件名（不含扩展名）作为默认书名
    ext = p.suffix.lower()

    if ext == ".epub":
        logger.info(f"解析 epub: {p.name}")
        text = extract_text_epub(path)
    elif ext == ".pdf":
        logger.info(f"解析 pdf: {p.name}")
        text = extract_text_pdf(path)
    else:
        raise ValueError(f"不支持的格式: {ext}")

    logger.info(f"提取文本完成，共 {len(text):,} 字符")
    return stem, text


# ── 截断全文（避免超出上下文窗口）────────────────────────────

MAX_BOOK_CHARS = 120_000  # GPT-5.4 上下文充足，可适当放大

def truncate_text(text: str, max_chars: int = MAX_BOOK_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    # 取前 80% + 后 20%，保留开头和结尾的信息
    front = int(max_chars * 0.8)
    back  = int(max_chars * 0.2)
    logger.warning(f"全文过长（{len(text):,} 字符），截断至 {max_chars:,} 字符")
    return text[:front] + "\n\n[... 中间部分省略 ...]\n\n" + text[-back:]


# ── 调用 GPT 生成 HTML 报告 ──────────────────────────────────

def analyze_book(book_name: str, book_text: str) -> str:
    """调用 GPT-5.4（流式），返回完整 HTML 字符串"""
    client = get_client()
    trimmed = truncate_text(book_text)

    user_msg = f"""请对以下书籍进行深度分析，并输出完整的 HTML 报告。

书名：{book_name}
全文内容如下：
────────────────────────────────
{trimmed}
────────────────────────────────

重要要求：
1. 严格按照系统提示中的 10 个板块，每个板块都要深度展开，不要因为篇幅限制而压缩内容
2. 第4板块的全书结构图必须使用 markmap 交互式思维导图（使用 CDN：https://cdn.jsdelivr.net/npm/markmap-autoloader@0.16），不要用 ASCII 树或纯文本
3. 关键概念每个至少写 200 字分析，圆桌讨论每位嘉宾发言不少于 150 字，金句提取 20 条
4. 直接输出完整 HTML，从 <!DOCTYPE html> 开始，到 </html> 结束，不要有任何其他说明文字"""

    logger.info(f"调用 GPT（{MODEL}）进行深度分析，流式模式，请耐心等待...")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": user_msg},
    ]

    # 流式输出，避免长时间无响应导致 504
    chunks = []
    stream = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        max_tokens=32000,
        temperature=0.7,
        stream=True,
    )
    for chunk in stream:
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            chunks.append(delta)
            if len(chunks) % 200 == 0:
                logger.debug(f"  已接收 {len(chunks)} 个 chunk...")

    html = "".join(chunks).strip()

    # 清理可能的 markdown 代码块包裹
    if html.startswith("```"):
        html = re.sub(r"^```[a-z]*\n?", "", html)
        html = re.sub(r"\n?```$", "", html)

    logger.info(f"GPT 响应完成，HTML 长度: {len(html):,} 字符")

    # 注入强化 CSS（覆盖 GPT 可能生成的薄弱样式）
    html = inject_enhanced_css(html)
    return html


# ── CSS 强化注入 ─────────────────────────────────────────────

ENHANCED_CSS = """
/* ═══════════════════════════════════════════
   BOOK ANALYST — Enhanced Report Styles v4
   ═══════════════════════════════════════════ */

:root {
  --bg: #f4f1ec;
  --paper: #ffffff;
  --ink: #1a1f27;
  --ink2: #5a6272;
  --accent: #b85c10;
  --accent-soft: #fdf3ea;   /* 全底色用：暖橙奶白 */
  --accent-border: #e5b98a;
  --blue-soft: #f0f5fb;     /* 全底色用：冷蓝奶白 */
  --blue-border: #b0c8e4;
  --yellow-soft: #fefce8;   /* 全底色用：淡黄 */
  --yellow-border: #e5d070;
  --line: #e6e0d8;
  --radius: 10px;
  --shadow-sm: 0 1px 4px rgba(0,0,0,.05);
  --shadow-md: 0 3px 12px rgba(0,0,0,.08);
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
html { scroll-behavior: smooth; }
body {
  background: var(--bg);
  color: var(--ink);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
               "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
  font-size: 13px; line-height: 1.75;
}
a { color: inherit; text-decoration: none; }

/* ── 侧边栏 ── */
.sidebar {
  position: fixed; left: 0; top: 0; bottom: 0; width: 240px;
  background: #ece8e0; border-right: 1px solid var(--line);
  padding: 16px 10px 24px; overflow-y: auto; z-index: 100;
}
.brand {
  font-size: 11.5px; line-height: 1.5;
  padding: 8px 10px 10px; margin-bottom: 8px;
  border-bottom: 1px solid var(--line); color: #374151;
}
.brand .book-title { font-weight: 700; display: block; margin-bottom: 2px; }
.brand .book-author { color: var(--ink2); font-size: 11px; display: block; }
.toc a {
  display: flex; align-items: center; gap: 6px;
  padding: 7px 10px; margin: 2px 0; border-radius: 7px;
  font-size: 11.5px; color: #374151; line-height: 1.4; transition: background .15s;
}
.toc a:hover { background: #ddd8cf; }
.toc a.active { background: var(--accent-soft); color: var(--accent); font-weight: 600; }
.toc-num {
  display: inline-flex; align-items: center; justify-content: center;
  width: 18px; height: 18px; border-radius: 50%;
  background: var(--line); font-size: 10px; font-weight: 700;
  flex-shrink: 0; color: var(--ink2);
}
.toc a.active .toc-num { background: var(--accent); color: #fff; }

/* ── 主内容区 ── */
.main { margin-left: 240px; padding: 24px 28px 80px; }
.container { max-width: 920px; margin: 0 auto; }

/* ── Hero ── */
.hero {
  background: var(--paper);
  border: 1px solid var(--line); border-radius: 14px;
  padding: 24px 28px 18px; box-shadow: var(--shadow-md);
  margin-bottom: 16px; position: relative; overflow: hidden;
}
.hero::before {
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: var(--accent);
}
.hero h1 { font-size: 1.5rem; font-weight: 800; margin-bottom: 6px; line-height: 1.3; }
.hero .meta { color: var(--ink2); font-size: .85rem; margin-bottom: 12px; }
.hero .subtitle {
  border-left: 3px solid var(--accent-border);
  padding: 8px 12px; font-size: .88rem; line-height: 1.6; color: var(--ink2);
}

/* ── section-card ── */
.section-card {
  background: var(--paper); border: 1px solid var(--line);
  border-radius: 14px; box-shadow: var(--shadow-sm);
  margin-bottom: 20px; overflow: hidden;
}
.section-header {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 20px; border-bottom: 1px solid var(--line);
  background: #f8f5f0;
}
.section-num {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 7px;
  background: var(--accent); color: #fff;
  font-size: 11px; font-weight: 700; flex-shrink: 0;
}
.section-title { font-size: .95rem; font-weight: 800; color: var(--ink); }
.section-body { padding: 18px 22px; }

/* ── 标题层级 ── */
h2 {
  font-size: .97rem; font-weight: 800;
  margin: 20px 0 10px;
  padding: 7px 12px;
  border-left: 3px solid var(--accent);
  background: #f8f5f0;
  border-radius: 0 6px 6px 0;
}
h3 {
  font-size: .92rem; font-weight: 700;
  margin: 16px 0 7px; padding-bottom: 4px;
  border-bottom: 1px solid var(--line);
  color: var(--ink);
}
h4 { font-size: .87rem; font-weight: 600; margin: 10px 0 5px; color: var(--ink2); }
p  { font-size: .875rem; margin: 7px 0; }
ul, ol { padding-left: 20px; }
li { font-size: .875rem; margin: 5px 0; line-height: 1.7; }

/* strong → 仅加粗，不加颜色不加底纹 */
strong, b { font-weight: 700; }
mark { background: #fef9c3; color: var(--ink); padding: 1px 3px; border-radius: 3px; }

/* ── 通用卡片 ── */
.card {
  background: var(--paper); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 14px 16px; margin-bottom: 12px;
}
/* 观点/章节模块：白底 + 左侧橙边框（结构性，不涂色） */
.card-accent {
  background: var(--paper);
  border: 1px solid var(--line);
  border-left: 4px solid var(--accent);
  border-radius: var(--radius); padding: 14px 16px; margin-bottom: 12px;
}

/* ══════════════════════════════════════
   颜色原则：有颜色 = 整个框都有底色，不搞半边
   暖色系 = 橙系（重点/警示）
   冷色系 = 蓝系（信息/参考）
   黄色系 = 洞见/摘要
   ══════════════════════════════════════ */

/* callout：暖橙底 + 匹配边框（全框着色） */
.callout {
  background: var(--accent-soft);
  border: 1px solid var(--accent-border);
  padding: 11px 14px; border-radius: var(--radius); margin: 10px 0;
  font-size: .875rem;
}
/* callout-yellow：淡黄底 */
.callout-yellow {
  background: var(--yellow-soft);
  border: 1px solid var(--yellow-border);
  padding: 11px 14px; border-radius: var(--radius); margin: 10px 0;
  font-size: .875rem;
}
/* callout-blue：冷蓝底 */
.callout-blue {
  background: var(--blue-soft);
  border: 1px solid var(--blue-border);
  padding: 11px 14px; border-radius: var(--radius); margin: 10px 0;
  font-size: .875rem;
}
.callout-green {
  background: #f0faf4; border: 1px solid #a7d9b8;
  padding: 11px 14px; border-radius: var(--radius); margin: 10px 0;
  font-size: .875rem;
}

/* 概念框：暖橙底（全框着色） */
.concept-box {
  background: var(--accent-soft);
  border: 1px solid var(--accent-border);
  border-radius: var(--radius);
  padding: 12px 14px; margin: 10px 0;
}
.concept-box .concept-title {
  font-size: .8rem; font-weight: 700; color: var(--accent);
  text-transform: uppercase; letter-spacing: .05em;
  margin-bottom: 6px; padding-bottom: 5px;
  border-bottom: 1px dashed var(--accent-border);
}

/* 张力对比框：两侧皆有底色，中间深色 VS 柱 */
.tension-box {
  display: grid; grid-template-columns: 1fr 36px 1fr;
  border: 1px solid var(--line); border-radius: var(--radius);
  overflow: hidden; margin: 12px 0;
}
.tension-box .t-side { padding: 12px 14px; font-size: .855rem; line-height: 1.65; }
.tension-box .t-side:first-child { background: var(--blue-soft); }
.tension-box .t-side:last-child  { background: var(--accent-soft); }
.tension-box .t-vs {
  display: flex; align-items: center; justify-content: center;
  background: #3a3a3a; color: #fff;
  font-size: 9px; font-weight: 800; letter-spacing: 1px;
  writing-mode: vertical-lr;
}
.tension-box .t-label {
  font-size: .75rem; font-weight: 700; margin-bottom: 5px;
  color: var(--ink2); text-transform: uppercase; letter-spacing: .04em; display: block;
}

/* 参考框：冷蓝底（全框着色） */
.ref-box {
  background: var(--blue-soft);
  border: 1px solid var(--blue-border);
  border-radius: var(--radius);
  padding: 10px 12px; margin: 8px 0;
  display: flex; gap: 10px; align-items: flex-start;
}
.ref-box .ref-icon { font-size: 1rem; flex-shrink: 0; margin-top: 1px; }
.ref-box .ref-content { flex: 1; }
.ref-box .ref-title { font-weight: 700; font-size: .86rem; margin-bottom: 2px; }
.ref-box .ref-desc  { font-size: .81rem; color: var(--ink2); }

/* ── 金句 ── */
.quote {
  background: #fafaf8; border: 1px solid var(--line);
  border-radius: var(--radius); padding: 12px 16px 10px 30px;
  margin: 8px 0; position: relative;
}
.quote::before {
  content: '"'; position: absolute; top: 2px; left: 8px;
  font-size: 2rem; color: var(--accent-border); line-height: 1;
  font-family: Georgia, serif;
}
.quote .source { font-size: .76rem; color: var(--ink2); margin-top: 5px; }

/* ── Final Takeaway：白底，整洁列表，不用黑色条块 ── */
.take {
  background: var(--paper);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  padding: 16px 20px; margin: 10px 0;
}
.take ol, .take ul { padding-left: 20px; }
.take li {
  font-size: .875rem; margin: 8px 0; padding-bottom: 8px;
  border-bottom: 1px solid var(--line); line-height: 1.7;
}
.take li:last-child { border-bottom: none; padding-bottom: 0; }
.take p { font-size: .875rem; margin: 7px 0; }
.take strong, .take b { font-weight: 700; color: var(--accent); }

/* ── 圆桌对话 ── */
.roundtable-round {
  background: #f8f7f4; border: 1px solid var(--line);
  border-radius: var(--radius); padding: 14px 16px; margin-bottom: 12px;
}
.round-title {
  font-size: .76rem; font-weight: 700; color: var(--ink2);
  text-transform: uppercase; letter-spacing: .08em;
  margin-bottom: 10px; padding-bottom: 5px;
  border-bottom: 1px solid var(--line);
}
.dialogue { display: flex; gap: 10px; margin: 10px 0; align-items: flex-start; }
.dialogue-avatar {
  flex-shrink: 0; width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 11px; font-weight: 700; color: #fff;
}
.dialogue-bubble {
  flex: 1; background: var(--paper); border: 1px solid var(--line);
  border-radius: 10px; padding: 9px 13px;
}
.dialogue-name { font-size: 11px; font-weight: 700; color: var(--accent); margin-bottom: 3px; }
.dialogue-bubble p  { font-size: .86rem; }
.dialogue-bubble ul { font-size: .86rem; }
.dialogue-bubble li { margin: 3px 0; }
.round-insight {
  margin-top: 8px; padding: 9px 12px;
  background: var(--yellow-soft); border: 1px solid var(--yellow-border);
  border-radius: 6px; font-size: .82rem; color: var(--ink);
}

/* ── Grid ── */
.grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.grid-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 12px; }

/* ── 标签 ── */
.tag {
  display: inline-block; background: #f0ece5; color: var(--ink2);
  border: 1px solid var(--line);
  padding: 2px 8px; border-radius: 999px; font-size: 11px; margin: 2px 3px;
}

/* ── 表格 ── */
table { width: 100%; border-collapse: collapse; font-size: .84rem; margin: 10px 0; }
th { background: #f2ede6; font-weight: 700; }
th, td { border: 1px solid var(--line); padding: 7px 11px; text-align: left; }
tr:nth-child(even) td { background: #faf8f4; }

/* ── Markmap ── */
.markmap {
  width: 100% !important; height: 520px !important;
  display: block; border: 1px solid var(--line);
  border-radius: var(--radius); overflow: hidden; background: #fff;
}
.markmap svg { width: 100% !important; height: 100% !important; }

/* ── 响应式 ── */
@media (max-width: 900px) {
  .sidebar { display: none; }
  .main { margin-left: 0; padding: 16px; }
  .grid-2, .grid-3 { grid-template-columns: 1fr; }
  .tension-box { grid-template-columns: 1fr; }
  .tension-box .t-vs { writing-mode: horizontal-tb; padding: 6px; }
}
"""


def inject_enhanced_css(html: str) -> str:
    """替换或注入强化 CSS，同时修复 markmap 容器宽度。"""
    # 替换 <style>...</style> 中的内容（保留其他 <link> 和外部 CSS CDN）
    if re.search(r'<style[^>]*>', html, re.IGNORECASE):
        html = re.sub(
            r'<style[^>]*>.*?</style>',
            f'<style>{ENHANCED_CSS}</style>',
            html, count=1, flags=re.DOTALL | re.IGNORECASE
        )
    else:
        html = html.replace('</head>', f'<style>{ENHANCED_CSS}</style>\n</head>', 1)

    # 强制 markmap div 样式
    html = re.sub(
        r'<div\s+class="markmap"[^>]*>',
        '<div class="markmap" style="width:100%;height:520px;display:block;">',
        html
    )

    return html


# ── 元数据提取（用于门户网站）──────────────────────────────

def extract_meta(book_name: str, html: str) -> dict:
    """从 HTML 中提取书名、副标题等，写入 meta.json"""
    # 简单从 <title> 标签或 <h1> 提取
    title_match = re.search(r"<title>(.*?)</title>", html, re.IGNORECASE)
    h1_match    = re.search(r"<h1[^>]*>(.*?)</h1>",  html, re.IGNORECASE | re.DOTALL)

    title = title_match.group(1).strip() if title_match else book_name
    title = re.sub(r"<[^>]+>", "", title)  # 去掉内嵌标签

    return {
        "book_name": book_name,
        "title": title,
        "filename": _safe_filename(book_name) + ".html",
        "analyzed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "chars": len(html),
    }


def _safe_filename(name: str) -> str:
    """书名 → 安全文件名（优先保留中文，去掉文件系统禁止字符）"""
    # 去掉 Windows/Unix 文件系统中不允许的字符
    cleaned = re.sub(r'[\\/:*?"<>|]', '', name).strip()
    if cleaned:
        return cleaned[:60]
    # 兜底：尝试 pinyin
    try:
        from pypinyin import lazy_pinyin
        name_en = "_".join(lazy_pinyin(name))
    except ImportError:
        name_en = re.sub(r"[^\w\s-]", "", name, flags=re.ASCII)
        name_en = re.sub(r"[\s]+", "_", name_en)
    if not name_en.strip("_"):
        name_en = "book_" + hashlib.md5(name.encode()).hexdigest()[:8]
    return name_en[:60]


# ── 保存输出 ────────────────────────────────────────────────

def save_report(book_name: str, html: str, output_dir: str = "output") -> Path:
    out = Path(output_dir)
    out.mkdir(exist_ok=True)

    filename = _safe_filename(book_name) + ".html"
    report_path = out / filename
    report_path.write_text(html, encoding="utf-8")
    logger.success(f"HTML 报告已保存: {report_path}")

    # 写入元数据 JSON（供门户网站读取）
    meta = extract_meta(book_name, html)
    meta_path = out / (filename.replace(".html", "_meta.json"))
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"元数据已保存: {meta_path}")

    return report_path


# ── 缓存：避免重复分析同一本书 ──────────────────────────────

def _book_hash(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def is_already_analyzed(path: str, output_dir: str = "output") -> bool:
    book_name, _ = Path(path).stem, None
    filename = _safe_filename(Path(path).stem) + ".html"
    report_path = Path(output_dir) / filename
    if report_path.exists():
        logger.info(f"已有分析结果，跳过: {report_path}")
        return True
    return False


# ── 主流程 ───────────────────────────────────────────────────

def run(book_path: str, output_dir: str = "output", force: bool = False) -> Path:
    """
    完整分析流程入口。
    返回生成的 HTML 报告路径。
    """
    if not force and is_already_analyzed(book_path, output_dir):
        book_name = Path(book_path).stem
        return Path(output_dir) / (_safe_filename(book_name) + ".html")

    book_name, book_text = extract_book_text(book_path)
    html = analyze_book(book_name, book_text)
    return save_report(book_name, html, output_dir)


# ── CLI ──────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="深度读书分析 → HTML 报告")
    parser.add_argument("book", help="epub 或 pdf 文件路径")
    parser.add_argument("--output", "-o", default="output", help="输出目录（默认 output/）")
    parser.add_argument("--force",  "-f", action="store_true", help="强制重新分析（忽略缓存）")
    parser.add_argument("--verbose","-v", action="store_true", help="显示详细日志")
    args = parser.parse_args()

    logger.remove()
    logger.add(sys.stderr, level="DEBUG" if args.verbose else "INFO",
               format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
               colorize=True)

    report_path = run(args.book, args.output, args.force)
    print(f"\n报告已生成: {report_path}")
