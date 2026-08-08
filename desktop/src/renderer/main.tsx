/**
 * Renderer entry. Mounts the App and exposes a global window.kb type.
 */
import React from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import type { KBAPI } from "../shared/types";
import "./styles.css";

declare global {
  interface Window {
    kb: KBAPI;
  }
}

const root = createRoot(document.getElementById("root")!);
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);