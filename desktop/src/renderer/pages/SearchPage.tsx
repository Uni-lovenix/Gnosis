import React, { useState } from "react";
import type { Hit } from "../../shared/types";

interface Props {
  results: Hit[];
  onSearch: (q: string) => Promise<void>;
}

export function SearchPage({ results, onSearch }: Props): JSX.Element {
  const [q, setQ] = useState("");
  return (
    <section className="kb-page">
      <h2>Search</h2>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void onSearch(q);
        }}
      >
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ask your knowledge base..."
          autoFocus
        />
        <button type="submit">Search</button>
      </form>
      <ol className="kb-hits">
        {results.map((h) => (
          <li key={h.id}>
            <span className="kb-score">{h.score.toFixed(3)}</span>
            <p>{h.text.slice(0, 400)}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}