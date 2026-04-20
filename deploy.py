"""
deploy.py
────────────────────────────────────────────────
将 output/ 目录推送到 GitHub Pages，让知识库可以在线访问。

前置条件：
  1. 在 GitHub 创建一个 repo（如 my-book-notes）
  2. 在 .env 里设置 GITHUB_REPO=https://github.com/你的用户名/my-book-notes.git
  3. 配置好 git 凭据（或用 SSH key / GitHub Token）

推送策略：
  - output/ 的内容推送到 repo 的 gh-pages 分支
  - GitHub 会自动将 gh-pages 分支发布为静态网站
  - 访问地址：https://你的用户名.github.io/my-book-notes/

用法：
  python deploy.py                    # 推送 output/ 到 gh-pages
  python deploy.py --output-dir out   # 指定输出目录
  python deploy.py --message "新增书目：XXX"   # 自定义 commit 信息
"""

import os
import sys
import subprocess
import argparse
import shutil
from pathlib import Path
from datetime import datetime

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from loguru import logger


def run_cmd(cmd: list[str], cwd: str | None = None, check: bool = True) -> str:
    """执行命令，返回 stdout，出错时打印 stderr"""
    result = subprocess.run(
        cmd, cwd=cwd,
        capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"命令失败: {' '.join(cmd)}\n"
            f"stdout: {result.stdout}\n"
            f"stderr: {result.stderr}"
        )
    return result.stdout.strip()


def deploy(output_dir: str = "output", commit_message: str | None = None):
    """
    将 output/ 内容推送到 GitHub Pages（gh-pages 分支）。
    使用 git worktree 避免污染主分支。
    """
    # ── 读取配置 ──────────────────────────────────────────────
    repo_url = os.getenv("GITHUB_REPO")
    if not repo_url:
        logger.error(
            "未设置 GITHUB_REPO 环境变量\n"
            "请在 .env 文件中添加：\n"
            "  GITHUB_REPO=https://github.com/你的用户名/仓库名.git\n"
            "  （或使用 SSH：git@github.com:你的用户名/仓库名.git）"
        )
        sys.exit(1)

    output_path = Path(output_dir).resolve()
    if not output_path.exists():
        logger.error(f"输出目录不存在: {output_path}")
        sys.exit(1)

    html_files = list(output_path.glob("*.html"))
    if not html_files:
        logger.error(f"output/ 目录中没有 HTML 文件，请先运行分析")
        sys.exit(1)

    logger.info(f"准备推送 {len(html_files)} 个 HTML 文件到 GitHub Pages...")
    logger.info(f"目标仓库: {repo_url}")

    # ── 检查本地是否已有 git repo ──────────────────────────────
    project_dir = Path(__file__).parent.resolve()
    git_dir = project_dir / ".git"

    if not git_dir.exists():
        logger.info("初始化本地 git 仓库...")
        run_cmd(["git", "init"], cwd=str(project_dir))
        run_cmd(["git", "remote", "add", "origin", repo_url], cwd=str(project_dir))
    else:
        # 确认 remote 正确
        try:
            current_remote = run_cmd(
                ["git", "remote", "get-url", "origin"], cwd=str(project_dir)
            )
            if current_remote != repo_url:
                logger.info(f"更新 remote: {current_remote} → {repo_url}")
                run_cmd(["git", "remote", "set-url", "origin", repo_url], cwd=str(project_dir))
        except RuntimeError:
            run_cmd(["git", "remote", "add", "origin", repo_url], cwd=str(project_dir))

    # ── 用临时目录构建纯净的 gh-pages 提交 ───────────────────
    tmp_dir = project_dir / ".gh-pages-tmp"
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
    tmp_dir.mkdir()

    try:
        # 初始化一个独立的 git repo（只含 output 内容，历史干净）
        run_cmd(["git", "init"], cwd=str(tmp_dir))
        run_cmd(["git", "checkout", "-b", "gh-pages"], cwd=str(tmp_dir))
        run_cmd(["git", "remote", "add", "origin", repo_url], cwd=str(tmp_dir))

        # 拷贝 output/ 内容到临时目录
        for item in output_path.iterdir():
            dst = tmp_dir / item.name
            if item.is_file():
                shutil.copy2(item, dst)
            elif item.is_dir():
                shutil.copytree(item, dst)

        # 生成 commit 信息
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        book_names = [f.stem for f in html_files if f.stem != "index"]
        if commit_message is None:
            commit_message = f"📚 更新读书知识库 {now}（{len(book_names)} 本）"

        # 提交
        run_cmd(["git", "config", "user.email", "deploy@book-analyst"], cwd=str(tmp_dir))
        run_cmd(["git", "config", "user.name", "Book Analyst"], cwd=str(tmp_dir))
        run_cmd(["git", "add", "."], cwd=str(tmp_dir))
        run_cmd(["git", "commit", "-m", commit_message], cwd=str(tmp_dir))

        # 强制推送到 gh-pages 分支（每次都是全量替换）
        logger.info("推送到 gh-pages 分支...")
        run_cmd(
            ["git", "push", "origin", "gh-pages", "--force"],
            cwd=str(tmp_dir)
        )

        logger.success(
            f"\n✅ 推送成功！\n"
            f"   GitHub Pages 地址（约 1 分钟后生效）：\n"
            f"   {_get_pages_url(repo_url)}"
        )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def _get_pages_url(repo_url: str) -> str:
    """从 repo URL 推断 GitHub Pages 地址"""
    import re
    # HTTPS: https://github.com/user/repo.git
    m = re.search(r"github\.com[:/](.+?)/(.+?)(?:\.git)?$", repo_url)
    if m:
        user, repo = m.group(1), m.group(2)
        return f"https://{user}.github.io/{repo}/"
    return "（请在 GitHub 仓库 Settings → Pages 查看地址）"


# ── CLI ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="将读书知识库推送到 GitHub Pages")
    parser.add_argument("--output-dir", "-d", default="output", help="报告目录（默认 output/）")
    parser.add_argument("--message",    "-m", default=None,    help="自定义 commit 信息")
    args = parser.parse_args()

    logger.remove()
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level:<8}</level> | {message}",
        colorize=True,
    )

    deploy(args.output_dir, args.message)
