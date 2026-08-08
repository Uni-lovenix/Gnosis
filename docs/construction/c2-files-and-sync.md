# 文件与同步迭代交付（C2）

> 构造阶段第二个迭代的交付物说明。

## 模块清单

| 模块 | 文件 | 说明 |
|---|---|---|
| Excel 解析 | `server/app/parsers/excel.py` | openpyxl → Document；表格 markdown 化 |
| Word 解析 | `server/app/parsers/word.py` | python-docx → Document；段落/标题/表格 |
| PDF 解析 | `server/app/parsers/pdf.py` | pdfplumber → Document；纯文本层 |
| Markdown 解析 | `server/app/parsers/markdown.py` | markdown-it-py → Document；front-matter 剥离 |
| 公共辅助 | `server/app/parsers/_common.py` | MIME 探测 |
| 切片器 | `server/app/chunking/text_chunker.py` | 段落感知 + 字符窗口 + overlap + 硬切 |
| 任务存储 | `server/app/observability/task_store.py` | SQLite 任务状态 |
| Files API | `server/app/api/files.py` | `POST /v1/files/import` + `GET /v1/files/tasks/{id}` |

## 设计要点

- **解析**：每类解析器返回统一的 `Document(source_path, mime, text, metadata)`；失败语义清晰（包缺失 vs 文件损坏）。
- **切片**：paragraph-aware；buf 累积直到超过 `chunk_size` 时 flush，再 `overlap` 续接；超长段落硬切到 sentence/word 边界。默认 `chunk_size=1200, overlap=200`，目标 BGE-M3 的 ~256-512 tokens 实际负载。
- **任务持久化**：SQLite 单表 `tasks`；重启后可读历史状态。C3 写 embedding + 入库时同样 update 进度。
- **失败处理**：解析失败回 422 并把 task 标记为 `failed`；空文件 400；不支持类型 415。

## 验证证据

```bash
$ pytest
57 passed in 0.64s
```

| 测试文件 | 用例数 | 验证内容 |
|---|---|---|
| `tests/parsers/test_parsers.py` | 5 | excel/word/pdf/markdown + front-matter 剥离 |
| `tests/chunking/test_chunker.py` | 9 | 段落合并、overlap、硬切、min_chunk 过滤、参数校验 |
| `tests/test_task_store.py` | 4 | create/get/update/错误记录/idempotent schema |
| `tests/api/test_files_api.py` | 6 | multipart 上传 + task 状态 + 错误语义 |

API 端到端（TestClient）：
- `POST /v1/files/import` → 200 (md/xlsx/docx)，415 (未知)，400 (空)
- `GET  /v1/files/tasks/{id}` → 200 / 404

## 不在范围内（按协议 C2）

- embedding（C3 实现）。
- 入库到数据源（C3 实现）。
- OCR（占位 `ocr_required` 标志）。

## 已知缺口

- PDF 解析仅处理文本层；扫描件返回空文本 + `ocr_required=True`。后续可接 OCR 适配器。
- Word 解析不支持嵌入式图片/批注；如需可扩展 `python-docx` 之外的库。
- 任务表无过期清理；预计 C3 后做 archive job。