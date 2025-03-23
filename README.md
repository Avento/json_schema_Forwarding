[中文文档](./README-zh.md)
# FastAPI Request Forwarding Proxy for `json_schema` Service
A temporary solution to address the `json_schema` incompatibility issue (e.g., with Deepseek v3) in custom LLMs when using [openai-agents-python](https://github.com/openai/openai-openai-agents-python).
> **Structured Outputs Support**  
> Some model providers lack structured output support, which may result in errors like:  
> `BadRequestError: Error code: 400 - {'error': {'message': "'response_format.type' : value is not one of the allowed values ['text','json_object']", 'type': 'invalid_request_error'}}`  
> This proxy addresses providers that support JSON outputs but don't allow `json_schema` specification.

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
$ hey -z 30s -c 100 -m POST -H "Content-Type: application/json" -H "Authorization: Bearer xx-xx-xx" -d '{"model":"ep-xx","messages":[{"role":"system","content":"You are a helpful assistant."},{"role":"user","content":"Hello!"}]}' http://0.0.0.0:8000/chat/completions  

Requests/sec: 111.4224  
Latency distribution:  
  50% in 0.6781s  
  99% in 1.9287s  
```  

### Ideal Performance (Direct Access)
```bash  
$ hey -z 30s -c 100 -m POST https://ark.cn-beijing.volces.com/api/v3/chat/completions ...  

Requests/sec: 5223.7164  
Latency distribution:  
  50% in 0.0129s  
  99% in 0.2424s  
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
