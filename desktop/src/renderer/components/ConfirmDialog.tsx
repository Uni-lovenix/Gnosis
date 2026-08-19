import React, { useEffect, useState } from "react";

interface Props {
  title: string;
  body: React.ReactNode;
  confirmLabel: string;
  matchText: string;
  busy?: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  title,
  body,
  confirmLabel,
  matchText,
  busy = false,
  onConfirm,
  onCancel,
}: Props): JSX.Element {
  const [input, setInput] = useState("");

  useEffect(() => {
    setInput("");
  }, [matchText]);

  return (
    <div
      className="kb-modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget && !busy) onCancel();
      }}
    >
      <div className="kb-modal" role="dialog" aria-modal="true" aria-labelledby="kb-confirm-title">
        <h3 id="kb-confirm-title">{title}</h3>
        <div className="kb-modal-body">{body}</div>
        <label className="kb-confirm-input">
          请输入 <code>{matchText}</code> 确认
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            autoFocus
            spellCheck={false}
            disabled={busy}
          />
        </label>
        <div className="kb-modal-actions">
          <button onClick={onCancel} disabled={busy}>取消</button>
          <button
            className="kb-button-danger"
            onClick={onConfirm}
            disabled={input !== matchText || busy}
          >
            {busy ? "处理中…" : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
