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
