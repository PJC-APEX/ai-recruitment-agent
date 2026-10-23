# 后端说明

FastAPI 后端负责简历摄取、ChromaDB 检索、岗位评分、LangGraph 招聘 Agent、会话检查点和长期记忆。LLM 与 Embedding 服务通过 OpenAI 兼容客户端配置；仓库提供 Azure OpenAI 环境变量示例。

## 本地启动

需要 Python 3.11 和可访问的聊天/Embedding 模型服务。

```powershell
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

编辑 `.env`，填写 `AZURE_OPENAI_ENDPOINT`、`AZURE_OPENAI_API_KEY`、聊天模型与 Embedding 模型。启动：

```powershell
python -m app.main
```

API 文档位于 <http://localhost:8000/docs>，健康检查为 `/health`。

## API 路由

- `POST /api/upload-resume`：上传 PDF。同步模式下完成解析和向量化后返回；启用队列时返回 `job_id`。
- `GET /api/upload-jobs/{job_id}`：查询摄取任务状态。
- `GET /api/resumes/count`、`GET /api/resumes/list`：查询人才库。
- `POST /api/search-resumes`：语义搜索。
- `POST /api/score-resume`：岗位匹配评分。
- `POST /api/rank-candidates`：检索候选人后进行逐人排序。
- `POST /api/chat`：LangGraph Agent 对话。
- `POST/GET/DELETE /api/memories`：长期记忆管理。
- `POST /api/feishu/events`：可选飞书机器人回调。

实际 schema 以 FastAPI `/docs` 为准。

## 异步简历摄取

本地开发可通过 `INGESTION_QUEUE_ENABLED=true` 和 `REDIS_URL` 开启 ARQ 队列。启动 worker：

```powershell
cd backend
python -m arq app.jobs.worker.WorkerSettings
```

摄取任务按文件 SHA-256 幂等，解析文本、metadata、chunks 和 embeddings 分阶段保存，可通过 job 接口查看 `queued`、`processing`、`indexed` 或 `failed`。API 和 worker 必须共享上传目录、ChromaDB 目录和 `INGESTION_ARTIFACT_DIRECTORY`。当前根目录 Docker Compose 明确关闭队列，避免依赖未配置的 Redis。

## 可选集成

飞书配置使用 `FEISHU_APP_ID`、`FEISHU_APP_SECRET` 和 `FEISHU_VERIFICATION_TOKEN`；如启用加密事件，还需设置 `FEISHU_ENCRYPT_KEY`。生产回调应设置验证 token。

Langfuse 使用 `LANGFUSE_ENABLED=true` 及对应密钥启用 Agent、LLM 和工具调用观测。默认 `LANGFUSE_CAPTURE_CONTENT=false`，提示词和简历正文不会作为观测内容上传。配置在进程启动时读取，变更后需重启后端。

## 测试

```powershell
cd backend
python -m pytest tests -q
```

RAG evaluator 位于 `evals/run_rag_eval.py`。本地评测数据 `evals/rag_cases.jsonl` 和生成结果不应提交，因为它们可能包含真实候选人信息。
