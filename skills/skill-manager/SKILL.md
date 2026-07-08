---
name: skill-manager
description: Use this skill when the user says "打开 skill 管理器", "打开技能管理器", "open skill manager", or wants to browse, inspect, search, audit, visualize, refresh, summarize, or manage local Codex skills; compare skill descriptions; find broken or missing SKILL.md files; generate a skill inventory; or prepare data for a visual skill manager plugin.
---

# Skill Manager

## Purpose

Help the user understand what Codex skills are available locally and how they are likely to trigger.

Use the plugin's MCP server to scan skill roots and open the native widget view, then summarize the inventory in a way that helps the user decide which skills are useful, stale, duplicated, broken, or worth improving.

## Data Layer

The scanner lives at:

`scripts/skill_manager_mcp.py`

It can be used in four ways:

- as a plugin MCP stdio server through `.mcp.json`
- as a native Codex widget launcher through the `render_skill_manager_widget` MCP tool
- as a direct JSON exporter with `--dump-json`
- as a static dashboard generator with `--write-dashboard <path>`

Use `render_skill_manager_widget` when the user asks to open or refresh the Skill Manager. It returns the widget resource `ui://widget/skill-manager/dashboard.html` through `openai/outputTemplate`, so Codex can render the panel without `file://` or a local HTTP server.

The same tool also writes a static fallback HTML file to:

`assets/skill-dashboard.html`

Tell the user this HTML was regenerated. If they want a separate browser view, they can open the right-side browser and copy the generated HTML path or URL themselves. Do not start a local HTTP server just to show the dashboard.

The legacy launcher lives at:

`scripts/open_skill_manager.py`

Use it only as a development fallback when the MCP widget path is unavailable.

## Default Scan Roots

Unless the user gives specific roots, scan:

- `~/.codex/skills`
- `~/.codex/plugins/cache`

The scanner finds folders that contain `SKILL.md`, reads frontmatter, and returns metadata rather than loading every full skill body into the conversation.

## Workflow

When the user asks to open the Skill Manager:

1. Call the plugin MCP tool `render_skill_manager_widget`.
2. Let Codex render the returned `ui://widget/skill-manager/dashboard.html` widget.
3. Tell the user the Skill Manager was refreshed from the latest local skills.
4. Tell the user the fallback HTML path returned by the tool.
5. If the user installs or updates skills later, tell them to say "打开 skill 管理器" again to regenerate both the widget data and fallback HTML.

Do not use the browser-control skill to open the generated file automatically unless the user explicitly asks. Do not start a temporary local web server as the default path.

When the user asks to inspect or audit skills:

1. Scan skills first.
2. Group results by source root, plugin, collection, and skill name.
3. Flag missing required fields, weak descriptions, duplicate names, and unreadable files.
4. Only open a full `SKILL.md` when the user asks for details or when diagnosing a specific skill.
5. Keep recommendations practical: improve trigger descriptions, rename confusing skills, archive stale skills, or split overly broad skills.

## Visual Output

For the normal Codex experience, render:

`ui://widget/skill-manager/dashboard.html`

For a quick local development fallback, generate:

`assets/skill-dashboard.html`

If the fallback dashboard is generated from live data, tell the user where the HTML file was written.
