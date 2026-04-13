import cv2
import numpy as np

from config import COURT_LENGTH, COURT_WIDTH_DOUBLES
from .referee import AutoReferee


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

        dt = 1.0 / max(fps, 1)
        deltas = np.diff(valid_coords, axis=0) if len(valid_coords) > 1 else np.empty((0, 2), dtype=np.float32)
        velocities = np.sqrt(np.sum(deltas ** 2, axis=1)) / dt if len(deltas) > 0 else np.array([])

        max_speed_kmh = np.max(velocities) * 3.6 if len(velocities) > 0 else 0
        mean_speed_kmh = np.mean(velocities) * 3.6 if len(velocities) > 0 else 0
        end_speed_kmh = np.mean(velocities[-3:]) * 3.6 if len(velocities) >= 3 else mean_speed_kmh

        trajectory_quality = self._estimate_trajectory_quality(world_coords, valid_coords)
        match_details = self.referee.judge_details(valid_coords, match_type)
        match_result = match_details.get('auto_result', 'UNKNOWN')
        event_name = self._classify_event(max_speed_kmh, mean_speed_kmh)

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
            f"Referee confidence {match_details.get('referee_confidence', 0.0):.2f}; trajectory quality {trajectory_quality:.2f}."
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
            "rally_state": rally_state,
        }

    def calculate_reward(self, result_type):
        mapping = {"WIN": 10.0, "LOSS": -5.0, "GOOD": 2.0, "BAD": -2.0}
        return mapping.get(result_type, 0.0)

    def _valid_coords(self, world_coords):
        return np.array([point for point in world_coords if not (point[0] == 0 and point[1] == 0)], dtype=np.float32)

    def _estimate_trajectory_quality(self, world_coords, valid_coords):
        if len(world_coords) == 0 or len(valid_coords) == 0:
            return 0.0

        visibility_ratio = len(valid_coords) / len(world_coords)
        length_factor = min(len(valid_coords) / 12.0, 1.0)
        if len(valid_coords) > 2:
            deltas = np.diff(valid_coords, axis=0)
            smoothness = np.mean(np.linalg.norm(deltas, axis=1))
            stability_factor = float(np.clip(1.0 - min(smoothness / 8.0, 0.4), 0.6, 1.0))
        else:
            stability_factor = 0.6

        return float(np.clip(0.45 * visibility_ratio + 0.3 * length_factor + 0.25 * stability_factor, 0.0, 1.0))

    def _classify_event(self, max_speed_kmh, mean_speed_kmh):
        if max_speed_kmh >= 180:
            return "Power Smash"
        if max_speed_kmh >= 135:
            return "Smash"
        if mean_speed_kmh >= 80:
            return "Drive Exchange"
        if mean_speed_kmh >= 45:
            return "Pressure Rally"
        return "Control Rally"
