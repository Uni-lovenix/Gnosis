# 检索评测（KB Server）

## 目标

把 `corpus/snippets.md` 作为知识库底料走端到端流水线（解析 → 切片 →
embedding → 入库），再用 `fixtures/cases.json` 里的查询打检索，检查 top-k
是否包含期望片段。

## 运行

### 默认（mock）

```bash
cd server
PYTHONPATH=. python3 eval/run_eval.py
```

退出码 0 表示通过（命中率 ≥ `pass_threshold`，默认 0.6）。
当前迭代记录：**9 / 10 通过 = 90%**。

### 真实 BGE-M3

```bash
cd server
pip install -e ".[embedding-local]"   # 拉 sentence-transformers
./scripts/download_bge_m3.sh          # 把 ~2.4GB 权重放到 server/models/bge-m3
PYTHONPATH=. python3 eval/run_eval.py --embedder bge-m3
```

输出 JSON 会多两个字段：

```json
{
  "backend": "bge-m3",
  "dim": 1024,
  "passed": 10,
  "total": 10,
  "rate": 1.0,
  ...
}
```

真实模型门禁建议：`rate >= 0.8`（≥ 80%）；mock 仍以 60% 为底线。

## 通过策略

- mock 路径保证无外部依赖；CI 默认跑 mock。
- 真实模型仅在本机或带 GPU 的 runner 上跑；CI 不下载权重。
- 同一份 `cases.json` / `corpus/snippets.md` 在两种 backend 下都可重跑。

## 扩展

- 增加 case：编辑 `fixtures/cases.json`。
- 增加底料：在 `corpus/snippets.md` 加 `## doc:xxx` 节即可。
- 改 embedder：注册新类型到 `app/embedding/`，在 `_build_embedder` 里加分发。