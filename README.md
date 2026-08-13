# zero-to-hero-AI

This is where I build things with AI — real projects, end to end, each one a
step past the last. Some are small experiments, some turn into full systems
with actual hardware behind them. All of it lives here, organized by project,
as a running record of what I've built and how I got there.

Each project gets its own folder with its own README — go in for the details,
the architecture, the numbers. This top-level page is just the front door.

## Projects

- **[wildsense/](wildsense/)** — edge-AI wildfire risk detection on a
  Raspberry Pi. A sensor node that learns its own baseline instead of relying
  on a hardcoded threshold, with a simulated fleet showing how it'd federate
  across many nodes.

- **[EchoProof/](EchoProof/)** — a compliance assurance layer for voice AI
  agents. It proxies the agent's LLM call, pulls the governing rule out of a
  real policy corpus (Regulation F, 303 sections, straight from the eCFR API),
  and issues a verdict with the exact section cited, the rule text quoted, and
  an audio clip of the sentence — all in a hash-chained evidence log that
  renders to a single self-contained HTML report. Three findings in four cite
  the right paragraph. Detection sits at 35%, so the honest verdict is that it's
  a triage layer, not a release gate — and the report says so on its front page.

More projects will land here over time!

## Reference

- **[career/](career/)** — the delivery side of the same work, written down. A
  reference on how AI products go from a vague request to a monitored production
  system: the eleven stages and their gates, the stakeholders and what each of
  them blocks on, the architecture decisions, evaluation, governance, and the
  artifacts a delivery produces. Documentation, not code.

---
