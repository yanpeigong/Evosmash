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

        dt = 1.0 / fps
        deltas = np.diff(world_coords, axis=0)
        velocities = np.sqrt(np.sum(deltas ** 2, axis=1)) / dt
        max_speed_kmh = np.max(velocities) * 3.6 if len(velocities) > 0 else 0

        match_result = self.referee.judge(world_coords, match_type)

        mode_label = "Singles" if match_type == "singles" else "Doubles"
        description_parts = [f"Mode: {mode_label}."]
        if max_speed_kmh > 0:
            description_parts.append(f"Max shuttle speed {int(max_speed_kmh)} km/h.")
        if match_result == "WIN":
            description_parts.append("Verdict: point won, shuttle landed in.")
        elif match_result == "LOSS":
            description_parts.append("Verdict: point lost, shuttle landed out.")

        return {
            "event": "Smash" if max_speed_kmh > 150 else "Rally",
            "max_speed_kmh": round(max_speed_kmh, 1),
            "description": " ".join(description_parts),
            "coordinates": world_coords.tolist(),
            "auto_result": match_result,
            "match_type": match_type,
        }

    def calculate_reward(self, result_type):
        mapping = {"WIN": 10.0, "LOSS": -5.0, "GOOD": 2.0, "BAD": -2.0}
        return mapping.get(result_type, 0.0)
