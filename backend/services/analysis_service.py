from __future__ import annotations

from collections import Counter
from typing import Dict, List, Optional, Tuple

import cv2

from core.memory.sequence_memory import SequenceMemory
from core.memory.tactic_catalog import TACTIC_SEEDS
from core.memory.tactic_duel_simulator import TacticDuelSimulator
from core.physics.referee_audit import RefereeAuditTrail
from core.physics.uncertainty import ConfidenceCalibrator
from core.utils.match_intelligence import MatchIntelligenceAnalyzer
from core.utils.rally_quality import RallyQualityAnalyzer
from core.utils.report_builder import ReportBuilder
from core.utils.replay_storyline import ReplayStorylineBuilder
from core.utils.training_prescriptor import TrainingPrescriptor
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
        self.rally_quality = RallyQualityAnalyzer()
        self.match_intelligence = MatchIntelligenceAnalyzer()
        self.confidence_calibrator = ConfidenceCalibrator()
        self.referee_audit = RefereeAuditTrail()
        self.sequence_memory = SequenceMemory()
        self.duel_simulator = TacticDuelSimulator(TACTIC_SEEDS)
        self.report_builder = ReportBuilder()
        self.replay_storyline = ReplayStorylineBuilder()
        self.training_prescriptor = TrainingPrescriptor()

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
        sequence_context = self.sequence_memory.build_context([], match_type=match_type)

        self._prepare_court(filepath, warnings, pipeline_status)

        tracker_diagnostics = {}
        try:
            if hasattr(self.tracker, "infer_detailed"):
                trajectory, fps, tracker_diagnostics = self.tracker.infer_detailed(filepath)
            else:
                trajectory, fps = self.tracker.infer(filepath)
                tracker_diagnostics = getattr(self.tracker, "last_diagnostics", {}) or {}
            pipeline_status["tracking"] = "ok"
        except Exception as error:
            pipeline_status["tracking"] = "failed"
            return make_empty_rally_response(match_type, f"Tracking failed: {error}")

        if not trajectory or len(trajectory) < 2:
            return make_empty_rally_response(match_type, "Tracking returned too few points to analyze the rally.")

        motion_feedback, motion_profile = self._get_pose_feedback(filepath, warnings, pipeline_status)

        try:
            state = self.physics.analyze_trajectory(trajectory, fps, match_type=match_type)
            pipeline_status["physics"] = "ok"
        except Exception as error:
            pipeline_status["physics"] = "failed"
            return make_empty_rally_response(match_type, f"Physics analysis failed: {error}")

        state["description"] += f" [Motion: {motion_feedback}]"
        auto_result = state.get("auto_result", "UNKNOWN")
        rally_quality = self.rally_quality.evaluate(state, tracker_diagnostics=tracker_diagnostics, motion_profile=motion_profile)
        confidence_report = self.confidence_calibrator.calibrate(state, tracker_diagnostics=tracker_diagnostics, motion_profile=motion_profile, rally_quality=rally_quality)
        referee_audit = self.referee_audit.audit(state, tracker_diagnostics=tracker_diagnostics, motion_profile=motion_profile, rally_quality=rally_quality, confidence_report=confidence_report)
        state["calibrated_confidence"] = confidence_report.get("calibrated_confidence", state.get("referee_confidence", 0.5))
        state["verdict_stability"] = referee_audit.get("verdict_stability", 0.5)

        tactics = self._get_tactics(state, match_type, rally_quality, sequence_context, warnings, pipeline_status)
        duel_projection = self.duel_simulator.simulate(tactics, state, sequence_context=sequence_context)
        advice = self._get_advice(state, tactics, warnings, pipeline_status)

        tactic_id = None
        policy_update = {}
        if tactics:
            metadata = tactics[0].get("metadata", {})
            tactic_id = metadata.get("tactic_id") or metadata.get("id")

        reward = 0.0
        if tactic_id and auto_result != "UNKNOWN":
            try:
                reward = self.physics.calculate_reward(auto_result, trajectory_quality=state.get("trajectory_quality", 0.5), referee_confidence=state.get("referee_confidence", 0.5), pressure_index=state.get("pressure_index", 0.5))
                retrieval_confidence = self._retrieval_confidence(tactics)
                top_tactic = tactics[0] if tactics else {}
                policy_update = self.rag.update_policy(
                    tactic_id,
                    reward,
                    context={
                        "event": state.get("event"),
                        "match_type": match_type,
                        "court_context": state.get("court_context"),
                        "referee_confidence": state.get("referee_confidence", 0.5),
                        "trajectory_quality": state.get("trajectory_quality", 0.5),
                        "retrieval_confidence": retrieval_confidence,
                        "context_score": top_tactic.get("context_score", 0.5),
                        "attack_phase": state.get("attack_phase"),
                        "tempo_profile": state.get("tempo_profile"),
                        "last_hitter": state.get("last_hitter"),
                        "pressure_index": state.get("pressure_index", 0.5),
                        "rally_quality": rally_quality.get("overall_quality", 0.5),
                        "auto_result": auto_result,
                        **sequence_context.get("retrieval_context", {}),
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
            state=state,
            tracker_diagnostics=tracker_diagnostics,
            motion_profile=motion_profile,
            rally_quality=rally_quality,
            confidence_report=confidence_report,
            referee_audit=referee_audit,
            sequence_context=sequence_context,
            duel_projection=duel_projection,
        )
        diagnostics["policy_update"] = policy_update
        training_plan = self.training_prescriptor.build_rally_plan(state, tactics, diagnostics)
        rally_report = self.report_builder.build_rally_report(state, summary, diagnostics, tactics, training_plan=training_plan)

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
            "report": rally_report,
        }

    def analyze_match(self, filepath: str, match_type: str) -> Dict:
        warnings: List[str] = []
        self._prepare_court(filepath, warnings, {})

        try:
            full_trajectory, fps = self.tracker.infer(filepath)
        except Exception as error:
            return {
                "status": "failed",
                "match_summary": {"total_rallies_found": 0, "valid_rallies_analyzed": 0, "intelligence": {}, "report": {}},
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
        segment_summaries = fsm.get_segment_summaries() if hasattr(fsm, "get_segment_summaries") else []
        timeline = []
        for rally_index, rally_trajectory in enumerate(rally_segments, start=1):
            if len(rally_trajectory) < 3:
                continue
            sequence_context = self.sequence_memory.build_context(timeline, match_type=match_type)
            segment_summary = segment_summaries[rally_index - 1] if rally_index - 1 < len(segment_summaries) else {}
            timeline_item = self._analyze_rally_segment(
                rally_index=rally_index,
                rally_trajectory=rally_trajectory,
                fps=fps,
                match_type=match_type,
                tracker_diagnostics=segment_summary,
                sequence_context=sequence_context,
            )
            if timeline_item:
                timeline.append(timeline_item)

        if not timeline:
            warnings.append("No valid rally segments were strong enough for full tactical analysis.")

        sequence_context = self.sequence_memory.build_context(timeline, match_type=match_type)
        duel_summary = self.duel_simulator.summarize_matchup(timeline, sequence_context=sequence_context)
        intelligence = self.match_intelligence.summarize(timeline, match_type, sequence_context=sequence_context, duel_summary=duel_summary)
        replay_story = self.replay_storyline.build(timeline, intelligence, sequence_context=sequence_context, duel_summary=duel_summary)
        match_training_plan = self.training_prescriptor.build_match_plan(intelligence, timeline)
        match_metrics = self._build_match_metrics(timeline)
        match_report = self.report_builder.build_match_report(
            intelligence,
            timeline,
            training_plan=match_training_plan,
            sequence_context=sequence_context,
            duel_summary=duel_summary,
            replay_story=replay_story,
        )
        return {
            "status": "success",
            "match_summary": {
                "total_rallies_found": len(rally_segments),
                "valid_rallies_analyzed": len(timeline),
                "metrics": match_metrics,
                "intelligence": intelligence,
                "sequence_memory": sequence_context,
                "duel_summary": duel_summary,
                "replay_story": replay_story,
                "report": match_report,
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

    def _get_pose_feedback(self, filepath: str, warnings: List[str], pipeline_status: Dict[str, str]):
        try:
            pose_sequence = self.pose_analyzer.infer(filepath)
            if hasattr(self.pose_analyzer, "evaluate_motion_profile"):
                motion_profile = self.pose_analyzer.evaluate_motion_profile(pose_sequence)
                motion_feedback = motion_profile.get("feedback_text", "Pose analysis unavailable.")
            else:
                motion_feedback = self.pose_analyzer.evaluate_motion(pose_sequence)
                motion_profile = {}
            pipeline_status["pose"] = "ok"
            return motion_feedback, motion_profile
        except Exception as error:
            warnings.append(f"Pose analysis unavailable: {error}")
            pipeline_status["pose"] = "fallback"
            return "Pose analysis unavailable.", {}

    def _get_tactics(self, state: Dict, match_type: str, rally_quality: Dict, sequence_context: Dict, warnings: List[str], pipeline_status: Dict[str, str]) -> List[Dict]:
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
                "attack_phase": state.get("attack_phase", "neutral"),
                "tempo_profile": state.get("tempo_profile", "medium"),
                "last_hitter": state.get("last_hitter", "UNKNOWN"),
                "pressure_index": state.get("pressure_index", 0.5),
                "rally_quality": rally_quality.get("overall_quality", 0.5),
                **sequence_context.get("retrieval_context", {}),
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

    def _analyze_rally_segment(self, rally_index: int, rally_trajectory: List[Tuple[int, int]], fps: float, match_type: str, tracker_diagnostics: Dict | None = None, sequence_context: Dict | None = None) -> Optional[Dict]:
        warnings: List[str] = []
        pipeline_status = {"tracking": "segment", "pose": "not_available", "physics": "pending", "retrieval": "pending", "coach": "pending"}
        tracker_diagnostics = tracker_diagnostics or {}
        sequence_context = sequence_context or self.sequence_memory.build_context([], match_type=match_type)

        try:
            state = self.physics.analyze_trajectory(rally_trajectory, fps, match_type)
            pipeline_status["physics"] = "ok"
        except Exception:
            return None

        if state["max_speed_kmh"] < 30:
            return None

        motion_feedback = "Pose analysis is only computed for short rally clips."
        motion_profile = {"quality_label": "segment-only", "readiness_score": 0.45}
        state["description"] += f" [Motion: {motion_feedback}]"
        auto_result = state.get("auto_result", "UNKNOWN")
        rally_quality = self.rally_quality.evaluate(state, tracker_diagnostics=tracker_diagnostics, motion_profile=motion_profile)
        confidence_report = self.confidence_calibrator.calibrate(state, tracker_diagnostics=tracker_diagnostics, motion_profile=motion_profile, rally_quality=rally_quality)
        referee_audit = self.referee_audit.audit(state, tracker_diagnostics=tracker_diagnostics, motion_profile=motion_profile, rally_quality=rally_quality, confidence_report=confidence_report)
        state["calibrated_confidence"] = confidence_report.get("calibrated_confidence", state.get("referee_confidence", 0.5))
        state["verdict_stability"] = referee_audit.get("verdict_stability", 0.5)
        tactics = self._get_tactics(state, match_type, rally_quality, sequence_context, warnings, pipeline_status)
        duel_projection = self.duel_simulator.simulate(tactics, state, sequence_context=sequence_context)
        advice = self._get_advice(state, tactics, warnings, pipeline_status)

        reward = 0.0
        policy_update = {}
        if tactics:
            tactic_id = tactics[0].get("metadata", {}).get("tactic_id")
            if tactic_id and auto_result != "UNKNOWN":
                try:
                    reward = self.physics.calculate_reward(auto_result, trajectory_quality=state.get("trajectory_quality", 0.5), referee_confidence=state.get("referee_confidence", 0.5), pressure_index=state.get("pressure_index", 0.5))
                    retrieval_confidence = self._retrieval_confidence(tactics)
                    top_tactic = tactics[0]
                    policy_update = self.rag.update_policy(
                        tactic_id,
                        reward,
                        context={
                            "event": state.get("event"),
                            "match_type": match_type,
                            "court_context": state.get("court_context"),
                            "referee_confidence": state.get("referee_confidence", 0.5),
                            "trajectory_quality": state.get("trajectory_quality", 0.5),
                            "retrieval_confidence": retrieval_confidence,
                            "context_score": top_tactic.get("context_score", 0.5),
                            "attack_phase": state.get("attack_phase"),
                            "tempo_profile": state.get("tempo_profile"),
                            "last_hitter": state.get("last_hitter"),
                            "pressure_index": state.get("pressure_index", 0.5),
                            "rally_quality": rally_quality.get("overall_quality", 0.5),
                            "auto_result": auto_result,
                            **sequence_context.get("retrieval_context", {}),
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
            state=state,
            tracker_diagnostics=tracker_diagnostics,
            motion_profile=motion_profile,
            rally_quality=rally_quality,
            confidence_report=confidence_report,
            referee_audit=referee_audit,
            sequence_context=sequence_context,
            duel_projection=duel_projection,
        )
        diagnostics["policy_update"] = policy_update
        training_plan = self.training_prescriptor.build_rally_plan(state, tactics, diagnostics)
        rally_report = self.report_builder.build_rally_report(state, summary, diagnostics, tactics, training_plan=training_plan)

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
            "report": rally_report,
        }

    def _retrieval_confidence(self, tactics: List[Dict]) -> float:
        if not tactics:
            return 0.35
        top_score = float(tactics[0].get("score", 0.0))
        rerank_score = float(tactics[0].get("rerank_score", top_score) or top_score)
        context_score = float(tactics[0].get("context_score", 0.0))
        scenario_bias = float(tactics[0].get("scenario_bias", 0.0))
        graph_bias = float(tactics[0].get("graph_bias", 0.0))
        continuity_score = float(tactics[0].get("continuity_score", 0.5) or 0.5)
        coverage_score = float(tactics[0].get("coverage_score", 0.5) or 0.5)
        scheduler_profile = tactics[0].get("scheduler_profile", {}) or {}
        exploitation = float(scheduler_profile.get("exploitation_weight", 0.5) or 0.5)
        return max(0.35, min(0.2 * top_score + 0.18 * rerank_score + 0.14 * context_score + 0.12 * continuity_score + 0.1 * coverage_score + 0.06 * min(scenario_bias * 10, 1.0) + 0.06 * min(graph_bias * 10, 1.0) + 0.14 * exploitation, 1.0))

    def _build_match_metrics(self, timeline: List[Dict]) -> Dict:
        if not timeline:
            return {
                "result_distribution": {},
                "average_rally_duration_sec": 0.0,
                "average_max_speed_kmh": 0.0,
                "peak_speed_kmh": 0.0,
                "average_pressure_index": 0.0,
                "average_confidence": 0.0,
                "top_focuses": [],
                "top_tactics": [],
                "analysis_quality_distribution": {},
            }

        result_distribution = Counter(item.get("auto_result", "UNKNOWN") for item in timeline)
        analysis_quality_distribution = Counter(
            ((item.get("diagnostics", {}) or {}).get("analysis_quality", "unknown"))
            for item in timeline
        )
        focus_distribution = Counter(
            ((item.get("advice", {}) or {}).get("focus", "Recovery"))
            for item in timeline
        )
        tactic_distribution = Counter(
            (((item.get("tactics", []) or [{}])[0]).get("name", "Neutral reset"))
            for item in timeline
        )

        durations = [float(item.get("duration_sec", 0.0) or 0.0) for item in timeline]
        speeds = [float((item.get("physics", {}) or {}).get("max_speed_kmh", 0.0) or 0.0) for item in timeline]
        pressures = [float((item.get("physics", {}) or {}).get("pressure_index", 0.0) or 0.0) for item in timeline]
        confidences = [
            float((((item.get("diagnostics", {}) or {}).get("confidence_report", {}) or {}).get("calibrated_confidence", 0.0) or 0.0))
            for item in timeline
        ]

        def _average(values: List[float]) -> float:
            return round(sum(values) / len(values), 3) if values else 0.0

        return {
            "result_distribution": dict(result_distribution),
            "average_rally_duration_sec": _average(durations),
            "average_max_speed_kmh": _average(speeds),
            "peak_speed_kmh": round(max(speeds), 3) if speeds else 0.0,
            "average_pressure_index": _average(pressures),
            "average_confidence": _average(confidences),
            "top_focuses": [{"focus": focus, "count": count} for focus, count in focus_distribution.most_common(3)],
            "top_tactics": [{"name": name, "count": count} for name, count in tactic_distribution.most_common(3)],
            "analysis_quality_distribution": dict(analysis_quality_distribution),
        }
