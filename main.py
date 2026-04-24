from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import uvicorn

from estimator import estimate_project

app = FastAPI(
    title="SRS Estimator API",
    description="Parses SRS documents to extract keywords and generate cost + timeline estimates.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")


class SRSInput(BaseModel):
    text: str
    hourly_rate: float = 500.0
    start_date: Optional[str] = None   # ISO format: YYYY-MM-DD


@app.post("/api/estimate")
def api_estimate(data: SRSInput):
    """
    Process SRS text → extract keywords → estimate cost & timeline.
    """
    if not data.text or len(data.text.strip()) < 10:
        raise HTTPException(status_code=400, detail="SRS text is too short.")

    result = estimate_project(
        text=data.text,
        hourly_rate=data.hourly_rate,
        start_date_str=data.start_date,
    )
    return result


@app.get("/", response_class=HTMLResponse)
def serve_index():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>Frontend not found. Make sure static/index.html exists.</h1>"


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
