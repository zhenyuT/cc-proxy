import html
import json
import os
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse, Response

from capture_store import CaptureStore, get_db_path, get_log_dir


app = FastAPI(title="cc-proxy dashboard")
store = CaptureStore()


def format_bytes(num_bytes: int) -> str:
    units = ["B", "KB", "MB", "GB"]
    value = float(num_bytes)
    for unit in units:
        if value < 1024 or unit == units[-1]:
            return f"{value:.1f} {unit}" if unit != "B" else f"{int(value)} {unit}"
        value /= 1024
    return f"{num_bytes} B"


def format_timestamp(value: str | None) -> str | None:
    if not value:
        return value
    try:
        return datetime.fromisoformat(value).strftime("%Y-%m-%d %H:%M:%S.%f")
    except ValueError:
        return value


def format_record_timestamps(record: dict) -> dict:
    formatted = dict(record)
    formatted["started_at"] = format_timestamp(formatted.get("started_at"))
    formatted["finished_at"] = format_timestamp(formatted.get("finished_at"))
    return formatted


def dashboard_html() -> str:
    db_path = html.escape(str(get_db_path()))
    log_dir = html.escape(str(get_log_dir()))
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>cc-proxy 抓包查看</title>
  <link href="https://cdnjs.cloudflare.com/ajax/libs/jsoneditor/10.4.1/jsoneditor.min.css" rel="stylesheet" />
  <style>
    :root {{
      --bg: #f4efe7;
      --paper: #fffaf2;
      --ink: #1d1b19;
      --muted: #6a645d;
      --line: #d9cfbf;
      --accent: #9a3412;
      --accent-soft: #fed7aa;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: "Iowan Old Style", "Noto Serif SC", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, rgba(254, 215, 170, 0.7), transparent 28%),
        linear-gradient(180deg, #f7f2eb 0%, #efe6da 100%);
    }}
    .wrap {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 24px;
    }}
    .hero {{
      background: rgba(255, 250, 242, 0.86);
      border: 1px solid var(--line);
      border-radius: 24px;
      padding: 24px;
      box-shadow: 0 20px 50px rgba(80, 48, 20, 0.08);
      backdrop-filter: blur(8px);
    }}
    h1 {{
      margin: 0 0 8px;
      font-size: 34px;
    }}
    .muted {{
      color: var(--muted);
      margin: 0;
    }}
    .paths {{
      margin-top: 12px;
      font-size: 14px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: minmax(360px, 420px) minmax(0, 1fr);
      gap: 20px;
      margin-top: 20px;
    }}
    .card {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 24px;
      overflow: hidden;
      min-height: 540px;
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
    }}
    button {{
      border: 0;
      border-radius: 999px;
      background: var(--accent);
      color: #fff7ed;
      padding: 10px 14px;
      cursor: pointer;
      font: inherit;
    }}
    .ghost {{
      background: transparent;
      border: 1px solid var(--line);
      color: var(--ink);
    }}
    #record-list {{
      padding: 10px;
      max-height: 720px;
      overflow: auto;
    }}
    .record {{
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px;
      margin-bottom: 10px;
      cursor: pointer;
      transition: transform .15s ease, border-color .15s ease, background .15s ease;
      background: rgba(255,255,255,0.6);
    }}
    .record:hover, .record.active {{
      transform: translateY(-1px);
      border-color: var(--accent);
      background: #fff;
    }}
    .url {{
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 12px;
      word-break: break-all;
      color: var(--muted);
      margin-top: 6px;
    }}
    .meta {{
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      font-size: 13px;
      color: var(--muted);
    }}
    #detail {{
      padding: 18px;
      overflow: auto;
      max-height: 720px;
    }}
    pre {{
      background: #201a17;
      color: #fef3c7;
      border-radius: 16px;
      padding: 16px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      max-height: 360px;
    }}
    .section {{
      margin-bottom: 18px;
    }}
    .section h3 {{
      margin: 0 0 8px;
      font-size: 18px;
    }}
    .body-actions {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }}
    .body-toolbar {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-bottom: 8px;
    }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: #7c2d12;
      font-size: 12px;
      margin-right: 8px;
    }}
    details {{
      border: 1px solid var(--line);
      border-radius: 16px;
      background: rgba(255,255,255,0.5);
    }}
    summary {{
      cursor: pointer;
      padding: 14px 16px;
      font-weight: 600;
    }}
    details > div {{
      padding: 0 16px 16px;
    }}
    .json-editor-host {{
      border: 1px solid #e5ded2;
      border-radius: 16px;
      overflow: hidden;
      background: #fff;
      min-height: 260px;
    }}
    .json-editor-host .jsoneditor {{
      border: 0;
    }}
    .json-editor-host .jsoneditor-menu {{
      display: none;
    }}
    .json-editor-host .jsoneditor-navigation-bar {{
      background: #f8f5ef;
      border-bottom: 1px solid #e5ded2;
    }}
    .json-editor-host .jsoneditor-tree {{
      min-height: 220px;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 13px;
      line-height: 1.45;
    }}
    .json-editor-host .jsoneditor-statusbar {{
      display: none;
    }}
    .sse-view {{
      display: flex;
      flex-direction: column;
      gap: 12px;
    }}
    .sse-event {{
      border: 1px solid #e5ded2;
      border-radius: 16px;
      background: #fff;
      overflow: hidden;
    }}
    .sse-head {{
      display: flex;
      gap: 10px;
      align-items: center;
      padding: 10px 14px;
      border-bottom: 1px solid #efe7dc;
      background: #faf7f2;
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 12px;
    }}
    .sse-label {{
      color: #6b7280;
    }}
    .sse-value {{
      color: #111827;
      word-break: break-all;
    }}
    .sse-body {{
      padding: 12px;
    }}
    .fullscreen-modal {{
      position: fixed;
      inset: 0;
      background: rgba(17, 24, 39, 0.7);
      display: none;
      align-items: stretch;
      justify-content: center;
      padding: 24px;
      z-index: 1000;
    }}
    .fullscreen-modal.open {{
      display: flex;
    }}
    .fullscreen-panel {{
      width: min(1400px, 100%);
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.22);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    .fullscreen-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
    }}
    .fullscreen-body {{
      padding: 18px;
      overflow: auto;
      flex: 1;
    }}
    .messages-modal {{
      position: fixed;
      inset: 0;
      background: rgba(17, 24, 39, 0.7);
      display: none;
      align-items: stretch;
      justify-content: center;
      padding: 24px;
      z-index: 1001;
    }}
    .messages-modal.open {{
      display: flex;
    }}
    .messages-panel {{
      width: min(1500px, 100%);
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 24px;
      box-shadow: 0 24px 60px rgba(0, 0, 0, 0.22);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }}
    .messages-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      padding: 16px 18px;
      border-bottom: 1px solid var(--line);
    }}
    .messages-body {{
      padding: 18px;
      overflow: auto;
      flex: 1;
    }}
    .messages-grid {{
      display: grid;
      grid-template-columns: 180px minmax(0, 1fr);
      border: 1px solid #e5ded2;
      border-radius: 18px;
      overflow: hidden;
      background: #fff;
    }}
    .messages-head-cell {{
      padding: 12px 14px;
      font-weight: 700;
      background: #f8f5ef;
      border-bottom: 1px solid #e5ded2;
    }}
    .messages-cell {{
      padding: 14px;
      border-bottom: 1px solid #f1ebe2;
    }}
    .messages-role {{
      font-family: "SFMono-Regular", Consolas, monospace;
      color: #7c2d12;
      font-size: 13px;
      white-space: nowrap;
    }}
    .message-content-item {{
      margin-bottom: 12px;
    }}
    .message-content-item:last-child {{
      margin-bottom: 0;
    }}
    .message-content-item pre {{
      margin: 0;
      max-height: none;
      background: #201a17;
      color: #fef3c7;
    }}
    .tools-accordion {{
      display: grid;
      gap: 12px;
    }}
    .tool-item {{
      border: 1px solid #e5ded2;
      border-radius: 16px;
      background: #fff;
      overflow: hidden;
    }}
    .tool-summary {{
      display: flex;
      align-items: center;
      gap: 10px;
      padding: 14px 16px;
      cursor: pointer;
      list-style: none;
      font-family: "SFMono-Regular", Consolas, monospace;
      color: #7c2d12;
      font-size: 13px;
      user-select: none;
    }}
    .tool-summary::-webkit-details-marker {{
      display: none;
    }}
    .tool-summary::before {{
      content: "▸";
      color: #b45309;
      font-size: 12px;
      line-height: 1;
      transition: transform 0.18s ease;
    }}
    .tool-item[open] .tool-summary::before {{
      transform: rotate(90deg);
    }}
    .tool-item[open] .tool-summary {{
      border-bottom: 1px solid #f1ebe2;
      background: #f8f5ef;
    }}
    .tool-body {{
      padding: 14px;
    }}
    .markdown-body {{
      color: #1f2937;
      line-height: 1.65;
      word-break: break-word;
    }}
    .markdown-body :first-child {{
      margin-top: 0;
    }}
    .markdown-body :last-child {{
      margin-bottom: 0;
    }}
    .markdown-body pre {{
      margin: 10px 0;
    }}
    .markdown-body code {{
      font-family: "SFMono-Regular", Consolas, monospace;
      font-size: 12px;
    }}
    .markdown-body blockquote {{
      margin: 10px 0;
      padding-left: 12px;
      border-left: 3px solid #d6c7b3;
      color: #6b7280;
    }}
    .md-preview-layout {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      min-height: 520px;
    }}
    .md-editor-pane, .md-preview-pane {{
      min-width: 0;
      display: flex;
      flex-direction: column;
    }}
    .md-pane-title {{
      font-weight: 700;
      margin-bottom: 10px;
    }}
    .md-input {{
      width: 100%;
      flex: 1;
      min-height: 460px;
      resize: vertical;
      border: 1px solid #d9cfbf;
      border-radius: 16px;
      padding: 14px;
      font: 13px/1.6 "SFMono-Regular", Consolas, monospace;
      background: #fff;
      color: #1f2937;
      outline: none;
    }}
    .md-preview-surface {{
      flex: 1;
      min-height: 460px;
      border: 1px solid #d9cfbf;
      border-radius: 16px;
      padding: 14px;
      background: #fff;
      overflow: auto;
    }}
    .json-inline-view {{
      border: 1px solid #e5ded2;
      border-radius: 14px;
      background: #fff;
      padding: 10px 12px;
      font: 13px/1.6 "SFMono-Regular", Consolas, monospace;
      color: #1f2937;
      overflow: auto;
    }}
    .json-inline-line {{
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .json-inline-child {{
      margin-left: 18px;
    }}
    .json-inline-key {{
      color: #7c2d12;
    }}
    .json-inline-string {{
      color: #166534;
    }}
    .json-inline-number {{
      color: #b45309;
    }}
    .json-inline-boolean {{
      color: #7c3aed;
    }}
    .json-inline-null {{
      color: #6b7280;
    }}
    .json-hover-field {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }}
    .json-hover-field .js-open-md-preview {{
      opacity: 0;
      pointer-events: none;
      transition: opacity .12s ease;
      padding: 2px 8px;
      font-size: 12px;
    }}
    .json-hover-field:hover .js-open-md-preview {{
      opacity: 1;
      pointer-events: auto;
    }}
    @media (max-width: 980px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .card {{ min-height: auto; }}
      #record-list, #detail {{ max-height: none; }}
      .fullscreen-modal {{ padding: 12px; }}
      .messages-modal {{ padding: 12px; }}
      .messages-grid {{ grid-template-columns: 1fr; }}
      .md-preview-layout {{ grid-template-columns: 1fr; }}
      .md-input, .md-preview-surface {{ min-height: 280px; }}
    }}
  </style>
