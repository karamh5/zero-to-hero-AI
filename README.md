# zero-to-hero-AI

Hands-on labs from my journey learning modern AI engineering — every lab is runnable code, built in dependency order around one domain (wildfire/sensor monitoring). The concepts learned here converge in my flagship project: **[WildSense ↓](#wildsense)**

## Labs

| # | Lab | What I built and learned |
|---|---|---|
| 01 | [`backend`](labs/01-backend) | Dockerized FastAPI + PostgreSQL/pgvector, async endpoints, raw SQL (joins, window functions) |
| 02 | [`rag`](labs/02-rag) | RAG from scratch → hybrid search (BM25 + vector, RRF) → agentic self-grading retrieval, RAGAS evals |
| 03 | [`agents`](labs/03-agents) | Tool calling, from-scratch ReAct loop, LangGraph state machines, supervisor multi-agent system, working MCP server, crewAI |
| 04 | [`voice`](labs/04-voice) | Streaming STT → LLM → TTS pipeline (AssemblyAI, ElevenLabs), latency optimization |
| 05 | [`fine-tuning`](labs/05-fine-tuning) | LoRA fine-tune of TinyLlama-1.1B (HF PEFT/TRL), base-vs-tuned benchmarking on a GPU server |
| 06 | [`frontend`](labs/06-frontend) | React + TypeScript streaming chat (SSE), live WebSocket dashboard, Chrome extension w/ Cohere API |
| 07 | [`observability`](labs/07-observability) | LangSmith/LangFuse tracing, semantic caching, LLM routing, Guardrails |
| 08 | [`ml-foundations`](labs/08-ml-foundations) | Regression + regularization + Gaussian anomaly detection in NumPy, PyTorch NNs, attention from scratch, OpenCV |
| 09 | [`cloud`](labs/09-cloud) | AWS Lambda ingestion, Snowflake warehousing, Vertex AI + Ollama local inference, Databricks/K8s notes |

## Run any lab

```bash
cd labs/<lab>
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # add API keys
python src/<entry>.py  # each lab's README names the entry file
```

**Stack:** Python · LangChain/LangGraph · MCP · ChromaDB/pgvector · Hugging Face · Ollama · FastAPI · Docker · React/TS · AWS · Snowflake

---

## WildSense

**Multi-agent edge AI for wildfire detection.** Raspberry Pi nodes read environmental sensors, a LangGraph agent assesses fire risk grounded in a RAG pipeline over BC wildfire documents and live satellite data, and agents corroborate decisions with each other before raising an alert — with an on-device fine-tuned SLM so nodes work offline.

*Independent research project, supervised by UBC faculty.*

### Architecture

```
[Edge node × N]  Raspberry Pi + DHT22
   ├─ LangGraph agent: read → assess → corroborate → act
   ├─ on-device SLM (LoRA-tuned TinyLlama via Ollama)
   └─ MCP server exposing node tools
        │  agent-to-agent corroboration (n-of-m consensus before alert)
        ▼
[Context]  RAG over BC wildfire docs (hybrid search + reranking)
           + live APIs: NASA FIRMS · BC Wildfire Service · Open-Meteo
        ▼
[Cloud]    FastAPI → PostgreSQL/pgvector · AWS Lambda · Snowflake
        ▼
[UI]       React dashboard (live WebSocket feed) · voice alerts (streaming TTS)
```

### Why agents instead of federated learning

Edge nodes coordinate through structured agent-to-agent messages (corroborated risk assessment) rather than gradient sharing — richer semantics per exchange, auditable decision trails, and alignment with current agentic-AI practice. FL remains future work for model improvement across nodes.

### Repo layout

`wildsense/backend/` FastAPI + DB · `wildsense/agent/` LangGraph agent + MCP server · `wildsense/rag/` retrieval pipeline + evals · `wildsense/voice/` TTS alerts · `wildsense/frontend/` dashboard · `wildsense/hardware/` Pi + sensor setup · `wildsense/docs/` architecture + experiment results

### Run

```bash
docker compose up --build          # backend + db + dashboard
python wildsense/agent/run_node.py --node 1  # start an agent node (simulated sensors if no Pi)
```

### Status / Roadmap

- [x] Single-node agent loop + RAG grounding + dashboard
- [ ] Hybrid search + reranking with RAGAS before/after scores
- [ ] Multi-node corroboration experiment (single vs consensus: false-alarm & miss rates)
- [ ] On-Pi SLM deployment (quantized, via Ollama)
- [ ] Voice alert channel
