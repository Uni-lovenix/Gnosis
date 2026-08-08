# OpenAI 兼容远端重试退避迭代协议（G5）

> 第二轮 Goal 段第五个迭代：收敛 `docs/KNOWN_ISSUES.md` 的 KI-03（OpenAI 兼容远端无指数退避），让 embedding pipeline 在远程 Ollama / vLLM 抖动时自动恢复。

## 目标

为 `OpenAICompatEmbedder` 增加指数退避重试：**只对瞬时错误重试**（`httpx.TransportError` / HTTP 5xx / 429），配置错误立即抛。提供可调参（`max_retries` / `initial_backoff` / `max_backoff` / `backoff_jitter`）和 `embedder.retry` 结构化日志。**不**改 `Embedder` 抽象契约（其它 embedder 不动）。

## 范围

### 1. 重试策略

`server/app/embedding/openai_compat.py`：

| 错误类型 | 行为 |
|---|---|
| `httpx.TransportError`（`ConnectError` / `TimeoutException` / `ReadError` / `BrokenPipeError`） | 重试 |
| HTTP 429 / 5xx | 重试 |
| HTTP 400 / 401 / 403 / 404 / 4xx 其它 | 立即抛 `EmbedderError`（配置错误，重试无益） |

退避：`sleep = min(initial_backoff × 2^(n-1), max_backoff) × (1 ± backoff_jitter)`；默认 `initial=0.5s`、`max=8s`、`jitter=0.1`、`max_retries=3`（初始 + 3 次重试 = 4 次尝试）。

每次重试打：

```json
{"event": "embedder.retry", "log_level": "warning",
 "attempt": N, "max_attempts": total, "status_code": 503 | "error_kind": "ConnectError",
 "sleep_seconds": 0.48}
```

超过 `max_retries` 抛 `EmbedderError("remote embed failed after N attempt(s): ...")`，不掩盖原始异常。

### 2. 配置选项

`EmbedderConfig.options`：

| Key | Type | Default | 语义 |
|---|---|---|---|
| `max_retries` | int ≥ 0 | 3 | 重试次数（不含初始调用） |
| `initial_backoff` | float ≥ 0 | 0.5 | 首次重试前 sleep 秒数 |
| `max_backoff` | float ≥ 0 | 8.0 | 单次 sleep 上限 |
| `backoff_jitter` | float ∈ [0, 1] | 0.1 | ±jitter 比例 |

`max_retries=0` 完全禁用重试。

### 3. 测试

`server/tests/embedding/test_embedders.py`：

- 提取 `_Resp` 到模块级；新增 `_ScriptedTransport` + `_RecordingClient` 让任何 POST 都能逐次返回预期结果（`ok` / `status(N)` / `transport(类名)`）。
- 新增 7 项单测：
  1. 瞬时错误 → 重试 → 成功
  2. 全部耗尽 → `EmbedderError` 含 attempts 数与原异常类名
  3. 400 不重试，单次抛错，无 sleep
  4. 429 重试后成功
  5. 5xx（502/503）重试后成功
  6. 退避数学：`initial=0.5, max=2.0` → `[0.5, 1.0, 2.0, 2.0]`
  7. `embedder.retry` 日志包含 attempt / max_attempts / error_kind / log_level=warning

### 4. 文档

| 文档 | 改动 |
|---|---|
| `docs/RUNBOOK.md` | 在 §2 后新增 `### 2a. OpenAI 兼容远端的重试退避（KI-03）`：重试矩阵 + 调参示例 + 日志字段说明 |
| `docs/KNOWN_ISSUES.md` | KI-03 移入 G5 收敛表（带代码位置 + 测试覆盖） |
| `docs/goal/01-mapping.md` | "向量化" 行增 KI-03 引用 |
| `feature_list.json` | 新增 `feat-ki03-retry-backoff` 条目 |
| `progress.md` / `session-handoff.md` | G5 记录 + 决策 |

## 退出标准

- [x] `server/app/embedding/openai_compat.py` 实现指数退避，仅对瞬时错误重试
- [x] 可调参（4 个 options），有最大与抖动边界
- [x] 每次重试打 `embedder.retry` 结构化日志
- [x] 7 项新单测全部通过；pytest 全套 113 → 120 passed
- [x] `npm run verify` 全绿
- [x] `npm run check` / `npm run lint`（tsc --noEmit）0 errors
- [x] 文档收敛（RUNBOOK §2a / KNOWN_ISSUES 收敛表 / feature_list 新条目 / progress G5 / session-handoff G5）
- [x] 不改 `Embedder` 抽象 / 不改其它 embedder（bge-m3 / mock-hash 不动）

## 决策记录

- **不**做"任何异常都重试"——配置错误的 4xx 重试只会浪费时间，让用户立即看见清晰错误更有价值。
- **不**改抽象契约：retry 是 openai-compat 的实现细节，其它 embedder 不背这个复杂度。mock-hash 没网络问题；bge-m3 本地推理不需要重试。
- **不**引入第三方 retry 库（如 `tenacity`）——单文件 ~30 行可解决，避免新依赖。
- jitter 默认 10%：是灵知 (Gnosis) 的 desktop 用户规模，雪崩风险低，但仍然是好习惯。
- `kb_status_code` / `kb_retryable` 是绑定到 `EmbedderError` 的辅助 attr，不影响既有 `EmbedderError` 契约；调用方依赖 `isinstance(e, EmbedderError)` 即可。
