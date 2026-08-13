# EchoProof UI

The frontend package. Architecture, design system, honesty rules and
verification live in [../UI.md](../UI.md).

```
npm install
npm run build     # emits dist/, served by scripts/run_ui.py
npm run dev       # Vite dev server, proxies /api to :8077
```

Vite + React + TypeScript, no CSS framework: the design tokens in
`src/styles/tokens.css` are the design system. Fonts are bundled; the app
makes no external network request.
