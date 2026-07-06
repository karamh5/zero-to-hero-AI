from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class SensorReading(BaseModel):
    node_id: str
    temperature: float
    humidity: float


@app.get("/")
async def root():
    return {"status": "ok"}


@app.post("/sensor")
async def ingest_sensor(reading: SensorReading):
    alert = reading.temperature > 70
    return {
        "node_id": reading.node_id,
        "alert": alert,
        "message": "FIRE RISK" if alert else "Normal"
    }
