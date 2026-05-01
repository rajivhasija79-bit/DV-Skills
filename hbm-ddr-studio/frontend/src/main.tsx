import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import App from "./App";
import "./styles/globals.css";

// Auto-recover from stale Vite chunks (e.g. after dep re-optimization while
// the tab was idle). Without this, clicking a not-yet-loaded route can hang
// because the browser still references chunk hashes that no longer exist.
window.addEventListener("vite:preloadError", () => {
  // Hard reload picks up fresh chunk hashes from index.html.
  window.location.reload();
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>
);