</head>
<body>
  <div class="wrap">
    <div class="hero">
      <h1>cc-proxy 抓包查看</h1>
      <p class="muted">请求列表按开始时间倒序排列。点击左侧记录可查看请求头、请求体和完整响应预览。</p>
      <p class="muted paths">SQLite: <code>{db_path}</code><br />Logs: <code>{log_dir}</code></p>
    </div>
    <div class="grid">
      <section class="card">
        <div class="card-header">
          <strong>请求列表</strong>
          <button id="refresh-btn">刷新</button>
        </div>
        <div id="record-list"></div>
      </section>
      <section class="card">
        <div class="card-header">
          <strong>请求详情</strong>
          <span class="muted" id="detail-hint">选择一条记录</span>
        </div>
        <div id="detail"></div>
      </section>
    </div>
  </div>
  <div id="fullscreen-modal" class="fullscreen-modal">
    <div class="fullscreen-panel">
      <div class="fullscreen-header">
        <strong id="fullscreen-title">全屏查看</strong>
        <button id="fullscreen-close" class="ghost">关闭</button>
      </div>
      <div id="fullscreen-body" class="fullscreen-body"></div>
    </div>
  </div>
  <div id="messages-modal" class="messages-modal">
    <div class="messages-panel">
      <div class="messages-header">
        <strong>messages 便捷查看</strong>
        <button id="messages-close" class="ghost">关闭</button>
      </div>
      <div id="messages-body" class="messages-body"></div>
    </div>
  </div>
  <div id="tools-modal" class="messages-modal">
    <div class="messages-panel">
      <div class="messages-header">
        <strong>tools 便捷查看</strong>
        <button id="tools-close" class="ghost">关闭</button>
      </div>
      <div id="tools-body" class="messages-body"></div>
    </div>
  </div>
  <div id="system-modal" class="messages-modal">
    <div class="messages-panel">
      <div class="messages-header">
        <strong>system 便捷查看</strong>
        <button id="system-close" class="ghost">关闭</button>
      </div>
      <div id="system-body" class="messages-body"></div>
    </div>
  </div>
  <div id="md-preview-modal" class="messages-modal">
    <div class="messages-panel">
      <div class="messages-header">
        <strong>Markdown 渲染</strong>
        <button id="md-preview-close" class="ghost">关闭</button>
      </div>
      <div class="messages-body">
        <div class="md-preview-layout">
          <div class="md-editor-pane">
            <div class="md-pane-title">输入内容</div>
            <textarea id="md-preview-input" class="md-input"></textarea>
          </div>
          <div class="md-preview-pane">
            <div class="md-pane-title">渲染结果</div>
            <div id="md-preview-output" class="md-preview-surface markdown-body"></div>
          </div>
        </div>
      </div>
    </div>
  </div>
  <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
  <script src="https://cdnjs.cloudflare.com/ajax/libs/jsoneditor/10.4.1/jsoneditor.min.js"></script>
  <script>
    const state = {{ activeId: null, bodyEditors: [], fullscreenEditor: null }};

    function escapeHtml(value) {{
      return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;");
    }}

    function renderList(records) {{
      const root = document.getElementById("record-list");
      if (!records.length) {{
        root.innerHTML = '<p class="muted">暂无抓包记录</p>';
        return;
      }}

      root.innerHTML = records.map((record) => `
        <article class="record ${{
          record.id === state.activeId ? "active" : ""
        }}" data-id="${{record.id}}">
          <div><strong>#${{record.id}}</strong></div>
          <div class="meta">
            <span>${{escapeHtml(record.started_at || "-")}}</span>
            <span>耗时 ${{record.duration_ms ?? "-"}} ms</span>
          </div>
          <div class="url">${{escapeHtml(record.request_url)}}</div>
        </article>
      `).join("");

      root.querySelectorAll(".record").forEach((node) => {{
        node.addEventListener("click", () => {{
          const id = Number(node.dataset.id);
          state.activeId = id;
          highlightActive();
          loadDetail(id);
        }});
      }});
    }}

    function highlightActive() {{
      document.querySelectorAll(".record").forEach((node) => {{
        const id = Number(node.dataset.id);
        node.classList.toggle("active", id === state.activeId);
      }});
    }}

    function parseJsonContent(body) {{
      if (!body.content || body.content_type === "base64") {{
        return null;
      }}
      try {{
        return JSON.parse(body.content);
      }} catch (_error) {{
        return null;
      }}
    }}

    function getMessagesArray(body) {{
      const jsonValue = parseJsonContent(body);
      if (!jsonValue || !Array.isArray(jsonValue.messages)) {{
        return null;
      }}
      return jsonValue.messages;
    }}

    function getToolsArray(body) {{
      const jsonValue = parseJsonContent(body);
      if (!jsonValue || !Array.isArray(jsonValue.tools)) {{
        return null;
      }}
      return jsonValue.tools;
    }}

    function getSystemArray(body) {{
      const jsonValue = parseJsonContent(body);
      if (!jsonValue || !Array.isArray(jsonValue.system)) {{
        return null;
      }}
      return jsonValue.system;
    }}

    function renderMarkdown(text) {{
      if (!text) {{
        return '<p class="muted">(empty)</p>';
      }}
      if (window.marked && typeof window.marked.parse === "function") {{
        return window.marked.parse(text);
      }}
      return `<pre>${{escapeHtml(text)}}</pre>`;
    }}

    function extractMarkdownSource(value) {{
      if (typeof value === "string") {{
        return value;
      }}
      if (value && typeof value.text === "string") {{
        return value.text;
      }}
      return JSON.stringify(value, null, 2);
    }}

    function shouldShowMarkdownField(key, value) {{
      return typeof value === "string" && ["description", "text", "content", "thinking"].includes(String(key));
    }}

    function renderInlineJsonValue(value, key = null) {{
      if (value === null) {{
        return '<span class="json-inline-null">null</span>';
      }}
      if (typeof value === "string") {{
        const stringHtml = `<span class="json-inline-string">"${{escapeHtml(value)}}"</span>`;
        if (shouldShowMarkdownField(key, value)) {{
          return `
            <span class="json-hover-field">
              ${{stringHtml}}
              <button class="ghost js-open-md-preview" data-md="${{encodeURIComponent(value)}}">md渲染</button>
            </span>
          `;
        }}
        return stringHtml;
      }}
      if (typeof value === "number") {{
        return `<span class="json-inline-number">${{escapeHtml(String(value))}}</span>`;
      }}
      if (typeof value === "boolean") {{
        return `<span class="json-inline-boolean">${{escapeHtml(String(value))}}</span>`;
      }}
      return `<span>${{escapeHtml(String(value))}}</span>`;
    }}

    function renderInlineJsonNode(value, key = null) {{
      const keyHtml = key === null ? "" : `<span class="json-inline-key">"${{escapeHtml(String(key))}}"</span>: `;
      if (value === null || typeof value !== "object") {{
        return `<div class="json-inline-line">${{keyHtml}}${{renderInlineJsonValue(value, key)}}</div>`;
      }}

      if (Array.isArray(value)) {{
        const items = value.map((item) => `
          <div class="json-inline-child">${{renderInlineJsonNode(item)}}</div>
        `).join("");
        return `
          <div class="json-inline-line">${{keyHtml}}[</div>
          ${{items}}
          <div class="json-inline-line">]</div>
        `;
      }}

      const entries = Object.entries(value).map(([childKey, childValue]) => `
        <div class="json-inline-child">${{renderInlineJsonNode(childValue, childKey)}}</div>
      `).join("");
      return `
        <div class="json-inline-line">${{keyHtml}}{{</div>
        ${{entries}}
        <div class="json-inline-line">}}</div>
      `;
    }}

    function renderInlineJsonBlock(value) {{
      return `<div class="json-inline-view">${{renderInlineJsonNode(value)}}</div>`;
    }}

    function parseSseBody(body) {{
      if (!body.content || body.content_type === "base64") {{
        return null;
      }}
      const text = body.content;
      if (!text.includes("\\ndata:") && !text.startsWith("data:") && !text.includes("\\nevent:") && !text.startsWith("event:")) {{
        return null;
      }}

      const blocks = text.trim().split(/\\n\\s*\\n/).filter(Boolean);
      const events = blocks.map((block, index) => {{
        const lines = block.split("\\n");
        let eventName = "message";
        const dataLines = [];
        const rawLines = [];
        for (const line of lines) {{
          rawLines.push(line);
          if (line.startsWith("event:")) {{
            eventName = line.slice(6).trim() || "message";
          }} else if (line.startsWith("data:")) {{
            dataLines.push(line.slice(5).trimStart());
          }}
        }}
        const dataText = dataLines.join("\\n");
        let dataJson = null;
        if (dataText) {{
          try {{
            dataJson = JSON.parse(dataText);
          }} catch (_error) {{
            dataJson = null;
          }}
        }}
        return {{
          id: index,
          event: eventName,
          dataText,
          dataJson,
          raw: rawLines.join("\\n"),
        }};
      }});

      return events.length ? events : null;
    }}

    function formatBodyContent(body) {{
      const jsonValue = parseJsonContent(body);
      if (jsonValue !== null) {{
        return JSON.stringify(jsonValue, null, 2);
      }}
      return body.content || "(empty)";
    }}

    function legacyCopyText(text) {{
      const textarea = document.createElement("textarea");
      textarea.value = text;
      textarea.setAttribute("readonly", "readonly");
      textarea.style.position = "fixed";
      textarea.style.top = "-1000px";
      textarea.style.left = "-1000px";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      const ok = document.execCommand("copy");
      document.body.removeChild(textarea);
      if (!ok) {{
        throw new Error("execCommand copy failed");
      }}
    }}

    async function copyText(text) {{
      if (navigator.clipboard && window.isSecureContext) {{
        await navigator.clipboard.writeText(text);
        return;
      }}
      legacyCopyText(text);
    }}

    function renderBodyView(body) {{
      const sseEvents = parseSseBody(body);
      if (sseEvents) {{
        return `
          <div class="sse-view">
            ${{sseEvents.map((event) => `
              <div class="sse-event">
                <div class="sse-head">
                  <span class="sse-label">event</span>
                  <span class="sse-value">${{escapeHtml(event.event)}}</span>
                </div>
                <div class="sse-body">
                  ${{event.dataJson !== null
                    ? `<div class="json-editor-host js-json-editor" data-inline-json="${{encodeURIComponent(JSON.stringify(event.dataJson))}}"></div>`
                    : `<pre>${{escapeHtml(event.dataText || event.raw || "(empty)")}}</pre>`}}
                </div>
              </div>
            `).join("")}}
          </div>
        `;
      }}

      const jsonValue = parseJsonContent(body);
      if (jsonValue !== null) {{
        return '<div class="json-editor-host js-json-editor"></div>';
      }}
      return `<pre>${{escapeHtml(formatBodyContent(body))}}</pre>`;
    }}

    function destroyEditors() {{
      state.bodyEditors.forEach((editor) => editor.destroy());
      state.bodyEditors = [];
    }}

    function destroyFullscreenEditor() {{
      if (state.fullscreenEditor) {{
        state.fullscreenEditor.destroy();
        state.fullscreenEditor = null;
      }}
    }}

    function createReadonlyJsonEditor(container, value, expandAllNodes = false) {{
      const editor = new JSONEditor(container, {{
        mode: "view",
        modes: ["view"],
        mainMenuBar: false,
        navigationBar: true,
        statusBar: false
      }});
      editor.set(value);
      if (expandAllNodes && typeof editor.expandAll === "function") {{
        editor.expandAll();
      }}
      return editor;
    }}

    function mountDetailJsonEditors(detail) {{
      destroyEditors();
      const jsonContainers = document.querySelectorAll(".js-json-editor");
      jsonContainers.forEach((container) => {{
        const inlineJson = container.dataset.inlineJson;
        if (inlineJson) {{
          try {{
            const inlineValue = JSON.parse(decodeURIComponent(inlineJson));
            state.bodyEditors.push(createReadonlyJsonEditor(container, inlineValue, true));
          }} catch (_error) {{
          }}
          return;
        }}
        const kind = container.dataset.kind;
        const body = kind === "request" ? detail.request_body : detail.response_body;
        const jsonValue = parseJsonContent(body);
        if (jsonValue !== null) {{
          state.bodyEditors.push(createReadonlyJsonEditor(container, jsonValue, kind === "response"));
        }}
      }});
    }}

    function openFullscreen(title, body) {{
      const modal = document.getElementById("fullscreen-modal");
      document.getElementById("fullscreen-title").textContent = title;
      document.getElementById("fullscreen-body").innerHTML = renderBodyView(body);
      destroyFullscreenEditor();
      const containers = document.querySelectorAll("#fullscreen-body .js-json-editor");
      const sseEvents = parseSseBody(body);
      if (sseEvents) {{
        const editors = [];
        containers.forEach((container) => {{
          const inlineJson = container.dataset.inlineJson;
          if (!inlineJson) {{
            return;
          }}
          try {{
            const inlineValue = JSON.parse(decodeURIComponent(inlineJson));
            editors.push(createReadonlyJsonEditor(container, inlineValue, true));
          }} catch (_error) {{
          }}
        }});
        state.fullscreenEditor = {{
          destroy() {{
            editors.forEach((editor) => editor.destroy());
          }}
        }};
      }} else {{
        const container = document.querySelector("#fullscreen-body .js-json-editor");
        const jsonValue = parseJsonContent(body);
        if (container && jsonValue !== null) {{
          state.fullscreenEditor = createReadonlyJsonEditor(container, jsonValue, true);
        }}
      }}
      modal.classList.add("open");
    }}

    function closeFullscreen() {{
      document.getElementById("fullscreen-modal").classList.remove("open");
      document.getElementById("fullscreen-body").innerHTML = "";
      destroyFullscreenEditor();
    }}

    function renderMessagesModal(messages) {{
      if (!messages || !messages.length) {{
        return '<p class="muted">没有可展示的 messages</p>';
      }}

      const rows = messages.map((message) => {{
        const role = escapeHtml(message.role || "-");
        const contentItems = Array.isArray(message.content) ? message.content : [message.content];
        const contentHtml = contentItems.map((item) => `
          <div class="message-content-item">
            ${{renderInlineJsonBlock(item)}}
          </div>
        `).join("");
        return `
          <div class="messages-cell messages-role">${{role}}</div>
          <div class="messages-cell">${{contentHtml || '<pre>(empty)</pre>'}}</div>
        `;
      }}).join("");

      return `
        <div class="messages-grid">
          <div class="messages-head-cell">role</div>
          <div class="messages-head-cell">content</div>
          ${{rows}}
        </div>
      `;
    }}

    function openMessagesModal(messages) {{
      document.getElementById("messages-body").innerHTML = renderMessagesModal(messages);
      document.getElementById("messages-modal").classList.add("open");
      bindMarkdownPreviewButtons("#messages-body");
    }}

    function closeMessagesModal() {{
      document.getElementById("messages-modal").classList.remove("open");
      document.getElementById("messages-body").innerHTML = "";
    }}

    function renderToolsModal(tools) {{
      if (!tools || !tools.length) {{
        return '<p class="muted">没有可展示的 tools</p>';
      }}

      const items = tools.map((tool, index) => {{
        const name = escapeHtml(tool.name || `tool_${{index}}`);
        const inputSchema = tool.input_schema === undefined ? null : tool.input_schema;
        const parts = [
          `<div class="message-content-item">${{renderInlineJsonBlock(tool)}}</div>`
        ];
        if (inputSchema !== null) {{
          parts.unshift(
            `<div class="message-content-item">${{renderInlineJsonBlock(inputSchema)}}</div>`
          );
        }}
        return `
          <details class="tool-item">
            <summary class="tool-summary">${{name}}</summary>
            <div class="tool-body">${{parts.join("")}}</div>
          </details>
        `;
      }}).join("");

      return `
        <div class="tools-accordion">
          ${{items}}
        </div>
      `;
    }}

    function openToolsModal(tools) {{
      document.getElementById("tools-body").innerHTML = renderToolsModal(tools);
      document.getElementById("tools-modal").classList.add("open");
      bindMarkdownPreviewButtons("#tools-body");
    }}

    function closeToolsModal() {{
      document.getElementById("tools-modal").classList.remove("open");
      document.getElementById("tools-body").innerHTML = "";
    }}

    function renderSystemModal(systemItems) {{
      if (!systemItems || !systemItems.length) {{
        return '<p class="muted">没有可展示的 system</p>';
      }}

      const rows = systemItems.map((item) => {{
        const type = escapeHtml(item.type || "-");
        const markdown = renderMarkdown(item.text || "");
        return `
          <div class="messages-cell messages-role">${{type}}</div>
          <div class="messages-cell"><div class="markdown-body">${{markdown}}</div></div>
        `;
      }}).join("");

      return `
        <div class="messages-grid">
          <div class="messages-head-cell">type</div>
          <div class="messages-head-cell">text</div>
          ${{rows}}
        </div>
      `;
    }}

    function openSystemModal(systemItems) {{
      document.getElementById("system-body").innerHTML = renderSystemModal(systemItems);
      document.getElementById("system-modal").classList.add("open");
    }}

    function closeSystemModal() {{
      document.getElementById("system-modal").classList.remove("open");
      document.getElementById("system-body").innerHTML = "";
    }}

    function updateMarkdownPreview() {{
      const input = document.getElementById("md-preview-input");
      document.getElementById("md-preview-output").innerHTML = renderMarkdown(input.value);
    }}

    function openMarkdownPreview(initialText) {{
      const modal = document.getElementById("md-preview-modal");
      const input = document.getElementById("md-preview-input");
      input.value = initialText || "";
      updateMarkdownPreview();
      modal.classList.add("open");
      input.focus();
    }}

    function closeMarkdownPreview() {{
      document.getElementById("md-preview-modal").classList.remove("open");
    }}

    function bindMarkdownPreviewButtons(rootSelector) {{
      document.querySelectorAll(rootSelector + " .js-open-md-preview").forEach((button) => {{
        button.addEventListener("click", () => {{
          openMarkdownPreview(decodeURIComponent(button.dataset.md || ""));
        }});
      }});
    }}

    function bodyBlock(kind, body) {{
      const label = kind === "request" ? "请求体" : "响应体";
      const downloadUrl = `/api/records/${{state.activeId}}/body/${{kind}}/download`;
      const encodedContent = encodeURIComponent(body.content || "");
      const canFullscreen = kind === "request";
      const hasMessages = kind === "request" && !!getMessagesArray(body);
      const hasTools = kind === "request" && !!getToolsArray(body);
      const hasSystem = kind === "request" && !!getSystemArray(body);
      return `
        <div class="section">
          <h3>${{label}}</h3>
          <div class="body-actions">
            <span class="pill">大小 ${{body.total_bytes_display}}</span>
            ${{body.truncated ? '<span class="pill">预览已截断</span>' : ''}}
            <a href="${{downloadUrl}}"><button class="ghost">下载完整内容</button></a>
          </div>
          <div class="body-toolbar">
            <button class="ghost js-copy-body" data-copy="${{encodedContent}}">复制内容</button>
            ${{canFullscreen ? `<button class="ghost js-fullscreen-body" data-kind="${{kind}}">全屏查看</button>` : ''}}
            ${{hasMessages ? `<button class="ghost js-view-messages" data-kind="${{kind}}">查看 messages</button>` : ''}}
            ${{hasTools ? `<button class="ghost js-view-tools" data-kind="${{kind}}">查看 tools</button>` : ''}}
            ${{hasSystem ? `<button class="ghost js-view-system" data-kind="${{kind}}">查看 system</button>` : ''}}
          </div>
          <div data-kind="${{kind}}" class="js-json-container">${{renderBodyView(body)}}</div>
        </div>
      `;
    }}

    async function loadList() {{
      const response = await fetch("/api/records");
      const records = await response.json();
      renderList(records);
      if (!state.activeId && records.length) {{
        state.activeId = records[0].id;
        highlightActive();
        loadDetail(state.activeId);
      }}
    }}

    async function loadDetail(id) {{
      const hint = document.getElementById("detail-hint");
      hint.textContent = `记录 #${{id}}`;
      const response = await fetch(`/api/records/${{id}}`);
      if (!response.ok) {{
        document.getElementById("detail").innerHTML = '<p class="muted">记录不存在</p>';
        return;
      }}
      const detail = await response.json();
      document.getElementById("detail").innerHTML = `
        <div class="section">
          <h3>基本信息</h3>
          <p><strong>ID:</strong> ${{detail.id}}</p>
          <p><strong>URL:</strong> <code>${{escapeHtml(detail.request_url)}}</code></p>
          <p><strong>开始:</strong> ${{escapeHtml(detail.started_at || "-")}}</p>
          <p><strong>完成:</strong> ${{escapeHtml(detail.finished_at || "-")}}</p>
          <p><strong>耗时:</strong> ${{detail.duration_ms ?? "-"}} ms</p>
        </div>
        <div class="section">
          <details>
            <summary>请求头</summary>
            <div>
              <pre>${{escapeHtml(JSON.stringify(detail.request_headers, null, 2))}}</pre>
            </div>
          </details>
        </div>
        ${{bodyBlock("request", detail.request_body)}}
        ${{bodyBlock("response", detail.response_body)}}
      `;
      document.querySelectorAll(".js-json-container .js-json-editor").forEach((node) => {{
        const parent = node.closest(".js-json-container");
        if (parent) {{
          node.dataset.kind = parent.dataset.kind;
        }}
      }});
      mountDetailJsonEditors(detail);

      document.querySelectorAll(".js-copy-body").forEach((button) => {{
        button.addEventListener("click", async () => {{
          try {{
            await copyText(decodeURIComponent(button.dataset.copy || ""));
            button.textContent = "已复制";
            setTimeout(() => {{
              button.textContent = "复制内容";
            }}, 1200);
          }} catch (_error) {{
            button.textContent = "复制失败";
            setTimeout(() => {{
              button.textContent = "复制内容";
            }}, 1200);
          }}
        }});
      }});

      document.querySelectorAll(".js-fullscreen-body").forEach((button) => {{
        button.addEventListener("click", () => {{
          const kind = button.dataset.kind;
          const body = kind === "request" ? detail.request_body : detail.response_body;
          openFullscreen(kind === "request" ? "请求体全屏查看" : "响应体全屏查看", body);
        }});
      }});

      document.querySelectorAll(".js-view-messages").forEach((button) => {{
        button.addEventListener("click", () => {{
          const kind = button.dataset.kind;
          const body = kind === "request" ? detail.request_body : detail.response_body;
          openMessagesModal(getMessagesArray(body));
        }});
      }});

      document.querySelectorAll(".js-view-tools").forEach((button) => {{
        button.addEventListener("click", () => {{
          const kind = button.dataset.kind;
          const body = kind === "request" ? detail.request_body : detail.response_body;
          openToolsModal(getToolsArray(body));
        }});
      }});

      document.querySelectorAll(".js-view-system").forEach((button) => {{
        button.addEventListener("click", () => {{
          const kind = button.dataset.kind;
          const body = kind === "request" ? detail.request_body : detail.response_body;
          openSystemModal(getSystemArray(body));
        }});
      }});
    }}

    document.getElementById("refresh-btn").addEventListener("click", loadList);
    document.getElementById("fullscreen-close").addEventListener("click", closeFullscreen);
    document.getElementById("fullscreen-modal").addEventListener("click", (event) => {{
      if (event.target.id === "fullscreen-modal") {{
        closeFullscreen();
      }}
    }});
    document.addEventListener("keydown", (event) => {{
      if (event.key === "Escape") {{
        closeFullscreen();
        closeMessagesModal();
        closeToolsModal();
        closeSystemModal();
        closeMarkdownPreview();
      }}
    }});
    document.getElementById("messages-close").addEventListener("click", closeMessagesModal);
    document.getElementById("messages-modal").addEventListener("click", (event) => {{
      if (event.target.id === "messages-modal") {{
        closeMessagesModal();
      }}
    }});
    document.getElementById("tools-close").addEventListener("click", closeToolsModal);
    document.getElementById("tools-modal").addEventListener("click", (event) => {{
      if (event.target.id === "tools-modal") {{
        closeToolsModal();
      }}
    }});
    document.getElementById("system-close").addEventListener("click", closeSystemModal);
    document.getElementById("system-modal").addEventListener("click", (event) => {{
      if (event.target.id === "system-modal") {{
        closeSystemModal();
      }}
    }});
    document.getElementById("md-preview-close").addEventListener("click", closeMarkdownPreview);
    document.getElementById("md-preview-modal").addEventListener("click", (event) => {{
      if (event.target.id === "md-preview-modal") {{
        closeMarkdownPreview();
      }}
    }});
    document.getElementById("md-preview-input").addEventListener("input", updateMarkdownPreview);
    loadList();
  </script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index() -> HTMLResponse:
    return HTMLResponse(dashboard_html())


