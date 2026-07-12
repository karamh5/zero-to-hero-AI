# zero-to-hero-AI

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

### Repo layout

`wildsense/backend/` FastAPI + DB · `wildsense/agent/` LangGraph agent + MCP server · `wildsense/rag/` retrieval pipeline + evals · `wildsense/voice/` TTS alerts · `wildsense/frontend/` dashboard · `wildsense/hardware/` Pi + sensor setup · `wildsense/docs/` architecture + experiment results

### Run

```bash
docker compose up --build          # backend + db + dashboard
python wildsense/agent/run_node.py --node 1  # start an agent node (simulated sensors if no Pi)
```

### Status / Roadmap

- [ ] Single-node agent loop + RAG grounding + dashboard
- [ ] Hybrid search + reranking with RAGAS before/after scores
- [ ] Multi-node corroboration experiment (single vs consensus: false-alarm & miss rates)
- [ ] On-Pi SLM deployment (quantized, via Ollama)
- [ ] Voice alert channel
