import json
from pathlib import Path

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DATA_PATH = Path(__file__).with_name("q-vercel-latency.json")

with DATA_PATH.open() as f:
    TELEMETRY = json.load(f)


class AnalyticsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float


@app.post("/analytics")
def analytics(request: AnalyticsRequest):
    result = {}

    for region in request.regions:
        records = [
            record
            for record in TELEMETRY
            if record.get("region") == region
        ]

        if not records:
            result[region] = {
                "avg_latency": None,
                "p95_latency": None,
                "avg_uptime": None,
                "breaches": 0,
            }
            continue

        latencies = np.array(
            [record["latency_ms"] for record in records],
            dtype=float,
        )
        uptimes = np.array(
            [record["uptime"] for record in records],
            dtype=float,
        )

        result[region] = {
            "avg_latency": float(np.mean(latencies)),
            "p95_latency": float(np.percentile(latencies, 95)),
            "avg_uptime": float(np.mean(uptimes)),
            "breaches": int(np.sum(latencies > request.threshold_ms)),
        }

    return result
