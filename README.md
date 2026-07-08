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
- 提供 Codex 原生 widget 面板，不依赖 `file://` 或本地 HTTP 服务
- 保留静态 HTML 生成能力，方便开发调试
- 保留可选本地服务预览，适合手动放到右侧内置浏览器查看

## 目录结构

这个仓库本身就是插件根目录：

```text
skill-manager/
├── .codex-plugin/
│   └── plugin.json
├── .mcp.json
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

> 注意：把插件加入 `~/.agents/plugins/marketplace.json` 只是让它出现在 Codex 的插件列表里，不等于已经启用。还需要在 Codex 插件页里安装/启用一次。

### 1. 复制插件到本机插件目录

从这个仓库根目录执行：

```bash
mkdir -p ~/plugins
cp -R . ~/plugins/skill-manager
```

### 2. 加入个人插件市场

把下面这一项加入 `~/.agents/plugins/marketplace.json` 的 `plugins` 数组：

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

如果 `~/.agents/plugins/marketplace.json` 还不存在，可以直接创建这个文件：

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

### 3. 在 Codex 里安装/启用

完成上面两步后，重启或刷新 Codex，然后打开 Codex 的插件页面。

你应该能在个人插件市场里看到 `skill-manager`。点击安装/启用后，再新开一个 Codex 对话。

新对话里说：

```text
打开 skill 管理器
```

这时 Codex 才会加载插件贡献的 skill 和 MCP 工具。

## 安装是否成功

安装成功后，通常会出现类似这样的缓存目录：

```text
~/.codex/plugins/cache/personal/skill-manager/
```

如果这个目录没有出现，说明插件大概率只是被加入了 marketplace，还没有在 Codex 里真正安装/启用。

成功启用后，说“打开 skill 管理器”时，Codex 应该能看到并调用：

```text
render_skill_manager_widget
```

如果 Codex 回复“没有看到 skill 管理器的专用工具”，基本就是当前对话还没加载到插件。请回到插件页确认已安装/启用，然后新开一个对话再试。

## 使用方式

在 Codex 里说：

```text
打开 skill 管理器
```

Codex 会运行：

`render_skill_manager_widget`

这个 MCP 工具会重新扫描当前本机 skills，并返回：

```text
ui://widget/skill-manager/dashboard.html
```

Codex 会把它作为原生 widget 面板打开。这个流程不会经过 `file://`，也不需要你手动启动 `localhost` 服务。

同时，它会自动刷新一个备用静态页面：

```text
assets/skill-dashboard.html
```

如果你想放到右侧内置浏览器里单独看，可以打开右侧浏览器后自己复制这个 HTML 路径或地址。插件不会默认启动本地服务，也不会默认自动控制浏览器。

以后如果你安装、删除或更新了 skill，再对 Codex 说一次：

```text
打开 skill 管理器
```

它就会重新扫描，并同时刷新 widget 和这个静态 HTML。

## 开发备用：静态页面

如果 MCP widget 不可用，或你只是想调试 HTML，可以在插件根目录运行：

```bash
python3 scripts/open_skill_manager.py
```

## 可选：本地服务预览

如果你明确想把 dashboard 放到右侧内置浏览器里看，可以在插件根目录运行：

```bash
python3 scripts/open_skill_manager.py --serve --port 8765
```

它会先刷新 `assets/skill-dashboard.html`，再提供一个本机地址：

```text
http://127.0.0.1:8765/skill-dashboard.html
```

这个只是备用预览方式，不是默认打开路径。

或直接生成静态页面：

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

当前提供四个工具：

- `render_skill_manager_widget`：打开 Codex 原生 Skill 管理器面板
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
- 可以通过一句“打开 skill 管理器”刷新并打开原生 widget
- 静态 HTML 仍可作为开发备用路径
