# FastAPI 请求转发代理 `json_schema` 服务
一个解决（例如 Deepseek v3 等）自定义 LLM 在 [openai-agents-python](https://github.com/openai/openai-agents-python) 不支持 `json_schema` 问题的临时方案。
>Structured outputs support
Some model providers don't have support for structured outputs. This sometimes results in an error that looks something like this:
>`BadRequestError: Error code: 400 - {'error': {'message': "'response_format.type' : value is not one of the allowed values ['text','json_object']", 'type': 'invalid_request_error'}}`
This is a shortcoming of some model providers - they support JSON outputs, but don't allow you to specify the json_schema to use for the output. We are working on a fix for this, but we suggest relying on providers that do have support for JSON schema output, because otherwise your app will often break because of malformed JSON.
![image](https://github.com/user-attachments/assets/09d73124-9318-4c0a-96f2-8539ea8d20f6)

## 📦 环境要求
- Python 3.10+
- 使用 UV 包管理器安装依赖：
```bash
uv pip install fastapi uvicorn httpx uvloop httptools
```

## 🚀 核心功能
### 请求代理
- 全方法支持：`GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS`
- 请求头透传：保留 `Authorization`、`Content-Type` 等关键头信息
- 路径自动映射：`/your_path → {TARGET_BASE_URL}/your_path`

### 内容处理
```python
# 自动执行字符串替换（请求体+响应体）
json_schema ⇨ json_object  # 支持二进制安全替换
```

### 性能优化
```yaml
连接池:
  max_connections: 600       # 最大并发连接数
  max_keepalive: 300         # 保持活跃连接数

协议支持:
  HTTP/2: 启用
  Keep-Alive: 75秒
```

## ⚡ 启动命令
### 开发模式（带热重载）
```bash
uvicorn fastapi_app:app --reload \
--host 0.0.0.0 --port 8000 \
--loop uvloop --http httptools
```

### 生产模式（8 workers）
```bash
uvicorn fastapi_app:app \
--host 0.0.0.0 --port 8000 \
--workers 8 \
--loop uvloop \
--http httptools \
--timeout-keep-alive 75
```

## 🔧 配置说明
```python
# fastapi_app.py 顶部常量
TARGET_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"  # 目标服务地址
TARGET_HOST = "ark.cn-beijing.volces.com"                     # 强制Host头

# 超时策略（单位：秒）
TIMEOUT_CONNECT = 5.0    # 连接建立
TIMEOUT_READ = 30.0      # 响应读取  
TIMEOUT_WRITE = 10.0     # 请求发送
MAX_RETRIES = 3          # 失败重试次数

# 日志采样率（1.0=100%记录）
LOG_SAMPLE_RATE = 0.01   # 生产环境建议1%采样
```

## 🛡️ 可靠性设计
### 错误处理机制
```yaml
可恢复错误:
  - 网络抖动: 自动重试(MAX_RETRIES)
  - 临时超时: 504响应 + 错误分类

不可恢复错误:
  - 协议错误: 400响应
  - 系统异常: 500响应 + 安全错误信息
```

### 防御策略
- 内存保护：请求体大小限制（默认无限制，可添加`request.body(max_size=10_000_000)`）
- 连接泄漏防护：自动清理闲置连接
- 异常隔离：单个请求错误不影响整体服务

## 📊 监控指标
```bash
# 内置日志类型
CONNECTION_TIMEOUT    # 连接超时计数
READ_TIMEOUT          # 响应读取超时
RETRY_EXHAUSTED       # 重试耗尽事件
UNEXPECTED_ERROR      # 未捕获异常
```

## 🚨 注意事项
1. **生产部署**：
    - 建议配合 Nginx 作为反向代理
    - 设置 `workers = CPU核心数 * 2 + 1`
    - 监控 `MAX_CONNECTIONS` 使用率

2. **安全建议**：
    - 敏感头信息（如`Authorization`）不会记录日志
    - 开启防火墙限制来源IP

3. **调优指南**：
   ```python
   # 连接数公式
   MAX_CONNECTIONS = workers * 75  # 8 workers → 600
   
   # 超时设置原则
   TIMEOUT_READ > 上游服务最大响应时间 + 10秒
   ```

## ✊压力测试
转发性能
```bash
$ hey -z 30s -c 100 -m POST   -H "Content-Type: application/json"   -H "Authorization: Bearer xx-xx-xx"   -d '{
    "model": "ep-xx",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello!"}
    ]
  }'   http://0.0.0.0:8000/chat/completions

Summary:
  Total:        33.2698 secs
  Slowest:      3.5171 secs
  Fastest:      0.4390 secs
  Average:      0.8242 secs
  Requests/sec: 111.4224

  Total data:   1815019 bytes
  Size/request: 489 bytes

Response time histogram:
  0.439 [1]     |
  0.747 [2664]  |■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
  1.055 [390]   |■■■■■■
  1.362 [87]    |■
  1.670 [453]   |■■■■■■■
  1.978 [81]    |■
  2.286 [11]    |
  2.594 [11]    |
  2.901 [4]     |
  3.209 [1]     |
  3.517 [4]     |


Latency distribution:
  10% in 0.5930 secs
  25% in 0.6294 secs
  50% in 0.6781 secs
  75% in 0.7686 secs
  90% in 1.4647 secs
  95% in 1.5708 secs
  99% in 1.9287 secs

Details (average, fastest, slowest):
  DNS+dialup:   0.0001 secs, 0.4390 secs, 3.5171 secs
  DNS-lookup:   0.0000 secs, 0.0000 secs, 0.0000 secs
  req write:    0.0001 secs, 0.0000 secs, 0.0213 secs
  resp wait:    0.8237 secs, 0.4388 secs, 3.5168 secs
  resp read:    0.0001 secs, 0.0000 secs, 0.0013 secs

Status code distribution:
  [200] 3707 responses
```
非转发理想性能
```bash
$ hey -z 30s -c 100 -m POST https://ark.cn-beijing.volces.com/api/v3/chat/completions   -H "Content-Type: application/json"   -H "Authorization: Bearer xx-xx-xx"   -d '{       "model": "ep-xxx",
    "messages": [
        {
            "role": "system",
            "content": "You are a helpful assistant."
        },
        {
            "role": "user",
            "content": "Hello!"
        }
    ]
  }'

Summary:
  Total:        30.3043 secs
  Slowest:      3.4912 secs
  Fastest:      0.0085 secs
  Average:      0.0190 secs
  Requests/sec: 5223.7164

  Total data:   33243210 bytes
  Size/request: 210 bytes

Response time histogram:
  0.009 [1]     |
  0.357 [158141]        |■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■
  0.705 [131]   |
  1.053 [27]    |
  1.402 [0]     |
  1.750 [0]     |
  2.098 [0]     |
  2.446 [0]     |
  2.795 [0]     |
  3.143 [0]     |
  3.491 [1]     |


Latency distribution:
  10% in 0.0114 secs
  25% in 0.0120 secs
  50% in 0.0129 secs
  75% in 0.0142 secs
  90% in 0.0165 secs
  95% in 0.0191 secs
  99% in 0.2424 secs

Details (average, fastest, slowest):
  DNS+dialup:   0.0000 secs, 0.0085 secs, 3.4912 secs
  DNS-lookup:   0.0000 secs, 0.0000 secs, 0.0498 secs
  req write:    0.0000 secs, 0.0000 secs, 0.0027 secs
  resp wait:    0.0188 secs, 0.0084 secs, 3.4911 secs
  resp read:    0.0000 secs, 0.0000 secs, 0.0032 secs

Status code distribution:
  [401] 158301 responses
```


## 📜 License
MIT License - 自由修改部署，建议保留原始作者信息

---

该文档完整覆盖：
1. 一键部署指南
2. 核心功能可视化说明
3. 生产级参数配置建议
4. 可靠性设计细节
5. 性能调优公式化指导
6. 安全运维最佳实践
