import os
import shutil
import uuid

import cv2
import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from core.agent.llm import CoachAgent
from core.memory.rag_engine import RAGEngine
from core.physics.engine import PhysicsEngine
from core.utils.fsm_segmenter import BadmintonFSM
from core.vision.court_detector import CourtDetector
from core.vision.pose import PoseAnalyzer
from core.vision.tracker import BallTracker

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
print("System Ready.")

TEMP_DIR = "temp_uploads"
os.makedirs(TEMP_DIR, exist_ok=True)


def normalize_tactics_payload(tactics):
    return [
        {
            **tactic,
            "name": tactic.get("name") or tactic.get("metadata", {}).get("name") or tactic.get("content", "Tactic"),
        }
        for tactic in tactics
    ]


@app.get("/")
async def root():
    return {"status": "running", "message": "EvoSmash Backend is ready!"}


@app.post("/analyze_rally")
async def analyze_rally(file: UploadFile = File(...), match_type: str = Form("singles")):
    filename = f"{uuid.uuid4()}.mp4"
    filepath = os.path.join(TEMP_DIR, filename)

    with open(filepath, "wb") as output_file:
        shutil.copyfileobj(file.file, output_file)

    try:
        cap = cv2.VideoCapture(filepath)
        ret, frame0 = cap.read()
        cap.release()
        if ret:
            corners = court_detector.detect(frame0)
            physics.update_homography(corners)

        trajectory, fps = tracker.infer(filepath)
        pose_sequence = pose_analyzer.infer(filepath)
        pose_feedback = pose_analyzer.evaluate_motion(pose_sequence)

        state = physics.analyze_trajectory(trajectory, fps, match_type=match_type)
        state["description"] += f" [Motion: {pose_feedback}]"

        auto_result = state.get("auto_result", "UNKNOWN")
        query_text = f"[{match_type}] {state['description']}"
        tactics = normalize_tactics_payload(rag.retrieve(query_text))
        advice_text = coach.generate_advice(state, tactics)

        tactic_id = None
        if tactics:
            metadata = tactics[0]["metadata"]
            tactic_id = metadata.get("tactic_id") or metadata.get("id")

        reward = 0.0
        if tactic_id and auto_result != "UNKNOWN":
            reward = physics.calculate_reward(auto_result)
            rag.update_policy(tactic_id, reward)
            print(f"[Auto-Evolution] Rally evolved. Result: {auto_result}, Reward: {reward}")

        return {
            "physics": state,
            "advice": {"text": advice_text},
            "tactics": tactics,
            "session_id": tactic_id,
            "match_type": match_type,
            "auto_result": auto_result,
            "auto_reward": reward,
        }
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.post("/analyze_match")
async def analyze_match(file: UploadFile = File(...), match_type: str = Form("singles")):
    filename = f"match_{uuid.uuid4()}.mp4"
    filepath = os.path.join(TEMP_DIR, filename)

    with open(filepath, "wb") as output_file:
        shutil.copyfileobj(file.file, output_file)

    try:
        print(f">>> Start Match Analysis: {filename}")

        cap = cv2.VideoCapture(filepath)
        ret, frame0 = cap.read()
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        if ret:
            corners = court_detector.detect(frame0)
            physics.update_homography(corners)

        full_trajectory, fps = tracker.infer(filepath)

        print(">>> Running FSM Segmentation...")
        fsm = BadmintonFSM(fps=fps, width=width, height=height)
        for frame_index, coordinate in enumerate(full_trajectory):
            fsm.update(frame_index, coordinate)

        rally_segments = fsm.get_segments()
        print(f">>> Found {len(rally_segments)} rallies.")

        results = []
        for rally_index, rally_trajectory in enumerate(rally_segments, start=1):
            state = physics.analyze_trajectory(rally_trajectory, fps, match_type)
            if state["max_speed_kmh"] < 30:
                continue

            auto_result = state.get("auto_result", "UNKNOWN")
            tactics = normalize_tactics_payload(rag.retrieve(state["description"]))
            advice_text = coach.generate_advice(state, tactics)

            reward = 0.0
            tactic_id = None
            if tactics:
                tactic_id = tactics[0]["metadata"].get("tactic_id")
                if tactic_id and auto_result != "UNKNOWN":
                    reward = physics.calculate_reward(auto_result)
                    rag.update_policy(tactic_id, reward)

            results.append({
                "rally_index": rally_index,
                "duration_sec": round(len(rally_trajectory) / fps, 2),
                "physics": state,
                "advice": {"text": advice_text},
                "tactics": tactics,
                "auto_result": auto_result,
                "auto_reward": reward,
            })

        return {
            "status": "success",
            "match_summary": {
                "total_rallies_found": len(rally_segments),
                "valid_rallies_analyzed": len(results),
            },
            "timeline": results,
        }
    except Exception as error:
        import traceback

        traceback.print_exc()
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
