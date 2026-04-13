import os
import shutil
import uuid

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from core.agent.llm import CoachAgent
from core.memory.rag_engine import RAGEngine
from core.physics.engine import PhysicsEngine
from core.vision.court_detector import CourtDetector
from core.vision.pose import PoseAnalyzer
from core.vision.tracker import BallTracker
from schemas.analysis_response import MatchAnalysisResponse, RallyAnalysisResponse
from services import AnalysisService

app = FastAPI(title="EvoSmash Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

print("System Initializing...")
tracker = BallTracker()
court_detector = CourtDetector()
pose_analyzer = PoseAnalyzer()
physics = PhysicsEngine()
rag = RAGEngine()
coach = CoachAgent()
analysis_service = AnalysisService(
    tracker=tracker,
    court_detector=court_detector,
    pose_analyzer=pose_analyzer,
    physics=physics,
    rag=rag,
    coach=coach,
)
print("System Ready.")

TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)

ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}


def validate_match_type(match_type: str) -> str:
    if match_type not in {"singles", "doubles"}:
        raise HTTPException(status_code=400, detail="match_type must be 'singles' or 'doubles'.")
    return match_type


def validate_upload(file: UploadFile):
    suffix = os.path.splitext(file.filename or "")[1].lower()
    if suffix and suffix not in ALLOWED_VIDEO_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")


@app.get("/")
async def root():
    return {"status": "running", "message": "EvoSmash Backend is ready!"}


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "services": {
            "tracker": "ready",
            "court_detector": "ready",
            "pose_analyzer": "ready",
            "physics": "ready",
            "rag": "ready",
            "coach": "ready",
        },
    }


@app.post("/analyze_rally", response_model=RallyAnalysisResponse)
async def analyze_rally(file: UploadFile = File(...), match_type: str = Form("singles")):
    match_type = validate_match_type(match_type)
    validate_upload(file)

    filename = f"{uuid.uuid4()}.mp4"
    filepath = os.path.join(TEMP_DIR, filename)

    with open(filepath, "wb") as output_file:
        shutil.copyfileobj(file.file, output_file)

    try:
        return analysis_service.analyze_rally(filepath, match_type)
    except HTTPException:
        raise
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.post("/analyze_match", response_model=MatchAnalysisResponse)
async def analyze_match(file: UploadFile = File(...), match_type: str = Form("singles")):
    match_type = validate_match_type(match_type)
    validate_upload(file)

    filename = f"match_{uuid.uuid4()}.mp4"
    filepath = os.path.join(TEMP_DIR, filename)

    with open(filepath, "wb") as output_file:
        shutil.copyfileobj(file.file, output_file)

    try:
        return analysis_service.analyze_match(filepath, match_type)
    except Exception as error:
        raise HTTPException(status_code=500, detail=str(error))
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.post("/feedback")
async def feedback(tactic_id: str = Form(...), result: str = Form(...)):
    reward = physics.calculate_reward(result)
    rag.update_policy(tactic_id, reward)
    return {"status": "ok", "reward": reward}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