@app.get("/api/records")
async def list_records() -> JSONResponse:
    return JSONResponse([format_record_timestamps(record) for record in store.list_records()])


@app.get("/api/records/{capture_id}")
async def get_record(capture_id: int) -> JSONResponse:
    record = store.get_record(capture_id)
    if record is None:
        raise HTTPException(status_code=404, detail="record not found")

    try:
        request_headers = json.loads(record["request_headers"])
    except json.JSONDecodeError:
        request_headers = {"raw": record["request_headers"]}

    request_preview = store.read_body_preview(capture_id, "request")
    response_preview = store.read_body_preview(capture_id, "response")

    payload = {
        **format_record_timestamps(record),
        "request_headers": request_headers,
        "request_body": {
            "content": request_preview.content,
            "content_type": request_preview.content_type,
            "encoding": request_preview.encoding,
            "total_bytes": request_preview.total_bytes,
            "total_bytes_display": format_bytes(request_preview.total_bytes),
            "truncated": request_preview.truncated,
        },
        "response_body": {
            "content": response_preview.content,
            "content_type": response_preview.content_type,
            "encoding": response_preview.encoding,
            "total_bytes": response_preview.total_bytes,
            "total_bytes_display": format_bytes(response_preview.total_bytes),
            "truncated": response_preview.truncated,
        },
    }
    return JSONResponse(payload)


@app.get("/api/records/{capture_id}/body/{kind}/download")
async def download_body(capture_id: int, kind: str) -> Response:
    if kind not in {"request", "response"}:
        raise HTTPException(status_code=404, detail="unsupported body kind")

    if store.get_record(capture_id) is None:
        raise HTTPException(status_code=404, detail="record not found")

    body = store.read_body_bytes(capture_id, kind)
    suffix = "req" if kind == "request" else "res"
    filename = f"log_{capture_id}_{suffix}"
    return Response(
        content=body,
        media_type="application/octet-stream",
        headers={"content-disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/healthz", response_class=PlainTextResponse)
async def healthz() -> PlainTextResponse:
    db_exists = get_db_path().exists()
    log_dir_exists = get_log_dir().exists()
    return PlainTextResponse(
        f"ok db_exists={db_exists} log_dir_exists={log_dir_exists} pid={os.getpid()}"
    )
