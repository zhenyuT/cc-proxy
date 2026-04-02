# cc-proxy

一个基于 FastAPI 的轻量级代理服务，用于将 OpenAI 兼容请求转发到上游接口，并处理普通响应与流式响应（SSE）。

## 项目特点

- 提供 `/healthz` 健康检查接口
- 透传大多数 HTTP 方法与请求头
- 支持普通 JSON 响应转发
- 支持 `stream=true` 的流式输出
- 可通过环境变量统一注入上游鉴权

## 项目结构

```text
.
├── proxy.py          # FastAPI 应用与代理逻辑
├── requirements.txt  # Python 依赖
├── start.sh          # 本地启动示例
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

如果你不使用 `start.sh`，也可以手动导出环境变量后再运行 `uvicorn`。

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

## 配置项

- `UPSTREAM_BASE`：必填，上游服务基础地址
- `OPENAI_API_KEY`：可选；如果已设置，会覆盖转发请求中的 `Authorization` 头

## 开发建议

- 修改代码后可直接使用 `--reload` 热更新
- 提交前至少执行一次语法检查：

```bash
python -m py_compile proxy.py
```

## 注意事项

- 不要提交真实 API Key、`.env` 文件或虚拟环境目录
- 当前仓库是精简实现，后续可补充 `tests/`、Dockerfile 和更完整的配置说明
