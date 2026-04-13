import cv2
import numpy as np

from config import COURT_LENGTH, COURT_WIDTH_DOUBLES
from .referee import AutoReferee
from .trajectory_features import TrajectoryFeatureExtractor


class PhysicsEngine:
    def __init__(self):
        self.std_points = np.array(
            [
                [0, 0],
                [COURT_WIDTH_DOUBLES, 0],
                [COURT_WIDTH_DOUBLES, COURT_LENGTH],
                [0, COURT_LENGTH],
            ],
            dtype=np.float32,
        )
        self.homography_matrix = None
        self.referee = AutoReferee()
        self.feature_extractor = TrajectoryFeatureExtractor()

    def update_homography(self, detected_corners):
        self.homography_matrix, _ = cv2.findHomography(detected_corners, self.std_points)

    def pixel_to_world(self, pixel_coords):
        if self.homography_matrix is None:
            return np.array(pixel_coords) * 0.02

        points = np.array(pixel_coords, dtype=np.float32).reshape(-1, 1, 2)
        world_points = cv2.perspectiveTransform(points, self.homography_matrix)
        return world_points.reshape(-1, 2)

    def analyze_trajectory(self, trajectory_pixels, fps, match_type="singles"):
        world_coords = self.pixel_to_world(trajectory_pixels)
        valid_coords = self._valid_coords(world_coords)
        trajectory_features = self.feature_extractor.extract(world_coords, valid_coords, fps)

        max_speed_kmh = trajectory_features.get('max_speed_kmh', 0.0)
        mean_speed_kmh = trajectory_features.get('mean_speed_kmh', 0.0)
        end_speed_kmh = trajectory_features.get('end_speed_kmh', 0.0)
        pressure_index = trajectory_features.get('pressure_index', 0.0)

        trajectory_quality = self._estimate_trajectory_quality(trajectory_features)
        match_details = self.referee.judge_details(
            valid_coords,
            match_type,
            trajectory_features=trajectory_features,
        )
        match_result = match_details.get('auto_result', 'UNKNOWN')
        event_name = self._classify_event(trajectory_features)

        mode_label = "Singles" if match_type == "singles" else "Doubles"
        description_parts = [f"Mode: {mode_label}.", f"Event: {event_name}."]
        if max_speed_kmh > 0:
            description_parts.append(f"Max shuttle speed {int(max_speed_kmh)} km/h.")
        if match_result == "WIN":
            description_parts.append("Verdict: point won.")
        elif match_result == "LOSS":
            description_parts.append("Verdict: point lost.")
        else:
            description_parts.append("Verdict: unresolved call.")
        description_parts.append(
            f"Phase {trajectory_features.get('attack_phase', 'neutral')}, tempo {trajectory_features.get('tempo_profile', 'medium')}, shot shape {trajectory_features.get('shot_shape', 'balanced-rally')}."
        )
        description_parts.append(
            f"Referee confidence {match_details.get('referee_confidence', 0.0):.2f}; trajectory quality {trajectory_quality:.2f}; pressure index {pressure_index:.2f}."
        )

        rally_state = {
            'trajectory_quality': round(trajectory_quality, 3),
            'landing_confidence': match_details.get('landing_confidence', 0.0),
            'direction_consistency': match_details.get('direction_consistency', 0.0),
            'court_context': match_details.get('court_context', 'unknown'),
            'speed_profile': {
                'mean_speed_kmh': round(mean_speed_kmh, 2),
                'max_speed_kmh': round(max_speed_kmh, 2),
                'end_speed_kmh': round(end_speed_kmh, 2),
            },
            'attack_phase': trajectory_features.get('attack_phase', 'neutral'),
            'tempo_profile': trajectory_features.get('tempo_profile', 'medium'),
            'shot_shape': trajectory_features.get('shot_shape', 'balanced-rally'),
            'pressure_index': round(pressure_index, 3),
        }

        return {
            "event": event_name,
            "max_speed_kmh": round(max_speed_kmh, 1),
            "description": " ".join(description_parts),
            "coordinates": valid_coords.tolist(),
            "auto_result": match_result,
            "match_type": match_type,
            "trajectory_quality": round(trajectory_quality, 3),
            "referee_confidence": match_details.get('referee_confidence', 0.0),
            "referee_reason": match_details.get('referee_reason', 'Unavailable'),
            "landing_confidence": match_details.get('landing_confidence', 0.0),
            "direction_consistency": match_details.get('direction_consistency', 0.0),
            "landing_margin": match_details.get('landing_margin', 0.0),
            "court_context": match_details.get('court_context', 'unknown'),
            "last_hitter": match_details.get('last_hitter', 'UNKNOWN'),
            "landing_point": match_details.get('landing_point'),
            "attack_phase": trajectory_features.get('attack_phase', 'neutral'),
            "tempo_profile": trajectory_features.get('tempo_profile', 'medium'),
            "shot_shape": trajectory_features.get('shot_shape', 'balanced-rally'),
            "pressure_index": round(pressure_index, 3),
            "trajectory_features": trajectory_features,
            "referee_trace": match_details.get('referee_trace', {}),
            "rally_state": rally_state,
        }

    def calculate_reward(self, result_type, trajectory_quality=0.5, referee_confidence=0.5, pressure_index=0.5):
        mapping = {"WIN": 10.0, "LOSS": -5.0, "GOOD": 2.0, "BAD": -2.0}
        base_reward = mapping.get(result_type, 0.0)
        certainty_bonus = 0.7 + 0.2 * float(trajectory_quality or 0.5) + 0.1 * float(referee_confidence or 0.5)
        pressure_scale = 1.0 + 0.08 * float(pressure_index or 0.0)
        return round(base_reward * certainty_bonus * pressure_scale, 3)

    def _valid_coords(self, world_coords):
        return np.array([point for point in world_coords if not (point[0] == 0 and point[1] == 0)], dtype=np.float32)

    def _estimate_trajectory_quality(self, trajectory_features):
        visibility = float(trajectory_features.get('visibility_ratio', 0.0) or 0.0)
        directness = float(trajectory_features.get('route_directness', 0.0) or 0.0)
        sample_count = float(trajectory_features.get('sample_count', 0) or 0)
        terminal_settle = float(trajectory_features.get('terminal_settle', 0.0) or 0.0)
        pressure_index = float(trajectory_features.get('pressure_index', 0.0) or 0.0)
        coverage_factor = min(sample_count / 12.0, 1.0)
        return float(np.clip(
            0.36 * visibility + 0.24 * coverage_factor + 0.18 * directness + 0.12 * terminal_settle + 0.1 * min(pressure_index + 0.25, 1.0),
            0.0,
            1.0,
        ))

    def _classify_event(self, trajectory_features):
        max_speed_kmh = float(trajectory_features.get('max_speed_kmh', 0.0) or 0.0)
        mean_speed_kmh = float(trajectory_features.get('mean_speed_kmh', 0.0) or 0.0)
        lateral_span_ratio = float(trajectory_features.get('lateral_span_ratio', 0.0) or 0.0)
        depth_span_ratio = float(trajectory_features.get('depth_span_ratio', 0.0) or 0.0)
        pressure_index = float(trajectory_features.get('pressure_index', 0.0) or 0.0)
        shot_shape = trajectory_features.get('shot_shape', 'balanced-rally')
        terminal_settle = float(trajectory_features.get('terminal_settle', 0.0) or 0.0)

        if max_speed_kmh >= 190 and depth_span_ratio >= 0.4:
            return "Power Smash"
        if max_speed_kmh >= 150 and shot_shape == 'direct-pressure':
            return "Steep Smash"
        if mean_speed_kmh >= 95 and lateral_span_ratio < 0.35:
            return "Fast Flat Exchange"
        if mean_speed_kmh >= 78:
            return "Drive Exchange"
        if shot_shape == 'soft-control' and terminal_settle >= 0.48:
            return "Net Control"
        if pressure_index >= 0.58:
            return "Pressure Rally"
        return "Control Rally"
