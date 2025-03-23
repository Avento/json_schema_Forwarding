# fastapi for forwarding all LLM request
# uvicorn fastapi_app:app --host 0.0.0.0 --port 8000 --workers 8 --loop uvloop --http httptools

from fastapi import FastAPI, Request
import httpx
from starlette.responses import Response
import json
import logging
import os
import asyncio

# 配置常量
TARGET_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"
# TARGET_BASE_URL = "https://gblqzvdqvmdinphtdwmbtdfu8fu5ai47k.oast.fun"
TARGET_HOST = "ark.cn-beijing.volces.com"
MAX_CONNECTIONS = 600
LOG_SAMPLE_RATE = 1.0  # 1%日志采样率
# 建议调整的常量值（单位：秒）
TIMEOUT_CONNECT = 5.0    # 原3.0 → 5.0 (建立连接超时)
TIMEOUT_READ = 30.0      # 原10.0 → 30.0 (读取响应超时)
TIMEOUT_WRITE = 10.0     # 新增写超时
MAX_RETRIES = 3          # 原2 → 3 (重试次数)
KEEPALIVE_TIMEOUT = 75   # 新增连接保持时间

app = FastAPI()

class CustomClient:
    def __init__(self):
        self.client = None
        self.limits = httpx.Limits(
            max_connections=MAX_CONNECTIONS,
            max_keepalive_connections=MAX_CONNECTIONS//2
        )

    # 修改后的正确配置
    async def startup(self):
        transport = httpx.AsyncHTTPTransport(retries=MAX_RETRIES)
        self.client = httpx.AsyncClient(
            transport=transport,
            limits=self.limits,
            timeout=httpx.Timeout(
                connect=TIMEOUT_CONNECT,
                read=TIMEOUT_READ,
                write=TIMEOUT_CONNECT,  # 新增写超时
                pool=TIMEOUT_CONNECT    # 新增连接池超时
            ),
            http2=True
        )


    async def shutdown(self):
        if self.client:
            await self.client.aclose()

client_wrapper = CustomClient()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("uvicorn")
logger.propagate = False

def should_log() -> bool:
    return os.urandom(1)[0] < 256 * LOG_SAMPLE_RATE

async def log_request(request: Request, content: bytes):
    if not should_log():
        return

    try:
        # body = content.decode('utf-8', errors='replace')[:1000]
        body = content.decode('utf-8', errors='replace')
    except UnicodeDecodeError:
        body = "<binary data>"

    logger.info(f"Request[{request.method} {request.url}]: {body}")

async def log_response(response: httpx.Response):
    if not should_log():
        return

    try:
        content = response.content.decode('utf-8', errors='replace')
        # content = response.content.decode('utf-8', errors='replace')[:500]
    except UnicodeDecodeError:
        content = "<binary data>"

    logger.info(f"Response[{response.status_code}]: {content}")

def modify_content(data: bytes) -> bytes:
    return data.replace(b"json_schema", b"json_object")

async def forward_request(request: Request):
    content = await request.body()
    # logging.INFO("Replaceing json_schema...")
    modified_content = modify_content(content)
    # logging.INFO("Replaceing json_schema success!")
    print("AAA")

    target_url = f"{TARGET_BASE_URL}{request.url.path}"
    headers = {
        "Host": TARGET_HOST,
        "Authorization": request.headers.get("Authorization", ""),
        "Content-Type": request.headers.get("Content-Type", "application/json"),
        "Connection": "keep-alive"
    }

    try:
        await log_request(request, content)
        response = await client_wrapper.client.request(
            method=request.method,
            url=target_url,
            headers=headers,
            content=modified_content
        )
        await log_response(response)

        return Response(
            content=modify_content(response.content),
            status_code=response.status_code,
            headers=dict(response.headers)
        )

    except httpx.ConnectTimeout:
        logger.warning("Connection timeout")
        return Response(
            content=json.dumps({"error": "Upstream connection timeout"}),
            status_code=504
        )
    except httpx.ReadTimeout:
        logger.warning("Read timeout")
        return Response(
            content=json.dumps({"error": "Upstream response timeout"}),
            status_code=504
        )
    except Exception as e:
        logger.exception(f"Unexpected error: {str(e)}")
        return Response(
            content=json.dumps({"error": "Internal server error"}),
            status_code=500
        )

@app.on_event("startup")
async def startup():
    await client_wrapper.startup()

@app.on_event("shutdown")
async def shutdown():
    await client_wrapper.shutdown()

@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"])
async def catch_all(request: Request, path: str):
    return await forward_request(request)

if __name__ == "__main__":
    import uvicorn
    import sys

    worker_config = {
        "host": "0.0.0.0",
        "port": 8000,
        "loop": "uvloop",
        "http": "httptools",
        "timeout_keep_alive": 60,
        "log_config": None
    }

    if "--dev" in sys.argv:
        uvicorn.run("fastapi_app:app", reload=True, **worker_config)
    else:
        uvicorn.run(
            "fastapi_app:app",
            workers=os.cpu_count(),
            **worker_config
        )
