import cv2
import numpy as np


class CourtDetector:
    def __init__(self):
        self.canny_low = 50
        self.canny_high = 150

        # ===== State =====
        self.prev_corners = None

        # Maximum allowed per-frame corner displacement in pixels.
        self.max_step = 5.0

    def detect(self, frame):
        h_img, w_img = frame.shape[:2]

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (5, 5), 0)
        edges = cv2.Canny(gray, self.canny_low, self.canny_high)

        lines = cv2.HoughLines(edges, 1, np.pi / 180, threshold=150)
        if lines is None or len(lines) < 4:
            return self._get_fallback_corners(w_img, h_img)

        lines = np.array([line[0] for line in lines])
        thetas = lines[:, 1].reshape(-1, 1)

        thetas_norm = np.hstack([np.cos(thetas), np.sin(thetas)])
        _, labels, _ = cv2.kmeans(
            thetas_norm.astype(np.float32),
            2,
            None,
            (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 50, 0.01),
            10,
            cv2.KMEANS_RANDOM_CENTERS,
        )

        group1 = lines[labels.ravel() == 0]
        group2 = lines[labels.ravel() == 1]

        if np.mean(np.abs(np.cos(group1[:, 1]))) > np.mean(np.abs(np.cos(group2[:, 1]))):
            vertical, horizontal = group1, group2
        else:
            vertical, horizontal = group2, group1

        if len(horizontal) < 2 or len(vertical) < 2:
            return self._get_fallback_corners(w_img, h_img)

        top = horizontal[np.argmin(horizontal[:, 0])]
        bottom = horizontal[np.argmax(horizontal[:, 0])]
        left = vertical[np.argmin(vertical[:, 0])]
        right = vertical[np.argmax(vertical[:, 0])]

        corners = np.array([
            self._intersect_rho_theta(top, left),
            self._intersect_rho_theta(top, right),
            self._intersect_rho_theta(bottom, right),
            self._intersect_rho_theta(bottom, left),
        ], dtype=np.float32)

        # Limit motion between frames so the detected corners settle smoothly.
        if self.prev_corners is None:
            self.prev_corners = corners
        else:
            delta = corners - self.prev_corners
            dist = np.linalg.norm(delta, axis=1, keepdims=True)

            # Avoid division by zero.
            dist = np.maximum(dist, 1e-6)

            scale = np.minimum(1.0, self.max_step / dist)
            corners = self.prev_corners + delta * scale
            self.prev_corners = corners

        return corners

    def _intersect_rho_theta(self, l1, l2):
        rho1, theta1 = l1
        rho2, theta2 = l2

        matrix = np.array([
            [np.cos(theta1), np.sin(theta1)],
            [np.cos(theta2), np.sin(theta2)],
        ])
        vector = np.array([rho1, rho2])

        if abs(np.linalg.det(matrix)) < 1e-6:
            return (0.0, 0.0)

        x, y = np.linalg.solve(matrix, vector)
        return (float(x), float(y))

    def _get_fallback_corners(self, w, h):
        return np.array([
            [w * 0.2, h * 0.3],
            [w * 0.8, h * 0.3],
            [w * 0.9, h * 0.9],
            [w * 0.1, h * 0.9],
        ], dtype=np.float32)
