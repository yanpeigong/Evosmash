from __future__ import annotations

from typing import Dict, List, Sequence

import numpy as np


class MotionScorer:
    def score(self, pose_seq: Sequence[np.ndarray], knee_angles: np.ndarray, arm_angles: np.ndarray) -> Dict:
        valid_frames = int(np.sum(~np.isnan(knee_angles)))
        if valid_frames < 5:
            return self._empty_profile()

        knee_valid = knee_angles[~np.isnan(knee_angles)]
        arm_valid = arm_angles[~np.isnan(arm_angles)]

        base_depth_score = self._base_depth_score(knee_valid)
        extension_score = self._extension_score(arm_valid)
        balance_score = self._balance_score(knee_valid)
        readiness_score = float(np.clip(0.45 * base_depth_score + 0.35 * extension_score + 0.2 * balance_score, 0.0, 1.0))
        motion_load = float(np.clip(np.nanstd(knee_angles) / 24.0 + np.nanstd(arm_angles) / 30.0, 0.0, 1.0))

        coaching_tags = []
        if base_depth_score < 0.45:
            coaching_tags.append("lower-base-earlier")
        if extension_score < 0.45:
            coaching_tags.append("improve-contact-extension")
        if balance_score < 0.45:
            coaching_tags.append("stabilize-center-of-mass")
        if not coaching_tags:
            coaching_tags.append("maintain-current-structure")

        return {
            "valid_pose_frames": valid_frames,
            "base_depth_score": round(base_depth_score, 3),
            "extension_score": round(extension_score, 3),
            "balance_score": round(balance_score, 3),
            "readiness_score": round(readiness_score, 3),
            "motion_load": round(motion_load, 3),
            "coaching_tags": coaching_tags,
            "quality_label": self._quality_label(readiness_score),
        }

    def _base_depth_score(self, knee_valid: np.ndarray) -> float:
        min_knee = float(np.percentile(knee_valid, 10))
        if min_knee <= 100:
            return 0.92
        if min_knee <= 118:
            return 0.76
        if min_knee <= 132:
            return 0.58
        return 0.32

    def _extension_score(self, arm_valid: np.ndarray) -> float:
        max_arm = float(np.percentile(arm_valid, 90))
        if max_arm >= 158:
            return 0.9
        if max_arm >= 148:
            return 0.72
        if max_arm >= 136:
            return 0.54
        return 0.3

    def _balance_score(self, knee_valid: np.ndarray) -> float:
        volatility = float(np.std(knee_valid))
        return float(np.clip(1.0 - volatility / 32.0, 0.2, 0.92))

    def _quality_label(self, readiness_score: float) -> str:
        if readiness_score >= 0.78:
            return "strong"
        if readiness_score >= 0.56:
            return "stable"
        if readiness_score >= 0.38:
            return "developing"
        return "limited"

    def _empty_profile(self) -> Dict:
        return {
            "valid_pose_frames": 0,
            "base_depth_score": 0.0,
            "extension_score": 0.0,
            "balance_score": 0.0,
            "readiness_score": 0.0,
            "motion_load": 0.0,
            "coaching_tags": ["insufficient-pose-signal"],
            "quality_label": "unavailable",
        }
