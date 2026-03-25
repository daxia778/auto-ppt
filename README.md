<![CDATA[<div align="center">

# 🎯 Auto-PPT

### NotebookLM 智能演示文稿生成器

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Playwright](https://img.shields.io/badge/Playwright-Automation-2EAD33?style=for-the-badge&logo=playwright&logoColor=white)](https://playwright.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)
[![Release](https://img.shields.io/github/v/release/daxia778/auto-ppt?style=for-the-badge&color=blue)](https://github.com/daxia778/auto-ppt/releases)

**一键生成专业 PPT — 让 Google NotebookLM 的 AI 为你做设计**

[快速开始](#-快速开始) · [功能特性](#-功能特性) · [使用指南](#-使用指南) · [配置说明](#️-配置说明)

---

</div>

## ✨ 功能特性

| 特性 | 说明 |
|:---:|:---|
| 🤖 **AI 驱动** | 利用 Google NotebookLM 的 Studio 面板，自动生成精美演示文稿 |
| 🎨 **官方品质** | 直接下载 NotebookLM 生成的 PPTX，享受 Google 级别的排版设计 |
| 🔐 **持久登录** | 基于 Playwright 持久化上下文，一次登录长期免密 |
| 📄 **双模式** | Studio 模式 (推荐) + 本地解析 Fallback 模式，稳定可靠 |
| ⚙️ **可配置** | YAML 配置文件，灵活自定义 Prompt、超时、输出路径 |

## 📦 快速开始

### 环境要求

- **Python** 3.10+
- **Google 账号** (用于访问 NotebookLM)

### 安装

```bash
# 1. 克隆仓库
git clone https://github.com/daxia778/auto-ppt.git
cd auto-ppt

# 2. 安装依赖
pip install -r requirements.txt

# 3. 安装 Playwright 浏览器
playwright install chromium
```

### 首次使用：登录 Google

```bash
python main.py --login-only
```

> 会弹出浏览器窗口，请手动登录你的 Google 账号。登录态会保存在 `chrome_profile/` 目录中，后续无需重复登录。

## 🚀 使用指南

### Studio 模式 (默认推荐)

```bash
# 基本用法 — 自动在 Studio 面板生成并下载 PPTX
python main.py --topic "人工智能在医疗领域的应用" --pages 8
```

此模式会自动执行以下流程：

```
创建 Notebook → 发送 Prompt → 点击 Studio「演示文稿」
     → 等待 AI 生成 (1~2 分钟) → 自动下载 PPTX
```

### Fallback 模式

```bash
# 使用本地解析 + python-pptx 生成 (不依赖 Studio 面板)
python main.py --topic "区块链技术" --pages 5 --no-use-studio
```

### 添加素材

```bash
# 从文件中读取素材作为参考
python main.py --topic "年度总结" --pages 10 --source-file ./my_notes.txt

# 直接传入文本
python main.py --topic "产品发布" --pages 6 --source-text "我们的新产品特性包括..."
```

### 离线测试

```bash
# 不启动浏览器，测试解析和生成逻辑
python main.py --parse-test --topic "测试主题"
```

## ⚙️ 配置说明

编辑 `config.yaml` 自定义行为：

```yaml
# 浏览器配置
browser:
  headless: false          # 是否无头模式
  slow_mo: 500             # 操作间隔 (ms)
  download_dir: "./output" # PPTX 下载目录

# Studio 面板配置
studio:
  generation_timeout: 180000  # 生成超时 (ms)

# Prompt 模板 (可自定义)
prompts:
  generate_outline: |
    请帮我生成一个关于「{topic}」的PPT大纲，共 {pages} 页...
```

## 📂 项目结构

```
auto-ppt/
├── main.py              # 主入口 & CLI
├── config.yaml          # 配置文件
├── requirements.txt     # Python 依赖
├── src/
│   ├── auth.py          # Google 登录管理
│   ├── notebook.py      # NotebookLM 页面自动化 + Studio 操作
│   ├── parser.py        # Markdown 解析器 (Fallback 模式)
│   └── generator.py     # python-pptx 生成器 (Fallback 模式)
├── output/              # 生成的 PPTX 文件
└── chrome_profile/      # 浏览器登录态 (不要提交!)
```

## 🔧 CLI 参数一览

| 参数 | 默认值 | 说明 |
|:---|:---|:---|
| `--topic` | `"测试生成PPT"` | PPT 的主题/标题 |
| `--pages` | `5` | 希望生成的 PPT 页数 |
| `--source-text` | - | 直接提供素材文本 |
| `--source-file` | - | 从文件中读取素材 |
| `--login-only` | - | 仅执行登录流程 |
| `--parse-test` | - | 离线测试模式 |
| `--use-studio` / `--no-use-studio` | `True` | Studio 模式开关 |

## 📝 注意事项

- 🔒 `chrome_profile/` 目录包含你的 Google 登录 Cookie，请勿分享或上传
- 🌐 需要稳定的网络连接访问 `notebooklm.google.com`
- ⏱️ Studio 生成通常需要 1-2 分钟，请耐心等待
- 🔄 如果 Google 更新了 NotebookLM 界面，选择器可能需要更新

## 📄 License

[MIT License](LICENSE) © 2026 daxia778
]]>
