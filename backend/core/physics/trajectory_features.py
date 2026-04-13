from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Dict

import numpy as np

from config import COURT_LENGTH, COURT_WIDTH_DOUBLES


@dataclass
class TrajectoryFeatureBundle:
    visibility_ratio: float
    sample_count: int
    path_length_m: float
    mean_step_m: float
    mean_speed_kmh: float
    max_speed_kmh: float
    end_speed_kmh: float
    speed_volatility: float
    acceleration_load: float
    route_directness: float
    lateral_span_ratio: float
    depth_span_ratio: float
    terminal_settle: float
    pressure_index: float
    attack_phase: str
    tempo_profile: str
    shot_shape: str

    def to_dict(self) -> Dict:
        return asdict(self)


class TrajectoryFeatureExtractor:
    def extract(self, world_coords, valid_coords, fps: float) -> Dict:
        if len(world_coords) == 0 or len(valid_coords) == 0:
            return TrajectoryFeatureBundle(
                visibility_ratio=0.0,
                sample_count=0,
                path_length_m=0.0,
                mean_step_m=0.0,
                mean_speed_kmh=0.0,
                max_speed_kmh=0.0,
                end_speed_kmh=0.0,
                speed_volatility=0.0,
                acceleration_load=0.0,
                route_directness=0.0,
                lateral_span_ratio=0.0,
                depth_span_ratio=0.0,
                terminal_settle=0.0,
                pressure_index=0.0,
                attack_phase="neutral",
                tempo_profile="medium",
                shot_shape="unclear",
            ).to_dict()

        valid_coords = np.array(valid_coords, dtype=np.float32)
        world_coords = np.array(world_coords, dtype=np.float32)
        dt = 1.0 / max(float(fps or 1.0), 1.0)
        deltas = np.diff(valid_coords, axis=0) if len(valid_coords) > 1 else np.empty((0, 2), dtype=np.float32)
        step_lengths = np.linalg.norm(deltas, axis=1) if len(deltas) > 0 else np.array([], dtype=np.float32)
        speeds = step_lengths / dt if len(step_lengths) > 0 else np.array([], dtype=np.float32)
        accelerations = np.diff(speeds) / dt if len(speeds) > 1 else np.array([], dtype=np.float32)

        path_length = float(np.sum(step_lengths)) if len(step_lengths) else 0.0
        displacement = float(np.linalg.norm(valid_coords[-1] - valid_coords[0])) if len(valid_coords) > 1 else 0.0
        route_directness = float(np.clip(displacement / max(path_length, 1e-6), 0.0, 1.0)) if path_length > 0 else 0.0

        x_values = valid_coords[:, 0]
        y_values = valid_coords[:, 1]
        lateral_span_ratio = float(np.clip((np.max(x_values) - np.min(x_values)) / max(COURT_WIDTH_DOUBLES, 1e-6), 0.0, 1.0))
        depth_span_ratio = float(np.clip((np.max(y_values) - np.min(y_values)) / max(COURT_LENGTH, 1e-6), 0.0, 1.0))

        visibility_ratio = float(np.clip(len(valid_coords) / max(len(world_coords), 1), 0.0, 1.0))
        mean_step = float(np.mean(step_lengths)) if len(step_lengths) else 0.0
        mean_speed_kmh = float(np.mean(speeds) * 3.6) if len(speeds) else 0.0
        max_speed_kmh = float(np.max(speeds) * 3.6) if len(speeds) else 0.0
        end_speed_kmh = float(np.mean(speeds[-3:]) * 3.6) if len(speeds) else 0.0
        speed_volatility = float(np.std(speeds) * 3.6) if len(speeds) else 0.0
        acceleration_load = float(np.mean(np.abs(accelerations))) if len(accelerations) else 0.0

        if len(step_lengths) >= 3:
            tail_motion = float(np.mean(step_lengths[-3:]))
            head_motion = float(np.mean(step_lengths[:3]))
            terminal_settle = float(np.clip(1.0 - tail_motion / max(head_motion, 1e-6), 0.0, 1.0))
        else:
            terminal_settle = 0.35

        pressure_index = float(np.clip(
            0.3 * depth_span_ratio + 0.22 * lateral_span_ratio + 0.22 * min(max_speed_kmh / 220.0, 1.0) + 0.16 * min(speed_volatility / 55.0, 1.0) + 0.1 * (1.0 - terminal_settle),
            0.0,
            1.0,
        ))

        attack_phase = self._infer_attack_phase(pressure_index, terminal_settle, route_directness)
        tempo_profile = self._infer_tempo_profile(mean_speed_kmh, max_speed_kmh, speed_volatility)
        shot_shape = self._infer_shot_shape(depth_span_ratio, lateral_span_ratio, route_directness, terminal_settle)

        return TrajectoryFeatureBundle(
            visibility_ratio=round(visibility_ratio, 3),
            sample_count=int(len(valid_coords)),
            path_length_m=round(path_length, 3),
            mean_step_m=round(mean_step, 3),
            mean_speed_kmh=round(mean_speed_kmh, 3),
            max_speed_kmh=round(max_speed_kmh, 3),
            end_speed_kmh=round(end_speed_kmh, 3),
            speed_volatility=round(speed_volatility, 3),
            acceleration_load=round(acceleration_load, 3),
            route_directness=round(route_directness, 3),
            lateral_span_ratio=round(lateral_span_ratio, 3),
            depth_span_ratio=round(depth_span_ratio, 3),
            terminal_settle=round(terminal_settle, 3),
            pressure_index=round(pressure_index, 3),
            attack_phase=attack_phase,
            tempo_profile=tempo_profile,
            shot_shape=shot_shape,
        ).to_dict()

    def _infer_attack_phase(self, pressure_index: float, terminal_settle: float, route_directness: float) -> str:
        if pressure_index >= 0.72 and terminal_settle < 0.4:
            return "under_pressure"
        if pressure_index >= 0.58 and route_directness >= 0.56:
            return "transition"
        if pressure_index < 0.38 and terminal_settle >= 0.42:
            return "advantage"
        return "neutral"

    def _infer_tempo_profile(self, mean_speed_kmh: float, max_speed_kmh: float, speed_volatility: float) -> str:
        if max_speed_kmh >= 185 or mean_speed_kmh >= 100:
            return "fast"
        if mean_speed_kmh >= 72 or speed_volatility >= 28:
            return "medium-fast"
        if mean_speed_kmh <= 38 and speed_volatility <= 14:
            return "controlled"
        return "medium"

    def _infer_shot_shape(self, depth_span_ratio: float, lateral_span_ratio: float, route_directness: float, terminal_settle: float) -> str:
        if route_directness >= 0.72 and depth_span_ratio >= 0.46:
            return "direct-pressure"
        if lateral_span_ratio >= 0.42 and depth_span_ratio >= 0.35:
            return "stretching-angle"
        if terminal_settle >= 0.52 and depth_span_ratio < 0.28:
            return "soft-control"
        return "balanced-rally"
