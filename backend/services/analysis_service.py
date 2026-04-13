from __future__ import annotations

from typing import Dict, List, Optional, Tuple

import cv2

from services.enrichment_service import (
    build_diagnostics_payload,
    build_summary_payload,
    enrich_tactics,
    make_empty_rally_response,
    normalize_advice_payload,
)


class AnalysisService:
    def __init__(self, tracker, court_detector, pose_analyzer, physics, rag, coach):
        self.tracker = tracker
        self.court_detector = court_detector
        self.pose_analyzer = pose_analyzer
        self.physics = physics
        self.rag = rag
        self.coach = coach

    def analyze_rally(self, filepath: str, match_type: str) -> Dict:
        warnings: List[str] = []
        pipeline_status = {
            "court_detection": "pending",
            "tracking": "pending",
            "pose": "pending",
            "physics": "pending",
            "retrieval": "pending",
            "coach": "pending",
        }

        self._prepare_court(filepath, warnings, pipeline_status)

        try:
            trajectory, fps = self.tracker.infer(filepath)
            pipeline_status["tracking"] = "ok"
        except Exception as error:
            pipeline_status["tracking"] = "failed"
            return make_empty_rally_response(match_type, f"Tracking failed: {error}")

        if not trajectory or len(trajectory) < 2:
            return make_empty_rally_response(match_type, "Tracking returned too few points to analyze the rally.")

        motion_feedback = self._get_pose_feedback(filepath, warnings, pipeline_status)

        try:
            state = self.physics.analyze_trajectory(trajectory, fps, match_type=match_type)
            pipeline_status["physics"] = "ok"
        except Exception as error:
            pipeline_status["physics"] = "failed"
            return make_empty_rally_response(match_type, f"Physics analysis failed: {error}")

        state["description"] += f" [Motion: {motion_feedback}]"
        auto_result = state.get("auto_result", "UNKNOWN")

        tactics = self._get_tactics(state, match_type, warnings, pipeline_status)
        advice = self._get_advice(state, tactics, warnings, pipeline_status)

        tactic_id = None
        policy_update = {}
        if tactics:
            metadata = tactics[0].get("metadata", {})
            tactic_id = metadata.get("tactic_id") or metadata.get("id")

        reward = 0.0
        if tactic_id and auto_result != "UNKNOWN":
            try:
                reward = self.physics.calculate_reward(auto_result)
                retrieval_confidence = self._retrieval_confidence(tactics)
                policy_update = self.rag.update_policy(
                    tactic_id,
                    reward,
                    context={
                        "referee_confidence": state.get("referee_confidence", 0.5),
                        "trajectory_quality": state.get("trajectory_quality", 0.5),
                        "retrieval_confidence": retrieval_confidence,
                    },
                ) or {}
            except Exception as error:
                warnings.append(f"Policy update skipped: {error}")

        summary = build_summary_payload(state, advice, tactics, auto_result)
        diagnostics = build_diagnostics_payload(
            warnings=warnings,
            pipeline_status=pipeline_status,
            motion_feedback=motion_feedback,
            trajectory_points=len(state.get("coordinates", [])),
            tactics=tactics,
        )
        diagnostics["policy_update"] = policy_update

        return {
            "physics": state,
            "advice": advice,
            "tactics": tactics,
            "session_id": tactic_id,
            "match_type": match_type,
            "auto_result": auto_result,
            "auto_reward": reward,
            "summary": summary,
            "diagnostics": diagnostics,
        }

    def analyze_match(self, filepath: str, match_type: str) -> Dict:
        warnings: List[str] = []
        self._prepare_court(filepath, warnings, {})

        try:
            full_trajectory, fps = self.tracker.infer(filepath)
        except Exception as error:
            return {
                "status": "failed",
                "match_summary": {
                    "total_rallies_found": 0,
                    "valid_rallies_analyzed": 0,
                },
                "timeline": [],
                "warnings": [f"Tracking failed: {error}"],
            }

        cap = cv2.VideoCapture(filepath)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()

        fsm = self._build_fsm(fps, width, height)
        for frame_index, coordinate in enumerate(full_trajectory):
            fsm.update(frame_index, coordinate)

        rally_segments = fsm.get_segments()
        timeline = []
        for rally_index, rally_trajectory in enumerate(rally_segments, start=1):
            if len(rally_trajectory) < 3:
                continue
            timeline_item = self._analyze_rally_segment(
                rally_index=rally_index,
                rally_trajectory=rally_trajectory,
                fps=fps,
                match_type=match_type,
            )
            if timeline_item:
                timeline.append(timeline_item)

        return {
            "status": "success",
            "match_summary": {
                "total_rallies_found": len(rally_segments),
                "valid_rallies_analyzed": len(timeline),
            },
            "timeline": timeline,
            "warnings": warnings,
        }

    def _prepare_court(self, filepath: str, warnings: List[str], pipeline_status: Dict[str, str]):
        try:
            cap = cv2.VideoCapture(filepath)
            ret, frame0 = cap.read()
            cap.release()
            if not ret or frame0 is None:
                warnings.append("Could not read the first frame for court detection.")
                if "court_detection" in pipeline_status:
                    pipeline_status["court_detection"] = "skipped"
                return

            corners = self.court_detector.detect(frame0)
            self.physics.update_homography(corners)
            if "court_detection" in pipeline_status:
                pipeline_status["court_detection"] = "ok"
        except Exception as error:
            warnings.append(f"Court detection fell back to default mapping: {error}")
            if "court_detection" in pipeline_status:
                pipeline_status["court_detection"] = "fallback"

    def _get_pose_feedback(self, filepath: str, warnings: List[str], pipeline_status: Dict[str, str]) -> str:
        try:
            pose_sequence = self.pose_analyzer.infer(filepath)
            motion_feedback = self.pose_analyzer.evaluate_motion(pose_sequence)
            pipeline_status["pose"] = "ok"
            return motion_feedback
        except Exception as error:
            warnings.append(f"Pose analysis unavailable: {error}")
            pipeline_status["pose"] = "fallback"
            return "Pose analysis unavailable."

    def _get_tactics(self, state: Dict, match_type: str, warnings: List[str], pipeline_status: Dict[str, str]) -> List[Dict]:
        try:
            query_text = f"[{match_type}] {state['description']}"
            retrieval_context = {
                "event": state.get("event"),
                "max_speed_kmh": state.get("max_speed_kmh", 0.0),
                "match_type": match_type,
                "court_context": state.get("court_context"),
                "auto_result": state.get("auto_result"),
                "trajectory_quality": state.get("trajectory_quality", 0.5),
                "referee_confidence": state.get("referee_confidence", 0.5),
            }
            tactics = self.rag.retrieve(query_text, context=retrieval_context)
            pipeline_status["retrieval"] = "ok" if tactics else "empty"
            return enrich_tactics(state, tactics)
        except Exception as error:
            warnings.append(f"Tactical retrieval unavailable: {error}")
            pipeline_status["retrieval"] = "fallback"
            return []

    def _get_advice(self, state: Dict, tactics: List[Dict], warnings: List[str], pipeline_status: Dict[str, str]) -> Dict:
        try:
            raw_advice = self.coach.generate_structured_advice(state, tactics)
            pipeline_status["coach"] = "ok"
        except Exception as error:
            warnings.append(f"Coach generation fell back to defaults: {error}")
            pipeline_status["coach"] = "fallback"
            raw_advice = None
        return normalize_advice_payload(raw_advice, tactics, state)

    def _build_fsm(self, fps: float, width: int, height: int):
        from core.utils.fsm_segmenter import BadmintonFSM

        return BadmintonFSM(fps=fps, width=width, height=height)

    def _analyze_rally_segment(self, rally_index: int, rally_trajectory: List[Tuple[int, int]], fps: float, match_type: str) -> Optional[Dict]:
        warnings: List[str] = []
        pipeline_status = {
            "tracking": "segment",
            "pose": "not_available",
            "physics": "pending",
            "retrieval": "pending",
            "coach": "pending",
        }

        try:
            state = self.physics.analyze_trajectory(rally_trajectory, fps, match_type)
            pipeline_status["physics"] = "ok"
        except Exception:
            return None

        if state["max_speed_kmh"] < 30:
            return None

        motion_feedback = "Pose analysis is only computed for short rally clips."
        state["description"] += f" [Motion: {motion_feedback}]"
        auto_result = state.get("auto_result", "UNKNOWN")
        tactics = self._get_tactics(state, match_type, warnings, pipeline_status)
        advice = self._get_advice(state, tactics, warnings, pipeline_status)

        reward = 0.0
        policy_update = {}
        if tactics:
            tactic_id = tactics[0].get("metadata", {}).get("tactic_id")
            if tactic_id and auto_result != "UNKNOWN":
                try:
                    reward = self.physics.calculate_reward(auto_result)
                    retrieval_confidence = self._retrieval_confidence(tactics)
                    policy_update = self.rag.update_policy(
                        tactic_id,
                        reward,
                        context={
                            "referee_confidence": state.get("referee_confidence", 0.5),
                            "trajectory_quality": state.get("trajectory_quality", 0.5),
                            "retrieval_confidence": retrieval_confidence,
                        },
                    ) or {}
                except Exception as error:
                    warnings.append(f"Policy update skipped: {error}")

        summary = build_summary_payload(state, advice, tactics, auto_result)
        diagnostics = build_diagnostics_payload(
            warnings=warnings,
            pipeline_status=pipeline_status,
            motion_feedback=motion_feedback,
            trajectory_points=len(state.get("coordinates", [])),
            tactics=tactics,
        )
        diagnostics["policy_update"] = policy_update

        return {
            "rally_index": rally_index,
            "duration_sec": round(len(rally_trajectory) / fps, 2),
            "physics": state,
            "advice": advice,
            "tactics": tactics,
            "auto_result": auto_result,
            "auto_reward": reward,
            "summary": summary,
            "diagnostics": diagnostics,
        }

    def _retrieval_confidence(self, tactics: List[Dict]) -> float:
        if not tactics:
            return 0.35
        top_score = float(tactics[0].get("score", 0.0))
        return max(0.35, min(top_score, 1.0))
