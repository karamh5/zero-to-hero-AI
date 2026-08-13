"""Read-only HTTP layer for the EchoProof UI.

Everything in this package reads artifacts the engine already wrote: evidence
logs, campaign summaries, packs, criteria and measurement files. Nothing here
re-judges, re-retrieves or recomputes a verdict, and nothing here writes to an
existing run. The one write path is live adjudication, which appends a NEW run
directory through the engine's own public pipeline, exactly as the proxy does.

The engine/pack boundary holds: this package contains no industry constant and
reads severity labels, gate thresholds and section identifier conventions from
the packs, never from code.
"""
