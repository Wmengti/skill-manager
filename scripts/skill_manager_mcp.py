#!/usr/bin/env python3
"""Local skill inventory scanner and minimal MCP stdio server."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


DEFAULT_ROOTS = [
    Path.home() / ".codex" / "skills",
    Path.home() / ".codex" / "plugins" / "cache",
]


@dataclass
class SkillRecord:
    name: str
    description: str
    path: str
    root: str
    source: str
    body_lines: int
    has_frontmatter: bool
    issues: list[str]


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str, bool]:
    if not text.startswith("---\n"):
        return {}, text, False
    end = text.find("\n---", 4)
    if end == -1:
        return {}, text, False
    raw = text[4:end].strip()
    body = text[text.find("\n", end + 4) + 1 :]
    data: dict[str, Any] = {}
    current_key: str | None = None
    for line in raw.splitlines():
        if not line.strip():
            continue
        if line.startswith((" ", "\t")) and current_key:
            data[current_key] = f"{data.get(current_key, '')} {line.strip()}".strip()
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        current_key = key.strip()
        value = value.strip()
        if value in {">", "|"}:
            data[current_key] = ""
        else:
            data[current_key] = value.strip("\"'")
    return data, body, True


def source_label(root: Path, skill_path: Path, description: str = "") -> str:
    try:
        rel = skill_path.relative_to(root)
    except ValueError:
        return root.name
    parts = rel.parts
    if ".codex" in root.parts and root.name == "skills":
        if parts and parts[0] == ".system":
            return "system/bundled-skills"
        if len(parts) >= 3 and parts[1] == "skills":
            return f"user-collection/{parts[0]}"
        if description.startswith("AI Berkshire skill:"):
            return "user-collection/ai-berkshire"
        return "user-single-skill"
    if "cache" in root.parts and len(parts) >= 2:
        return "/".join(parts[:2])
    return root.name


def collect_issues(name: str, description: str, has_frontmatter: bool) -> list[str]:
    issues: list[str] = []
    if not has_frontmatter:
        issues.append("missing-frontmatter")
    if not name:
        issues.append("missing-name")
    if not description:
        issues.append("missing-description")
    elif len(description) < 80:
        issues.append("short-description")
    if name and not re.fullmatch(r"[a-z0-9-]+", name):
        issues.append("nonstandard-name")
    return issues


def scan_skills(roots: list[Path] | None = None) -> dict[str, Any]:
    roots = roots or DEFAULT_ROOTS
    records: list[SkillRecord] = []
    errors: list[dict[str, str]] = []
    seen: dict[str, int] = {}

    for root in roots:
        expanded = root.expanduser().resolve()
        if not expanded.exists():
            errors.append({"root": str(expanded), "error": "root-not-found"})
            continue
        for skill_file in sorted(expanded.rglob("SKILL.md")):
            try:
                text = read_text(skill_file)
                frontmatter, body, has_frontmatter = parse_frontmatter(text)
            except OSError as exc:
                errors.append({"path": str(skill_file), "error": str(exc)})
                continue
            folder_name = skill_file.parent.name
            name = str(frontmatter.get("name") or folder_name).strip()
            description = str(frontmatter.get("description") or "").strip()
            seen[name] = seen.get(name, 0) + 1
            records.append(
                SkillRecord(
                    name=name,
                    description=description,
                    path=str(skill_file),
                    root=str(expanded),
                    source=source_label(expanded, skill_file, description),
                    body_lines=len(body.splitlines()),
                    has_frontmatter=has_frontmatter,
                    issues=collect_issues(name, description, has_frontmatter),
                )
            )

    duplicate_names = {name for name, count in seen.items() if count > 1}
    for record in records:
        if record.name in duplicate_names:
            record.issues.append("duplicate-name")

    by_source: dict[str, int] = {}
    issue_counts: dict[str, int] = {}
    for record in records:
        by_source[record.source] = by_source.get(record.source, 0) + 1
        for issue in record.issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1

    return {
        "summary": {
            "total": len(records),
            "sources": by_source,
            "issues": issue_counts,
        },
        "skills": [asdict(record) for record in records],
        "errors": errors,
    }


def read_skill(identifier: str, roots: list[Path] | None = None) -> dict[str, Any]:
    inventory = scan_skills(roots)
    for record in inventory["skills"]:
        if identifier in {record["name"], record["path"]}:
            path = Path(record["path"])
            return {"skill": record, "content": read_text(path)}
    raise ValueError(f"Skill not found: {identifier}")


def dashboard_html(inventory: dict[str, Any]) -> str:
    data = json.dumps(inventory, ensure_ascii=False)
    total = inventory.get("summary", {}).get("total", 0)
    issue_labels = {
        "missing-frontmatter": "缺少 frontmatter",
        "missing-name": "缺少名称",
        "missing-description": "缺少描述",
        "short-description": "描述偏短",
        "nonstandard-name": "名称不规范",
        "duplicate-name": "名称重复",
    }
    issue_labels_json = json.dumps(issue_labels, ensure_ascii=False)
    source_label_js = """
    function sourceLabel(value) {
      if (value === 'system/bundled-skills') return '系统内置 skills';
      if (value === 'user-single-skill') return '用户单个 skill';
      if (value.startsWith('user-collection/')) return `本地集合：${value.slice('user-collection/'.length)}`;
      if (value.startsWith('personal/')) return `个人插件：${value.slice('personal/'.length)}`;
      if (value.startsWith('openai-curated/')) return `官方精选插件：${value.slice('openai-curated/'.length)}`;
      if (value.startsWith('openai-bundled/')) return `Codex 内置插件：${value.slice('openai-bundled/'.length)}`;
      if (value.startsWith('openai-primary-runtime/')) return `运行时插件：${value.slice('openai-primary-runtime/'.length)}`;
      return value || '未知来源';
    }
