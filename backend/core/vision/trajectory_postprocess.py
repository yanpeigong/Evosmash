from __future__ import annotations

from typing import Dict, Iterable, List, Sequence, Tuple

import numpy as np


class TrajectoryPostProcessor:
    def __init__(self, max_gap: int = 8, spike_threshold: float = 120.0, smooth_window: int = 5):
        self.max_gap = max_gap
        self.spike_threshold = spike_threshold
        self.smooth_window = smooth_window

    def postprocess(self, trajectory: Sequence[Tuple[int, int]]) -> Dict:
        points = np.array(trajectory, dtype=np.float32) if trajectory else np.empty((0, 2), dtype=np.float32)
        if len(points) == 0:
            return {
                "trajectory": [],
                "diagnostics": self._empty_diagnostics(),
            }

        valid_mask = (points[:, 0] > 0) & (points[:, 1] > 0)
        interpolated = self._interpolate_short_gaps(points, valid_mask)
        denoised, spike_count = self._suppress_spikes(interpolated)
        smoothed = self._smooth_valid_path(denoised)
        diagnostics = self._build_diagnostics(points, smoothed, spike_count)

        return {
            "trajectory": [(int(x), int(y)) for x, y in smoothed],
            "diagnostics": diagnostics,
        }

    def _interpolate_short_gaps(self, points: np.ndarray, valid_mask: np.ndarray) -> np.ndarray:
        result = points.copy()
        index = 0
        while index < len(points):
            if valid_mask[index]:
                index += 1
                continue

            gap_start = index
            while index < len(points) and not valid_mask[index]:
                index += 1
            gap_end = index - 1
            gap_len = gap_end - gap_start + 1

            left_idx = gap_start - 1
            right_idx = index if index < len(points) else None
            if gap_len > self.max_gap or left_idx < 0 or right_idx is None or not valid_mask[left_idx] or not valid_mask[right_idx]:
                continue

            left = points[left_idx]
            right = points[right_idx]
            for offset, fill_index in enumerate(range(gap_start, gap_end + 1), start=1):
                alpha = offset / (gap_len + 1)
                result[fill_index] = (1.0 - alpha) * left + alpha * right
        return result

    def _suppress_spikes(self, points: np.ndarray) -> Tuple[np.ndarray, int]:
        result = points.copy()
        spike_count = 0
        valid_mask = (points[:, 0] > 0) & (points[:, 1] > 0)
        valid_indices = np.where(valid_mask)[0]
        if len(valid_indices) < 3:
            return result, spike_count

        for center_pos in range(1, len(valid_indices) - 1):
            idx = valid_indices[center_pos]
            prev_idx = valid_indices[center_pos - 1]
            next_idx = valid_indices[center_pos + 1]
            prev_point = result[prev_idx]
            point = result[idx]
            next_point = result[next_idx]

            jump_in = np.linalg.norm(point - prev_point)
            jump_out = np.linalg.norm(next_point - point)
            baseline = np.linalg.norm(next_point - prev_point)
            if jump_in > self.spike_threshold and jump_out > self.spike_threshold and baseline < self.spike_threshold:
                result[idx] = 0.5 * (prev_point + next_point)
                spike_count += 1
        return result, spike_count

    def _smooth_valid_path(self, points: np.ndarray) -> np.ndarray:
        result = points.copy()
        valid_mask = (result[:, 0] > 0) & (result[:, 1] > 0)
        valid_indices = np.where(valid_mask)[0]
        if len(valid_indices) < 3:
            return result

        window = max(3, self.smooth_window)
        radius = window // 2
        for pos, idx in enumerate(valid_indices):
            left = max(0, pos - radius)
            right = min(len(valid_indices), pos + radius + 1)
            neighborhood = result[valid_indices[left:right]]
            result[idx] = neighborhood.mean(axis=0)
        return result

    def _build_diagnostics(self, raw_points: np.ndarray, final_points: np.ndarray, spike_count: int) -> Dict:
        raw_valid = (raw_points[:, 0] > 0) & (raw_points[:, 1] > 0)
        final_valid = (final_points[:, 0] > 0) & (final_points[:, 1] > 0)
        observed_count = int(raw_valid.sum())
        repaired_count = int(final_valid.sum() - observed_count)
        missing_ratio = float(1.0 - observed_count / max(len(raw_points), 1))

        step_lengths = []
        valid_points = final_points[final_valid]
        if len(valid_points) > 1:
            step_lengths = np.linalg.norm(np.diff(valid_points, axis=0), axis=1)
        smoothness_score = float(np.clip(1.0 - np.std(step_lengths) / 48.0, 0.0, 1.0)) if len(step_lengths) > 1 else 0.4
        continuity_score = float(np.clip(1.0 - missing_ratio + repaired_count / max(len(raw_points), 1), 0.0, 1.0))
        signal_integrity = float(np.clip(0.58 * continuity_score + 0.42 * smoothness_score, 0.0, 1.0))

        return {
            "observed_points": observed_count,
            "repaired_points": max(repaired_count, 0),
            "missing_ratio": round(missing_ratio, 3),
            "spike_count": spike_count,
            "smoothness_score": round(smoothness_score, 3),
            "continuity_score": round(continuity_score, 3),
            "signal_integrity": round(signal_integrity, 3),
        }

    def _empty_diagnostics(self) -> Dict:
        return {
            "observed_points": 0,
            "repaired_points": 0,
            "missing_ratio": 1.0,
            "spike_count": 0,
            "smoothness_score": 0.0,
            "continuity_score": 0.0,
            "signal_integrity": 0.0,
        }
