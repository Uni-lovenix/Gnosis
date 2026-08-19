/**
 * Renderer-side error copy. Keeps raw IPC/HTTP failures out of primary UI
 * text and pairs every known failure mode with a next step.
 */

export interface HumanError {
  title: string;
  hint: string;
  raw: string;
}

function errorText(err: unknown): string {
  if (err instanceof Error) return err.message;
  if (typeof err === "string") return err;
  return String(err);
}

export function describeError(err: unknown, fallbackTitle = "操作失败"): HumanError {
  const raw = errorText(err);
  const lower = raw.toLowerCase();

  if (
    lower.includes("fetch failed") ||
    lower.includes("failed to fetch") ||
    lower.includes("econnrefused") ||
    lower.includes("network error") ||
    lower.includes("socket hang up") ||
    lower.includes("server unreachable") ||
    lower.includes("not ready")
  ) {
    return {
      title: "服务连接失败",
      hint: "请检查 Python 后端是否已启动（默认 8765 端口），或参考 RUNBOOK 的启动与排错章节。",
      raw,
    };
  }

  if (
    lower.includes("unsupported file type") ||
    lower.includes("415") ||
    lower.includes("empty file")
  ) {
    return {
      title: "文件无法导入",
      hint: "请导入 Excel、Word、PDF、Markdown 或纯文本文件；空文件也会被拒绝。",
      raw,
    };
  }

  if (lower.includes("unknown datasource type")) {
    return {
      title: "未知的数据源类型",
      hint: "请在类型列表中选择受支持的数据源，或查看 RUNBOOK 中的配置示例。",
      raw,
    };
  }

  if (
    lower.includes("options json is invalid") ||
    lower.includes("json parse") ||
    lower.includes("unexpected token")
  ) {
    return {
      title: "配置 JSON 无效",
      hint: "请检查括号与引号是否完整，或切换到表单模式编辑。",
      raw,
    };
  }

  if (
    lower.includes("chunk_list") ||
    lower.includes("501") ||
    lower.includes("not supported") ||
    lower.includes("notimplemented")
  ) {
    return {
      title: "当前数据源不支持此能力",
      hint: "建议切换到支持该能力的 Elasticsearch 数据源，或参考 RUNBOOK §3 的迁移路径。",
      raw,
    };
  }

  if (
    lower.includes("invalid config") ||
    lower.includes("health check failed") ||
    lower.includes("connection refused") ||
    lower.includes("timed out") ||
    lower.includes("could not connect") ||
    lower.includes("authentication")
  ) {
    return {
      title: "数据源连接失败",
      hint: "请检查地址、端口、凭证和数据源依赖是否就绪后重试。",
      raw,
    };
  }

  if (
    lower.includes("not configured") ||
    lower.includes("no active datasource") ||
    lower.includes("pipeline not configured")
  ) {
    return {
      title: "功能尚未配置",
      hint: "请先在设置中添加并激活数据源，同时确认 Embedding 服务可用。",
      raw,
    };
  }

  if (
    lower.includes("embedder") ||
    lower.includes("ollama") ||
    lower.includes("429") ||
    lower.includes("502") ||
    lower.includes("503") ||
    lower.includes("504")
  ) {
    return {
      title: "Embedding 服务暂不可用",
      hint: "请检查 Ollama 或远端 Embedding 服务是否运行，然后稍后重试。",
      raw,
    };
  }

  if (lower.includes("backup") || lower.includes("restore")) {
    return {
      title: "备份操作失败",
      hint: "请检查磁盘空间、目录权限与数据目录状态后重试。",
      raw,
    };
  }

  return {
    title: fallbackTitle,
    hint: "请稍后重试；若问题持续，可查看服务日志定位原因。",
    raw,
  };
}

export function formatError(err: unknown, fallbackTitle = "操作失败"): string {
  const e = describeError(err, fallbackTitle);
  return `${e.title}：${e.hint}`;
}
