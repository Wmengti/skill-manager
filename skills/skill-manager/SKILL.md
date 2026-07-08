---
name: skill-manager
description: Use this skill when the user says "打开 skill 管理器", "打开技能管理器", "open skill manager", or wants to browse, inspect, search, audit, visualize, refresh, summarize, or manage local Codex skills; compare skill descriptions; find broken or missing SKILL.md files; generate a skill inventory; or prepare data for a visual skill manager plugin.
---

# Skill Manager

## Purpose

Help the user understand what Codex skills are available locally and how they are likely to trigger.

Use the plugin's MCP server or local script to scan skill roots, then summarize the inventory in a way that helps the user decide which skills are useful, stale, duplicated, broken, or worth improving.

## Data Layer

The scanner lives at:

`scripts/skill_manager_mcp.py`

The easiest user-facing launcher lives at:

`scripts/open_skill_manager.py`

It can be used in three ways:

- as a plugin MCP stdio server through `.mcp.json`
- as a direct JSON exporter with `--dump-json`
- as a static dashboard generator with `--write-dashboard <path>`

Use `open_skill_manager.py` when the user asks to open or refresh the Skill Manager. It regenerates the dashboard from the latest installed skills and prints the local file path plus a `file://` URL.

## Default Scan Roots

Unless the user gives specific roots, scan:

- `~/.codex/skills`
- `~/.codex/plugins/cache`

The scanner finds folders that contain `SKILL.md`, reads frontmatter, and returns metadata rather than loading every full skill body into the conversation.

## Workflow

When the user asks to open the Skill Manager:

1. Run `python3 scripts/open_skill_manager.py`.
2. Tell the user the dashboard was refreshed.
3. Provide the generated HTML file path or `file://` URL.

When the user asks to inspect or audit skills:

1. Scan skills first.
2. Group results by source root, plugin, collection, and skill name.
3. Flag missing required fields, weak descriptions, duplicate names, and unreadable files.
4. Only open a full `SKILL.md` when the user asks for details or when diagnosing a specific skill.
5. Keep recommendations practical: improve trigger descriptions, rename confusing skills, archive stale skills, or split overly broad skills.

## Visual Output

For a quick local visual view, generate:

`assets/skill-dashboard.html`

If the dashboard is generated from live data, tell the user where the HTML file was written.
