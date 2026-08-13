import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";

// Fonts are bundled locally; the UI makes no external network request.
import "@fontsource-variable/source-serif-4";
import "@fontsource/ibm-plex-mono/400.css";
import "@fontsource/ibm-plex-mono/500.css";
import "@fontsource-variable/archivo";
// Archivo's variable axis carries the heavy display weights the oversized
// type needs; loading the italic file too would be bytes for nothing.

import "./styles/tokens.css";
import "./styles/base.css";
import { App } from "./App";

// Reveal animations arm themselves only once this class is present, so a
// failed bundle or a disabled script leaves every screen fully readable
// rather than blank. Anyone who has asked for reduced motion never arms them.
if (!window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
  document.documentElement.classList.add("js-motion");
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
);
