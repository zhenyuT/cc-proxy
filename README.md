# cc-proxy

一个基于 FastAPI 的轻量级代理服务，用于将 OpenAI 兼容请求转发到上游接口，并处理普通响应与流式响应（SSE）。现在同时包含抓包落盘与 Web 查看界面。

## 项目特点

- 提供 `/healthz` 健康检查接口
- 透传大多数 HTTP 方法与请求头
- 支持普通 JSON 响应转发
- 支持 `stream=true` 的流式输出
- 可通过环境变量统一注入上游鉴权
- 每次请求自动记录到 SQLite，并将请求体/响应体写入本地文件
- 提供独立 Web 页面查看抓包记录和详情

## 项目结构

```text
.
├── proxy.py          # 代理 FastAPI 应用与抓包埋点
├── dashboard.py      # 抓包查看 Web 页面和 API
├── capture_store.py  # SQLite 与 body 文件存储逻辑
├── requirements.txt  # Python 依赖
├── start.sh          # 同时启动代理和查看端
├── README.md
└── .gitignore
```

## 运行环境

- Python 3.10+
- Linux / macOS / WSL 均可

## 安装依赖

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 启动方式

项目强制从环境变量读取 `UPSTREAM_BASE`，不会在代码中内置默认上游地址。

先编辑 `.env`：

```bash
UPSTREAM_BASE="https://your-upstream.example.com"
OPENAI_API_KEY="your_api_key"
```

然后启动：

```bash
./start.sh
```

如果你不使用 `start.sh`，也可以手动导出环境变量后分别运行：

```bash
uvicorn proxy:app --host 0.0.0.0 --port 9000 --reload
uvicorn dashboard:app --host 0.0.0.0 --port 8888 --reload
```

## 接口说明

### 健康检查

```bash
curl http://127.0.0.1:9000/healthz
```

### 代理调用

服务会将请求转发到：

```text
{UPSTREAM_BASE}/{path}
```

例如：

```bash
curl http://127.0.0.1:9000/v1/models
```

流式请求示例：

```bash
curl http://127.0.0.1:9000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","stream":true,"messages":[{"role":"user","content":"hello"}]}'
```

### 抓包查看页面

默认地址：

```bash
http://127.0.0.1:8888/
```

页面能力：

- 请求列表按开始时间倒序展示
- 点击详情查看请求头、请求体、响应体
- 大 body 默认只展示预览，支持下载完整原始内容

## 配置项

- `UPSTREAM_BASE`：必填，上游服务基础地址
- `OPENAI_API_KEY`：可选；如果已设置，会覆盖转发请求中的 `Authorization` 头
- `PROXY_PORT`：可选，代理端口，默认 `9000`
- `DASHBOARD_PORT`：可选，抓包查看端口，默认 `8888`
- `CC_PROXY_DB_PATH`：可选，SQLite 路径，默认 `~/.cc-proxy/sqlite.db`
- `CC_PROXY_LOG_DIR`：可选，body 文件目录，默认 `~/.cc-proxy/logs`

## 抓包存储说明

- SQLite 默认保存到 `~/.cc-proxy/sqlite.db`
- 请求体保存到 `~/.cc-proxy/logs/log_{id}_req`
- 响应体保存到 `~/.cc-proxy/logs/log_{id}_res`
- SQLite 表字段包含：
  - `id`
  - `request_url`
  - `request_headers`
  - `started_at`
  - `finished_at`
  - `duration_ms`

流式响应会在转发给客户端的同时持续写入 `log_{id}_res`，确保查看页能看到完整响应内容。

## 开发建议

- 修改代码后可直接使用 `--reload` 热更新
- 提交前至少执行一次语法检查：

```bash
python -m py_compile proxy.py
```

## 注意事项

- 不要提交真实 API Key、`.env` 文件或虚拟环境目录
- 当前仓库是精简实现，后续可补充 `tests/`、Dockerfile 和更完整的配置说明
