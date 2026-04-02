# Repository Guidelines

## Project Structure & Module Organization
This repository is a small FastAPI-based proxy service.

- [`proxy.py`](/data/github/cc-proxy/proxy.py) contains the application, routing, upstream request handling, and streaming logic.
- [`requirements.txt`](/data/github/cc-proxy/requirements.txt) lists the runtime dependencies.
- [`start.sh`](/data/github/cc-proxy/start.sh) shows the intended local launch command.
- `.venv/` is a local virtual environment and should not be committed.

If the codebase grows, keep HTTP entrypoints in `proxy.py` or move them into a `app/` package, and place tests under `tests/`.

## Build, Test, and Development Commands
- `python -m venv .venv && . .venv/bin/activate`: create and activate a local virtual environment.
- `pip install -r requirements.txt`: install FastAPI, Uvicorn, `httpx`, and `aiohttp`.
- `uvicorn proxy:app --host 0.0.0.0 --port 9000 --reload`: run the proxy locally with auto-reload.
- `python -m py_compile proxy.py`: quick syntax check before submitting changes.

There is no Makefile or packaged build step at the moment.

## Coding Style & Naming Conventions
Follow standard Python conventions:

- Use 4-space indentation and keep imports grouped: standard library, third-party, local.
- Prefer `snake_case` for functions and variables, `UPPER_SNAKE_CASE` for module-level constants such as `UPSTREAM_BASE`.
- Keep request/response handling explicit; avoid hidden side effects in middleware-like code paths.
- Add short comments only where streaming or error-handling behavior is non-obvious.

## Testing Guidelines
There is no committed test suite yet. Add tests for any behavior change, especially around:

- `/healthz` responses
- header forwarding and auth injection
- JSON passthrough
- streaming and SSE edge cases

Use `pytest` with files named `tests/test_<feature>.py` when introducing tests.

## Commit & Pull Request Guidelines
This repository currently has no commit history, so use a simple baseline:

- Write commit messages in the imperative mood, for example: `Fix SSE shutdown handling`.
- Keep commits focused on one change.
- Pull requests should describe the behavior change, note any new environment variables, and include curl examples for API-facing changes.

## Security & Configuration Tips
Do not commit real API keys. Set `OPENAI_API_KEY` and `UPSTREAM_BASE` through environment variables instead of hardcoding secrets in scripts.
