# Skill Manager for Codex

一个本地 Codex 插件，用来可视化查看、搜索、筛选和审查你已经安装的 Codex skills。

它的目标很简单：

> 对 Codex 说“打开 skill 管理器”，就能刷新并看到最新的本地 skills 清单。

## 功能

- 扫描本机 Codex skills：
  - `~/.codex/skills`
  - `~/.codex/plugins/cache`
- 可视化展示 skill 名称、来源、路径、原始描述和一句话用途提示
- 支持中文搜索关键词，比如 `图片`、`部署`、`视频`、`Figma`、`小红书`
- 支持来源筛选：
  - 系统内置 skills
  - 用户单个 skill
  - 本地集合，比如 `ai-berkshire`、`uzi`
  - 官方插件、个人插件、运行时插件
- 支持状态筛选：
  - 状态正常
  - 描述偏短
  - 名称重复
  - 名称不规范
- 提供 MCP 数据层，后续可以接成真正的 Codex 原生面板

## 目录结构

这个仓库本身就是插件根目录：

```text
skill-manager/
├── .codex-plugin/
│   └── plugin.json
├── .mcp.json
├── .app.json
├── assets/
│   └── skill-dashboard.html
├── scripts/
│   ├── open_skill_manager.py
│   └── skill_manager_mcp.py
└── skills/
    └── skill-manager/
        └── SKILL.md
```

## 安装到本机 Codex

从仓库根目录执行：

```bash
mkdir -p ~/plugins
cp -R . ~/plugins/skill-manager
```

然后把下面这一项加入 `~/.agents/plugins/marketplace.json` 的 `plugins` 数组：

```json
{
  "name": "skill-manager",
  "source": {
    "source": "local",
    "path": "./plugins/skill-manager"
  },
  "policy": {
    "installation": "AVAILABLE",
    "authentication": "ON_INSTALL"
  },
  "category": "Productivity"
}
```

如果 `~/.agents/plugins/marketplace.json` 还不存在，可以创建：

```json
{
  "name": "personal",
  "interface": {
    "displayName": "Personal"
  },
  "plugins": [
    {
      "name": "skill-manager",
      "source": {
        "source": "local",
        "path": "./plugins/skill-manager"
      },
      "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
      },
      "category": "Productivity"
    }
  ]
}
```

安装后，重启或刷新 Codex，让插件被重新加载。

## 使用方式

在 Codex 里说：

```text
打开 skill 管理器
```

Codex 会运行：

```bash
python3 scripts/open_skill_manager.py
```

这个脚本会重新扫描当前本机 skills，生成最新 dashboard，并输出本地页面地址。

也可以手动运行：

```bash
cd ~/plugins/skill-manager
python3 scripts/open_skill_manager.py
```

输出示例：

```json
{
  "path": "/Users/you/plugins/skill-manager/assets/skill-dashboard.html",
  "url": "file:///Users/you/plugins/skill-manager/assets/skill-dashboard.html",
  "summary": {
    "total": 116
  }
}
```

把 `url` 放到浏览器里打开即可。

## 直接生成静态页面

在插件根目录运行：

```bash
python3 scripts/skill_manager_mcp.py --write-dashboard assets/skill-dashboard.html
```

## MCP 工具

插件暴露了一个 MCP stdio server：

```json
{
  "mcpServers": {
    "skill-manager": {
      "command": "python3",
      "args": ["./scripts/skill_manager_mcp.py"],
      "cwd": "."
    }
  }
}
```

当前提供三个工具：

- `list_skills`：扫描并返回 skills 元数据
- `read_skill`：按名称或路径读取一个 `SKILL.md`
- `write_dashboard`：重新生成静态 dashboard

## 上传到 GitHub

在本目录，也就是插件根目录里执行：

```bash
git init
git add .
git commit -m "Add Codex skill manager plugin"
```

在 GitHub 创建一个空仓库后，执行：

```bash
git branch -M main
git remote add origin git@github.com:<your-name>/<repo-name>.git
git push -u origin main
```

如果你使用 HTTPS：

```bash
git remote add origin https://github.com/<your-name>/<repo-name>.git
git push -u origin main
```

## 当前状态

这是第一版可用形态：

- 已经是一个合法 Codex 插件
- 可以作为个人插件安装
- 可以通过一句“打开 skill 管理器”刷新 dashboard
- UI 目前是静态 HTML

后续可以继续升级成真正的 Codex 原生 app 面板。