"""
    keyword_rules = {
        "image": "图片 生成 编辑 海报 视觉 素材",
        "pdf": "PDF 阅读 创建 提取 渲染 校验",
        "doc": "文档 Word docx 编辑 批注 修订",
        "spreadsheet": "表格 Excel CSV 数据 分析 图表",
        "presentation": "PPT 幻灯片 演示文稿 deck",
        "deploy": "部署 发布 上线 托管 hosting",
        "vercel": "Vercel 部署 网站 上线",
        "cloudflare": "Cloudflare Workers Pages 部署",
        "netlify": "Netlify 部署 网站",
        "render": "Render 部署 后端 服务",
        "figma": "Figma 设计稿 设计系统 组件 设计转代码",
        "browser": "浏览器 网页 自动化 截图 测试",
        "playwright": "浏览器 自动化 测试 截图 表单",
        "github": "GitHub PR CI issue 代码审查",
        "gh-": "GitHub PR CI issue 代码审查",
        "security": "安全 审计 威胁建模 风险",
        "sentry": "Sentry 线上错误 异常 监控",
        "stock": "股票 投资 估值 财报 个股",
        "investment": "投资 研究 估值 组合",
        "earnings": "财报 业绩 电话会 解读",
        "wechat": "微信公众号 文章 写作 发布",
        "xiaohongshu": "小红书 内容 素材 发布",
        "build-in-public": "公开创作 实验记录 小红书 素材 复盘",
        "skill": "Skill 技能 创建 安装 管理",
        "plugin": "插件 创建 安装 管理 marketplace",
        "mcp": "MCP 工具 接入 服务",
        "remotion": "Remotion React 视频 动画",
        "hyperframes": "视频 动画 HTML GSAP 短视频",
        "heygen": "HeyGen 数字人 头像 口播 视频",
        "speech": "语音 配音 TTS 旁白",
        "transcribe": "转录 音频 视频 文字 说话人",
        "obsidian": "Obsidian 笔记 知识库 Markdown",
        "notion": "Notion 文档 知识库 会议",
        "linear": "Linear issue 项目 管理",
        "jupyter": "Jupyter Notebook 实验 教程",
        "json-canvas": "画布 流程图 思维导图 JSON Canvas",
        "cowart": "Cowart 画布 图片 批注",
    }
    keyword_rules_json = json.dumps(keyword_rules, ensure_ascii=False)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Skill 管理器</title>
  <style>
    :root {{ color-scheme: light dark; font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    body {{ margin: 0; background: #f7f7f4; color: #1f2933; }}
    header {{ padding: 28px 32px 18px; border-bottom: 1px solid #ddd8cc; background: #ffffff; }}
    h1 {{ margin: 0 0 8px; font-size: 28px; letter-spacing: 0; }}
    .meta {{ color: #64748b; font-size: 14px; }}
    main {{ display: grid; grid-template-columns: 320px 1fr; min-height: calc(100vh - 98px); }}
    aside {{ border-right: 1px solid #ddd8cc; padding: 18px; background: #fbfaf7; }}
    input, select {{ width: 100%; box-sizing: border-box; padding: 10px 12px; border: 1px solid #cbd5e1; border-radius: 6px; background: #fff; color: #111827; margin-bottom: 12px; }}
    .stats {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 8px 0 16px; }}
    .stat {{ border: 1px solid #ddd8cc; border-radius: 8px; padding: 10px; background: #fff; }}
    .stat strong {{ display: block; font-size: 22px; }}
    .list {{ padding: 18px; display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; align-content: start; }}
    article {{ border: 1px solid #d9e0e8; border-radius: 8px; padding: 14px; background: #fff; min-height: 152px; }}
    article h2 {{ margin: 0 0 8px; font-size: 17px; overflow-wrap: anywhere; }}
    article p {{ margin: 0 0 12px; color: #475569; font-size: 13px; line-height: 1.45; }}
    .path {{ color: #64748b; font-size: 12px; overflow-wrap: anywhere; }}
    .hint {{ margin: 0 0 10px; color: #334155; font-size: 13px; line-height: 1.45; }}
    .chips {{ display: flex; flex-wrap: wrap; gap: 6px; margin: 10px 0; }}
    .chip {{ font-size: 12px; padding: 3px 7px; border-radius: 999px; background: #e8f1ff; color: #1d4ed8; }}
    .issue {{ background: #fff2d5; color: #92400e; }}
    .empty {{ padding: 32px; color: #64748b; }}
    @media (max-width: 760px) {{ main {{ grid-template-columns: 1fr; }} aside {{ border-right: 0; border-bottom: 1px solid #ddd8cc; }} }}
  </style>
</head>
<body>
  <header>
    <h1>Skill 管理器</h1>
    <div class="meta">本地 Codex skills 可视化清单。当前扫描到 {html.escape(str(total))} 个 skill。</div>
  </header>
  <main>
    <aside>
      <input id="q" placeholder="搜索名称、中文关键词、用途、路径" />
      <select id="source"><option value="">全部来源</option></select>
      <select id="issue"><option value="">全部状态</option></select>
      <div class="stats">
        <div class="stat"><strong id="total">0</strong><span>全部 skill</span></div>
        <div class="stat"><strong id="shown">0</strong><span>当前显示</span></div>
      </div>
      <div id="issues"></div>
    </aside>
    <section class="list" id="list"></section>
  </main>
  <script id="skill-data" type="application/json">{data}</script>
  <script>
    const data = JSON.parse(document.getElementById('skill-data').textContent);
    const issueLabels = {issue_labels_json};
    const keywordRules = {keyword_rules_json};
    {source_label_js}
    const skills = data.skills || [];
    const q = document.getElementById('q');
    const source = document.getElementById('source');
    const issue = document.getElementById('issue');
    const list = document.getElementById('list');
    const total = document.getElementById('total');
    const shown = document.getElementById('shown');
    total.textContent = skills.length;
    const allSources = [...new Set(skills.map(s => s.source).filter(Boolean))].sort();
    for (const item of allSources) {{
      const opt = document.createElement('option');
      opt.value = item;
      opt.textContent = sourceLabel(item);
      source.appendChild(opt);
    }}
    const allIssues = [...new Set(skills.flatMap(s => s.issues || []))].sort();
    for (const item of allIssues) {{
      const opt = document.createElement('option');
      opt.value = item;
      opt.textContent = issueLabels[item] || item;
      issue.appendChild(opt);
    }}
    function chineseHint(skill) {{
      const text = [skill.name, skill.description, skill.path, skill.source].join(' ').toLowerCase();
      const tags = [];
      for (const [key, value] of Object.entries(keywordRules)) {{
        if (text.includes(key.toLowerCase())) tags.push(...value.split(/\\s+/));
      }}
      if (text.includes('create') || text.includes('generate')) tags.push('创建', '生成');
      if (text.includes('edit') || text.includes('modify') || text.includes('update')) tags.push('编辑', '修改');
      if (text.includes('review') || text.includes('audit')) tags.push('审查', '检查');
      if (text.includes('analyze') || text.includes('analysis')) tags.push('分析');
      if (text.includes('workflow')) tags.push('工作流');
      if (text.includes('automation')) tags.push('自动化');
      if (text.includes('video')) tags.push('视频');
      if (text.includes('content')) tags.push('内容');
      const unique = [...new Set(tags)].slice(0, 10);
      return unique.length ? unique.join(' / ') : '暂无中文关键词，建议补充 skill 描述';
    }}
    function purposeSentence(skill) {{
      const text = [skill.name, skill.description, skill.path, skill.source].join(' ').toLowerCase();
      const name = skill.name || '这个 skill';
      const rules = [
        ['build-in-public', '用于把真实实验过程沉淀成小红书素材、复盘和公开创作线索。'],
        ['skill-manager', '用于查看、搜索和刷新本地 Codex skills 清单。'],
        ['image', '用于生成、编辑或处理图片、海报和视觉素材。'],
        ['pdf', '用于阅读、创建、提取、渲染或检查 PDF 文件。'],
        ['doc', '用于创建、编辑或检查 Word 文档和文档类交付物。'],
        ['spreadsheet', '用于处理表格、CSV、Excel、公式、图表和数据分析。'],
        ['presentation', '用于创建或编辑 PPT、幻灯片和演示文稿。'],
        ['deploy', '用于把网站、应用或服务部署上线。'],
        ['vercel', '用于把网站或应用部署到 Vercel。'],
        ['cloudflare', '用于把应用部署到 Cloudflare Workers 或 Pages。'],
        ['netlify', '用于把网站部署到 Netlify。'],
        ['render', '用于把应用或后端服务部署到 Render。'],
        ['figma', '用于读取、生成、实现或维护 Figma 设计和设计系统。'],
        ['browser', '用于控制浏览器、测试网页、截图或检查页面。'],
        ['playwright', '用于自动化浏览器操作、页面测试和截图验证。'],
        ['github', '用于处理 GitHub PR、CI、issue 或代码协作流程。'],
        ['gh-', '用于处理 GitHub PR、CI、issue 或代码协作流程。'],
        ['security', '用于做安全审查、威胁建模或安全责任分析。'],
        ['sentry', '用于查看 Sentry 线上错误、异常事件和健康数据。'],
        ['stock', '用于股票、财报、估值或投资研究分析。'],
        ['investment', '用于投资研究、组合管理、估值或投研备忘录。'],
        ['earnings', '用于分析财报、业绩电话会和公司经营数据。'],
        ['wechat', '用于微信公众号文章的选题、写作、编辑或发布准备。'],
        ['speech', '用于生成语音、配音、旁白或 TTS 音频。'],
        ['transcribe', '用于把音频或视频转写成文字并可辅助区分说话人。'],
        ['remotion', '用于用 React/Remotion 制作视频和动画。'],
        ['hyperframes', '用于制作 HTML/GSAP 风格的视频、动画和短视频。'],
        ['heygen', '用于创建数字人头像或生成真人口播视频。'],
        ['obsidian', '用于管理 Obsidian 笔记、知识库、Markdown 或 Bases。'],
        ['notion', '用于整理 Notion 知识库、会议资料、文档或任务。'],
        ['linear', '用于管理 Linear issue、项目和团队工作流。'],
        ['jupyter', '用于创建或编辑 Jupyter Notebook 实验和教程。'],
        ['json-canvas', '用于创建或编辑 JSON Canvas 画布、流程图和思维导图。'],
        ['cowart', '用于打开 Cowart 画布或处理画布中的图片和批注。'],
        ['plugin', '用于创建、更新或管理 Codex 插件。'],
        ['skill', '用于创建、安装、更新或管理 Codex skills。'],
        ['mcp', '用于接入、调试或管理 MCP 工具服务。'],
      ];
      for (const [needle, sentence] of rules) {{
        if (text.includes(needle)) return sentence;
      }}
      if (text.includes('create') || text.includes('generate')) return `用于创建或生成与 ${{name}} 相关的内容。`;
      if (text.includes('edit') || text.includes('modify') || text.includes('update')) return `用于编辑、修改或更新与 ${{name}} 相关的内容。`;
      if (text.includes('review') || text.includes('audit')) return `用于审查、检查或评估与 ${{name}} 相关的内容。`;
      if (text.includes('analyze') || text.includes('analysis')) return `用于分析与 ${{name}} 相关的数据、文件或流程。`;
      return '用于特定工作流；建议打开完整 SKILL.md 查看触发场景。';
    }}
    function render() {{
      const query = q.value.trim().toLowerCase();
      const selectedSource = source.value;
      const selectedIssue = issue.value;
      const filtered = skills.filter(s => {{
        const haystack = [s.name, s.description, s.path, s.source, chineseHint(s), purposeSentence(s), ...(s.issues || []).map(x => issueLabels[x] || x)].join(' ').toLowerCase();
        return (!query || haystack.includes(query)) && (!selectedSource || s.source === selectedSource) && (!selectedIssue || (s.issues || []).includes(selectedIssue));
      }});
      shown.textContent = filtered.length;
      list.innerHTML = '';
      if (!filtered.length) {{
        list.innerHTML = '<div class="empty">没有匹配的 skill。</div>';
        return;
      }}
      for (const s of filtered) {{
        const article = document.createElement('article');
        const hint = purposeSentence(s);
        const status = (s.issues || []).length ? s.issues : ['ok'];
        const issues = status.map(x => {{
          const label = x === 'ok' ? '状态正常' : (issueLabels[x] || x);
          const cls = x === 'ok' ? 'chip' : 'chip issue';
          return `<span class="${{cls}}">${{label}}</span>`;
        }}).join('');
        article.innerHTML = `<h2>${{s.name}}</h2><div class="hint">用途提示：${{hint}}</div><p>${{s.description || '没有描述'}}</p><div class="chips"><span class="chip">来源：${{sourceLabel(s.source)}}</span>${{issues}}</div><div class="path">路径：${{s.path}}</div>`;
        list.appendChild(article);
      }}
    }}
    q.addEventListener('input', render);
    source.addEventListener('change', render);
    issue.addEventListener('change', render);
    render();
  </script>
</body>
</html>
"""


