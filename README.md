[中文文档](./README-zh.md)
# FastAPI Request Forwarding Proxy for `json_schema` Service
A temporary solution to address the `json_schema` incompatibility issue (e.g., with Deepseek v3) in custom LLMs when using [openai-agents-python](https://github.com/openai/openai-openai-agents-python).
> **Structured Outputs Support**  
> Some model providers lack structured output support, which may result in errors like:  
> `BadRequestError: Error code: 400 - {'error': {'message': "'response_format.type' : value is not one of the allowed values ['text','json_object']", 'type': 'invalid_request_error'}}`  
> This proxy addresses providers that support JSON outputs but don't allow `json_schema` specification.


![image](https://github.com/user-attachments/assets/09d73124-9318-4c0a-96f2-8539ea8d20f6)

## 📦 Requirements
- Python 3.10+
- Install dependencies using UV package manager:
```bash  
uv pip install fastapi uvicorn httpx uvloop httptools  
```  

## 🚀 Core Features
### Request Forwarding
- Full HTTP method support: `GET/POST/PUT/DELETE/PATCH/HEAD/OPTIONS`
- Header passthrough: Preserves `Authorization`, `Content-Type`, etc.
- Automatic path mapping: `/your_path → {TARGET_BASE_URL}/your_path`

### Content Processing
```python  
# Automatic string replacement (request/response bodies)  
json_schema ⇨ json_object  # Binary-safe replacement  
```  

### Performance Optimization
```yaml  
Connection Pool:  
  max_connections: 600      # Max concurrent connections  
  max_keepalive: 300        # Persistent connections  

Protocol Support:  
  HTTP/2: Enabled  
  Keep-Alive: 75s  
```  

## ⚡ Startup Commands
### Development Mode (with hot reload)
```bash  
uvicorn fastapi_app:app --reload \  
--host 0.0.0.0 --port 8000 \  
--loop uvloop --http httptools  
```  

### Production Mode (8 workers)
```bash  
uvicorn fastapi_app:app \  
--host 0.0.0.0 --port 8000 \  
--workers 8 \  
--loop uvloop \  
--http httptools \  
--timeout-keep-alive 75  
```  

## 🔧 Configuration
```python  
# Constants in fastapi_app.py  
TARGET_BASE_URL = "https://ark.cn-beijing.volces.com/api/v3"  # Target service  
TARGET_HOST = "ark.cn-beijing.volces.com"                     # Forced Host header  

# Timeout policies (seconds)  
TIMEOUT_CONNECT = 5.0    # Connection establishment  
TIMEOUT_READ = 30.0      # Response read  
TIMEOUT_WRITE = 10.0     # Request send  
MAX_RETRIES = 3          # Retry attempts  

# Log sampling (1.0=100% logging)  
LOG_SAMPLE_RATE = 0.01   # Recommended 1% for production  
```  

## 🛡️ Reliability Design
### Error Handling
```yaml  
Recoverable Errors:  
  - Network jitter: Auto-retry (MAX_RETRIES)  
  - Temporary timeout: 504 response + error classification  

Non-recoverable Errors:  
  - Protocol errors: 400 response  
  - System failures: 500 response + sanitized error  
```  

### Protection Strategies
- Memory protection: Request size limit (default unlimited, add `request.body(max_size=10_000_000)`)
- Connection leak prevention: Automatic cleanup
- Fault isolation: Single request failures don't affect service

## 📊 Monitoring Metrics
```bash  
# Built-in log types  
CONNECTION_TIMEOUT    # Connection timeout count  
READ_TIMEOUT          # Response read timeout  
RETRY_EXHAUSTED       # Retry exhaustion  
UNEXPECTED_ERROR      # Uncaught exceptions  
```  

## 🚨 Best Practices
1. **Production Deployment**:
    - Use Nginx as reverse proxy
    - Set `workers = CPU cores * 2 + 1`
    - Monitor `MAX_CONNECTIONS` usage

2. **Security**:
    - Sensitive headers (e.g., `Authorization`) excluded from logs
    - Enable firewall IP restrictions

3. **Tuning Guide**:
   ```python  
   # Connection formula  
   MAX_CONNECTIONS = workers * 75  # 8 workers → 600  
   
   # Timeout principle  
   TIMEOUT_READ > Upstream max response time + 10s  
   ```  

## ✊ Load Testing
### Forwarding Performance
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

### Ideal Performance (Direct Access)
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
MIT License - Free to modify and deploy, please retain original author information

---  
This document covers:
1. One-click deployment guide
2. Visual feature explanations
3. Production-grade configuration
4. Reliability design details
5. Performance tuning formulas
6. Security best practices
