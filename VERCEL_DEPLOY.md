# Vercel 部署指南

## 方式一：通过 Vercel 网站部署（推荐，最简单）

1. **注册 Vercel 账号**
   - 访问 https://vercel.com
   - 用 GitHub 账号登录（一键授权）

2. **导入项目**
   - 点击 "Add New Project"
   - 选择你的 GitHub 仓库：`chenxxin299/Book-reading`
   - 点击 "Import"

3. **配置项目**
   - Framework Preset: 选择 "Other"
   - Root Directory: 留空（使用根目录）
   - Build Command: 留空
   - Output Directory: `output`
   - Install Command: 留空

4. **部署**
   - 点击 "Deploy"
   - 等待 1-2 分钟，完成！

5. **访问地址**
   - Vercel 会自动分配一个域名：`your-project.vercel.app`
   - 每次推送代码到 GitHub，Vercel 会自动重新部署

---

## 方式二：通过命令行部署

```bash
# 1. 安装 Vercel CLI
npm install -g vercel

# 2. 登录
vercel login

# 3. 部署（在项目根目录运行）
vercel --prod

# 4. 后续更新（每次分析完新书后运行）
python auto_analyze.py --once && vercel --prod
```

---

## 自动化部署流程

现在的工作流：

```bash
# 1. 把书放进"书本"目录
cp 新书.epub 书本/

# 2. 自动分析 + 推送到 GitHub
python auto_analyze.py --once

# 3. Vercel 自动检测到 GitHub 更新，自动重新部署
#    无需手动操作，约 1 分钟后网站更新
```

---

## 优势对比

| 特性 | GitHub Pages | Vercel |
|---|---|---|
| 国内访问速度 | 较慢 | 快 |
| 自动部署 | 需手动推送 | 推送即部署 |
| 自定义域名 | 支持 | 支持 |
| HTTPS | 自动 | 自动 |
| 成本 | 免费 | 免费 |

---

## 绑定自定义域名（可选）

如果你有自己的域名（如 `book.example.com`）：

1. 在 Vercel 项目设置里添加域名
2. 在域名服务商添加 CNAME 记录：
   ```
   book.example.com  →  cname.vercel-dns.com
   ```
3. 等待 DNS 生效（约 10 分钟）

---

## 当前状态

- ✅ `vercel.json` 已配置
- ✅ GitHub 仓库已推送
- ⏳ 等待你在 Vercel 网站导入项目

**下一步：访问 https://vercel.com 用 GitHub 登录，导入 `Book-reading` 仓库即可。**
