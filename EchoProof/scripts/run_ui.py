"""Start the EchoProof UI server.

The same FastAPI app as scripts/run_proxy.py, but credentials are optional:
stored runs, the corpus, the campaign and the readiness reading are fully
explorable with no key present. Live adjudication on the rig enables itself
only when MISTRAL_API_KEY exists, and reports its own disabled state when not.

Run:
    python scripts/run_ui.py                # http://127.0.0.1:8077
    python scripts/run_ui.py --port 8080

Dev mode for the frontend itself lives in ui/ (npm run dev), which proxies
/api to this server.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import uvicorn  # noqa: E402

from adapter.capture import CaptureQueue  # noqa: E402
from adapter.proxy import create_app  # noqa: E402
from core.config import load_settings  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the EchoProof UI server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8077)
    args = parser.parse_args()

    # require_model=False: the UI reads stored evidence, and failing to browse
    # a recorded run because a live-adjudication key is absent would be a bad
    # trade. The rig checks for the key itself and degrades to a labelled
    # disabled state.
    settings = load_settings(require_model=False)

    # No capture handler: this entry point serves the UI. Turns submitted to
    # the rig go through the job API, which owns its own adjudication stack.
    capture = CaptureQueue(handler=None)
    capture.start()

    app = create_app(settings, capture)
    if settings.mistral_api_key:
        print("model key present: live adjudication on the rig is enabled")
    else:
        print("no MISTRAL_API_KEY: stored runs only, rig shows its disabled state")
    print(f"UI at http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
