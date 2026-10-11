
import json
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.responses import Response

app = FastAPI()

@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    if request.method == "OPTIONS":
        response = Response(status_code=200)
    else:
        response = await call_next(request)

    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "*"

    return response

DATA_FILE = Path(__file__).resolve().parent.parent / "q-vercel-latency.json"

with open(DATA_FILE, "r", encoding="utf-8") as file:
    records = json.load(file)


class AnalyticsRequest(BaseModel):
    regions: list[str]
    threshold_ms: float


def percentile_95(values):
    values = sorted(values)

    if len(values) == 1:
        return values[0]

    position = (len(values) - 1) * 0.95
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower

    return values[lower] + fraction * (
        values[upper] - values[lower]
    )


@app.post("/")
def analytics(request: AnalyticsRequest):
    results = {}

    for region in request.regions:
        region_records = [
            record for record in records
            if record["region"] == region
        ]

        if not region_records:
            results[region] = {
                "avg_latency": 0,
                "p95_latency": 0,
                "avg_uptime": 0,
                "breaches": 0,
            }
            continue

        latencies = [
            record["latency_ms"] for record in region_records
        ]

        uptimes = [
            record["uptime_pct"] for record in region_records
        ]

        results[region] = {
            "avg_latency": sum(latencies) / len(latencies),
            "p95_latency": percentile_95(latencies),
            "avg_uptime": sum(uptimes) / len(uptimes),
            "breaches": sum(
                latency > request.threshold_ms
                for latency in latencies
            ),
        }

    return results
