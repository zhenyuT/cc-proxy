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
    @media (max-width: 980px) {{
      .grid {{ grid-template-columns: 1fr; }}
      .card {{ min-height: auto; }}
      #record-list, #detail {{ max-height: none; }}
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
  <script>
    const state = {{ activeId: null }};

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

    function formatBodyContent(body) {{
      if (!body.content) {{
        return "(empty)";
      }}
      if (body.content_type === "base64") {{
        return body.content;
      }}
      try {{
        return JSON.stringify(JSON.parse(body.content), null, 2);
      }} catch (_error) {{
        return body.content;
      }}
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

    function bodyBlock(kind, body) {{
      const label = kind === "request" ? "请求体" : "响应体";
      const downloadUrl = `/api/records/${{state.activeId}}/body/${{kind}}/download`;
      const copy = body.content_type === "base64"
        ? "二进制内容，以下为 base64 预览。"
        : "文本预览。";
      const prettyContent = formatBodyContent(body);
      const encodedContent = encodeURIComponent(body.content || "");
      return `
        <div class="section">
          <h3>${{label}}</h3>
          <div class="body-actions">
            <span class="pill">大小 ${{body.total_bytes_display}}</span>
            <span class="pill">${{escapeHtml(copy)}}</span>
            ${{body.truncated ? '<span class="pill">预览已截断</span>' : ''}}
            <a href="${{downloadUrl}}"><button class="ghost">下载完整内容</button></a>
          </div>
          <div class="body-toolbar">
            <button class="ghost js-copy-body" data-copy="${{encodedContent}}">复制内容</button>
            ${{body.content_type !== "base64" ? '<span class="pill">JSON 自动美化</span>' : ''}}
          </div>
          <pre>${{escapeHtml(prettyContent)}}</pre>
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
    }}

    document.getElementById("refresh-btn").addEventListener("click", loadList);
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
