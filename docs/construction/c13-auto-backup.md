# C13 自动备份（迭代协议）

> 类别：C（构建迭代）。本迭代新增服务后台调度能力（启动时 + 周期自动快照），属于新增运行时行为，需独立评估报告。

## 迭代目标

把“手动/CLI 备份”升级为**服务运行期自动备份**：

1. 服务启动时若没有新快照则立即创建一份；之后按 `KB_BACKUP_INTERVAL_HOURS`（默认 24h）周期检查，到期才创建，避免频繁刷盘。
2. 自动备份复用 C10 的一致性快照与 C11 的保留策略（`KB_BACKUP_KEEP`）。
3. 日志可观测：`backup.auto_scheduled` / `backup.auto_created` / `backup.auto_skipped` / `backup.auto_failed`。

## 迭代范围

### 1. 设置

`server/app/config/settings.py` 新增：

| Env | 默认 | 语义 |
|---|---|---|
| `KB_BACKUP_AUTO` | `true` | 服务运行时是否自动备份 |
| `KB_BACKUP_INTERVAL_HOURS` | `24.0` | 自动备份最小间隔（小时） |

### 2. backup 模块

- `latest_backup(backup_root)`：返回最新快照摘要或 `None`。
- `backup_if_due(data_dir, backup_root, keep, interval_hours, now=time.time)`：
  - 无快照或最新快照 age ≥ interval → `backup_data_dir` 并返回 `(True, path)`；
  - 否则返回 `(False, latest_path)`。

### 3. 服务启动

`server/app/main.py`：

- `startup` 时若 `settings.backup_auto` 为真，创建后台任务：
  - 先 `backup_if_due(...)` 立即检查一次；
  - 然后循环 `sleep(3600)` 再检查，直到服务关闭。
- `shutdown` 时取消后台任务。
- 每次自动创建/跳过/失败打结构化日志。

### 4. 测试

`server/tests/conftest.py` 固定 `KB_BACKUP_AUTO=false`，避免测试启动调度任务。

`server/tests/test_backup.py` 新增：

- `latest_backup` 返回最新快照；
- `backup_if_due` 无快照 → 创建；
- `backup_if_due` 间隔未到 → 跳过；
- `backup_if_due` 间隔已到 → 创建新快照。

## 实施计划

1. 先落盘本协议。
2. 扩展 settings 与 backup 模块。
3. main.py 启动/关闭后台任务。
4. 补测试，跑全量 pytest / tsc / Vite build。
5. 更新文档与 harness + C13 评估。

## 交付物

- `server/app/config/settings.py`：`backup_auto` / `backup_interval_hours`。
- `server/app/observability/backup.py`：`latest_backup` / `backup_if_due`。
- `server/app/main.py`：自动备份后台任务。
- 测试：`server/tests/conftest.py` + `server/tests/test_backup.py`。
- 文档：`docs/RUNBOOK.md`、`docs/elaboration/01-architecture-baseline.md`、`feature_list.json`、`progress.md`、`session-handoff.md`、`evaluator-rubric.md`、`docs/construction/c13-auto-backup.md` + `c13-auto-backup-evaluation.md`。

## 退出标准

- [x] `backup_if_due` 对“无快照 / 未到期 / 已到期”三种情况行为正确。
- [x] 服务启动时自动创建/跳过、周期检查、关闭取消，均留有结构化日志。
- [x] `KB_BACKUP_AUTO=false` 时测试不启动后台任务。
- [x] `npm run check` / `lint` 0 errors；Vite build 通过并记录体积差值。
- [x] 全量 pytest 通过（记录实测数值）。
- [x] C13 评估报告由评估者角色出具。

## 决策记录

- **自动备份跟随服务运行**：个人知识库没有常驻桌面端时，仍可把 server 作为常驻服务跑；不引入系统级 cron/launchd 依赖。
- **启动即检查 + 每小时检查**：不固定整点，避免与服务重启重叠时重复创建；`backup_if_due` 按最新快照 age 决定。
- **默认开启**：高可用的默认应是“数据不靠人记”，用户可用 `KB_BACKUP_AUTO=false` 关闭。
