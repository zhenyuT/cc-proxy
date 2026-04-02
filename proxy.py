import os
import json
import logging

import aiohttp
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import Response, StreamingResponse


logger = logging.getLogger("cc_proxy")

app = FastAPI()

def get_required_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


UPSTREAM_BASE = get_required_env("UPSTREAM_BASE").rstrip("/")
API_KEY = os.environ.get("OPENAI_API_KEY", "")


def mask_secret(value: str) -> str:
    if not value:
        return "<empty>"
    if len(value) <= 8:
        return "***"
    return f"{value[:4]}...{value[-4:]}"


logger.warning("UPSTREAM_BASE=%s", UPSTREAM_BASE)
logger.warning("OPENAI_API_KEY=%s", mask_secret(API_KEY))


@app.get("/healthz")
async def healthz():
    return {"ok": True, "upstream": UPSTREAM_BASE}


@app.api_route(
    "/{path:path}",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def proxy(path: str, request: Request):
    upstream_url = f"{UPSTREAM_BASE}/{path}"

    headers = dict(request.headers)
    headers.pop("host", None)

    if API_KEY:
        headers["authorization"] = f"Bearer {API_KEY}"

    body = await request.body()
    wants_stream = False
    if body:
        try:
            payload = json.loads(body)
            wants_stream = bool(payload.get("stream"))
        except json.JSONDecodeError:
            pass
    timeout = httpx.Timeout(connect=30.0, read=None, write=30.0, pool=None)

    if wants_stream:
        timeout_cfg = aiohttp.ClientTimeout(total=None, connect=30, sock_connect=30, sock_read=None)
        session = aiohttp.ClientSession(timeout=timeout_cfg, trust_env=True)
        upstream_resp = await session.request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            data=body,
            params=request.query_params,
        )

        resp_headers = dict(upstream_resp.headers)
        for key in ("content-length", "content-encoding", "transfer-encoding", "connection"):
            resp_headers.pop(key, None)
        resp_headers["cache-control"] = "no-cache"
        resp_headers["x-accel-buffering"] = "no"

        async def sse_iterator():
            try:
                async for chunk in upstream_resp.content.iter_any():
                    if chunk:
                        yield chunk
            finally:
                upstream_resp.close()
                await session.close()

        return StreamingResponse(
            sse_iterator(),
            status_code=upstream_resp.status,
            headers=resp_headers,
            media_type="text/event-stream",
        )

    async with httpx.AsyncClient(timeout=timeout, http2=False, trust_env=True) as client:
        upstream_req = client.build_request(
            method=request.method,
            url=upstream_url,
            headers=headers,
            content=body,
            params=request.query_params,
        )
        upstream_resp = await client.send(upstream_req, stream=True)

        resp_headers = dict(upstream_resp.headers)
        for key in ("content-length", "content-encoding", "transfer-encoding", "connection"):
            resp_headers.pop(key, None)

        content_type = upstream_resp.headers.get("content-type", "")
        if "application/json" in content_type and "text/event-stream" not in content_type:
            data = await upstream_resp.aread()
            await upstream_resp.aclose()
            return Response(
                content=data,
                status_code=upstream_resp.status_code,
                headers=resp_headers,
                media_type=content_type or None,
            )

        is_event_stream = "text/event-stream" in content_type

        async def iterator():
            try:
                if is_event_stream:
                    async for line in upstream_resp.aiter_lines():
                        if not line:
                            yield b"\n"
                            continue
                        yield line.encode("utf-8") + b"\n"
                    return

                async for chunk in upstream_resp.aiter_raw():
                    yield chunk
            except (httpx.ReadError, httpx.RemoteProtocolError):
                # The upstream sometimes closes streaming responses abruptly after
                # sending the useful data. Stop cleanly instead of crashing ASGI.
                if is_event_stream:
                    yield b"data: [DONE]\n\n"
                return
            finally:
                await upstream_resp.aclose()

        if is_event_stream:
            resp_headers["cache-control"] = "no-cache"
            resp_headers["x-accel-buffering"] = "no"

        return StreamingResponse(
            iterator(),
            status_code=upstream_resp.status_code,
            headers=resp_headers,
            media_type="text/event-stream" if is_event_stream else upstream_resp.headers.get("content-type"),
        )