def handle_tool(name: str, arguments: dict[str, Any]) -> Any:
    roots = [Path(p) for p in arguments.get("roots", [])] or None
    if name == "list_skills":
        return scan_skills(roots)
    if name == "read_skill":
        return read_skill(str(arguments["identifier"]), roots)
    if name == "write_dashboard":
        inventory = scan_skills(roots)
        output = Path(arguments.get("outputPath") or "assets/skill-dashboard.html")
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(dashboard_html(inventory), encoding="utf-8")
        return {"path": str(output.resolve()), "summary": inventory["summary"]}
    raise ValueError(f"Unknown tool: {name}")


def mcp_response(request_id: Any, result: Any = None, error: str | None = None) -> dict[str, Any]:
    if error is not None:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": -32000, "message": error}}
    return {"jsonrpc": "2.0", "id": request_id, "result": result}


def run_mcp() -> None:
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            message = json.loads(line)
            method = message.get("method")
            request_id = message.get("id")
            if method == "initialize":
                result = {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "skill-manager", "version": "0.1.0"},
                }
                print(json.dumps(mcp_response(request_id, result)), flush=True)
            elif method == "notifications/initialized":
                continue
            elif method == "tools/list":
                tools = [
                    {
                        "name": "list_skills",
                        "description": "Scan local Codex skill roots and return skill metadata.",
                        "inputSchema": {"type": "object", "properties": {"roots": {"type": "array", "items": {"type": "string"}}}},
                    },
                    {
                        "name": "read_skill",
                        "description": "Read one SKILL.md by skill name or absolute path.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "identifier": {"type": "string"},
                                "roots": {"type": "array", "items": {"type": "string"}},
                            },
                            "required": ["identifier"],
                        },
                    },
                    {
                        "name": "write_dashboard",
                        "description": "Generate a static HTML skill dashboard from the scan result.",
                        "inputSchema": {
                            "type": "object",
                            "properties": {
                                "outputPath": {"type": "string"},
                                "roots": {"type": "array", "items": {"type": "string"}},
                            },
                        },
                    },
                ]
                print(json.dumps(mcp_response(request_id, {"tools": tools})), flush=True)
            elif method == "tools/call":
                params = message.get("params") or {}
                result = handle_tool(params.get("name"), params.get("arguments") or {})
                content = [{"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}]
                print(json.dumps(mcp_response(request_id, {"content": content})), flush=True)
            else:
                print(json.dumps(mcp_response(request_id, {}, None)), flush=True)
        except Exception as exc:
            request_id = None
            if "message" in locals() and isinstance(message, dict):
                request_id = message.get("id")
            print(json.dumps(mcp_response(request_id, error=str(exc))), flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scan Codex skills or run the Skill Manager MCP server.")
    parser.add_argument("--dump-json", action="store_true", help="Print skill inventory JSON.")
    parser.add_argument("--write-dashboard", help="Write a static HTML dashboard.")
    parser.add_argument("--root", action="append", default=[], help="Skill root to scan. May be repeated.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    roots = [Path(p) for p in args.root] or None
    if args.dump_json:
        print(json.dumps(scan_skills(roots), ensure_ascii=False, indent=2))
        return
    if args.write_dashboard:
        inventory = scan_skills(roots)
        output = Path(args.write_dashboard)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(dashboard_html(inventory), encoding="utf-8")
        print(str(output.resolve()))
        return
    run_mcp()


if __name__ == "__main__":
    main()
