# 版本变更记录

## 2026-10-23：KEV 开发前基线

此基线用于在现有招聘 Agent 上继续开发 KEV/Laya 简历初筛流程。代码包含以下能力：

- **对话记忆**：LangGraph 对话检查点写入 SQLite；用户长期记忆支持保存、检索和删除。会话历史限制长度，简历正文以候选人引用形式压缩后再保存。
- **可恢复的简历摄取**：上传文件以 SHA-256 识别，摄取阶段和中间产物可持久化；Redis/ARQ 模式支持任务状态查询、重试和向量幂等 upsert。Compose 当前默认走同步模式。
- **候选人上下文**：候选人完整简历作为结构化数据返回给 API/前端；Agent 为多候选人比较准备压缩上下文，优先从规则提取字段，并在必要时调用 LLM 补充。
- **前端/API 联动**：聊天结果展示候选人卡片和完整简历；API 默认使用同源 `/api`，适配反向代理部署。
- **飞书集成**：可选接收飞书消息事件并交给现有 Recruitment Agent 处理，支持事件校验、加密消息解密和回调去重。
- **可观测性**：可选 Langfuse 记录 Agent、模型和工具调用；默认不捕获原始提示词和简历正文。
- **部署配置**：Docker Compose 构建前后端，健康检查通过后启动前端；ChromaDB 与应用数据使用宿主机目录持久化。
- **评估与测试**：增加简历上下文测试和 RAG 评估程序，支持核对候选人身份、检索事实、重复候选人及禁止替代候选人。

### 当前业务流程边界

当前简历上传后会直接进入解析、分块、Embedding 和向量入库流程。KEV/Laya 预筛、岗位级初筛记录、自动排除状态和人工复核队列尚未实现。后续实现时应保留原始简历，并按岗位保存判断结果，避免把某岗位不匹配等同于候选人永久淘汰。

### 当前分支改动范围

- Agent 图节点、状态、工具与对话处理：`backend/app/agents/`
- REST API、飞书 webhook、配置及依赖注入：`backend/app/api/`、`backend/app/config.py`、`backend/app/dependencies.py`
- 检索、简历上下文抽取及向量存储：`backend/app/rag/`、`backend/app/services/`、`backend/app/agents/resume_context.py`
- Langfuse 观测适配器：`backend/app/observability/`
- 前端聊天结果展示与 API 地址：`frontend/src/`
- Docker 部署：根目录 `docker-compose.yml`、后端/前端 Dockerfile 与 Nginx 配置

### 未纳入版本控制的本地文件

本次基线不包含 `.env`、简历与 ChromaDB 数据、ZIP 打包件、调试输出以及 RAG 评测样本/结果。评测文件可能包含真实候选人姓名、简历片段或其他个人信息；请在本机保留，需要共享时先用合成数据替换。
