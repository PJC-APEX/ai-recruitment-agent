# RAG 评估

评估器调用正在运行的 `/api/chat`，对 Agent 返回的候选人身份、检索事实、重复结果和禁止替换的候选人进行可重复检查。Groundedness 与幻觉判断仍需要人工复核。

评估用例通常包含真实人才库中的姓名、简历文件名或事实，因此 `rag_cases.jsonl` 不随仓库发布。请基于自己的本地测试人才库创建该文件，或将 JSONL 放在仓库外，通过 `--cases` 指定。不要把真实候选人资料提交到 Git。

每行一个 JSON 对象，常用字段如下：

- `id`：稳定的用例编号。
- `category`：用例类别，例如 `exact_name`、`skill_search` 或 `multi_candidate_compare`。
- `query`：发送给 Agent 的问题。
- `expected_candidate` / `expected_file`：预期的候选人或简历文件。
- `expected_files`：多候选人场景预期返回的文件。
- `expected_facts`：回答中应有依据的事实。
- `forbidden_candidates`：不应被误认或替代的候选人。
- `expected_no_documents`：预期不返回完整简历时设为 `true`。

在后端目录运行：

```powershell
python -m evals.run_rag_eval --cases .\evals\rag_cases.jsonl
```

也可以使用仓库外的绝对路径：

```powershell
python -m evals.run_rag_eval --cases D:\private-recruiting-data\rag_cases.jsonl
```

默认结果文件为 `backend/rag_eval_results.json` 和 `backend/rag_eval_summary.json`，两者都属于本地运行产物并由 `.gitignore` 排除。需要将 trace 和评分写到 Langfuse 时增加 `--langfuse`；该选项要求 Langfuse 已启用并正确配置。
