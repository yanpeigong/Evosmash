import numpy as np
import torch
from scipy.signal import savgol_filter
from ultralytics import YOLO

from config import YOLO_PATH


class PoseAnalyzer:
    def __init__(self):
        self.model = YOLO(YOLO_PATH)
        self.device = "cuda:0" if torch.cuda.is_available() else "cpu"

    def infer(self, video_path):
        results = self.model(video_path, device=self.device, verbose=False, stream=True)
        pose_sequence = []

        for result in results:
            if result.keypoints is None or len(result.keypoints.data) == 0:
                pose_sequence.append(np.zeros((17, 3)))
                continue

            persons = result.keypoints.data.cpu().numpy()
            confidences = persons[..., 2].mean(axis=1)
            best_person = persons[np.argmax(confidences)]
            pose_sequence.append(best_person)

        return pose_sequence

    def evaluate_motion(self, pose_seq):
        knee_angles = []
        arm_angles = []

        for keypoints in pose_seq:
            if np.sum(keypoints) == 0:
                knee_angles.append(np.nan)
                arm_angles.append(np.nan)
                continue

            knee_angles.append(self._angle(keypoints[12], keypoints[14], keypoints[16]))
            arm_angles.append(self._angle(keypoints[6], keypoints[8], keypoints[10]))

        knee_angles = np.array(knee_angles)
        arm_angles = np.array(arm_angles)

        valid_mask = ~np.isnan(knee_angles)
        if valid_mask.sum() < 5:
            return "No reliable body motion was detected."

        knee_angles = knee_angles[valid_mask]
        arm_angles = arm_angles[valid_mask]

        window_length = min(11, len(knee_angles) if len(knee_angles) % 2 == 1 else len(knee_angles) - 1)
        window_length = max(window_length, 5)

        knee_smooth = savgol_filter(knee_angles, window_length, 3, mode="interp")
        arm_smooth = savgol_filter(arm_angles, window_length, 3, mode="interp")

        min_knee = np.percentile(knee_smooth, 5)
        max_arm = np.percentile(arm_smooth, 95)

        feedback = []

        if min_knee > 135:
            feedback.append("Base stays too high. Lower earlier to improve balance on defense.")
        elif min_knee < 100:
            feedback.append("Excellent lunge depth. Center-of-mass control looks strong.")
        else:
            feedback.append("Base control is solid, but there is room for a lower defensive stance.")

        if max_arm < 150:
            feedback.append("Arm extension is limited at contact, costing reach and power.")
        else:
            feedback.append("Contact point is well extended with strong striking structure.")

        return " | ".join(feedback)

    def _angle(self, a, b, c):
        a, b, c = a[:2], b[:2], c[:2]
        if np.any(np.isnan(a)) or np.any(np.isnan(b)) or np.any(np.isnan(c)):
            return np.nan

        ba = a - b
        bc = c - b

        norm = np.linalg.norm(ba) * np.linalg.norm(bc)
        if norm < 1e-6:
            return np.nan

        cosine = np.clip(np.dot(ba, bc) / norm, -1.0, 1.0)
        return np.degrees(np.arccos(cosine))
