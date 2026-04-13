import cv2
import numpy as np

from config import COURT_LENGTH, COURT_WIDTH_DOUBLES, SIDE_ALLEY_WIDTH


class AutoReferee:
    def __init__(self):
        pass

    def get_court_polygon(self, match_type):
        """Build the in-bounds polygon for singles or doubles mode."""
        if match_type == 'singles':
            x_min = SIDE_ALLEY_WIDTH
            x_max = COURT_WIDTH_DOUBLES - SIDE_ALLEY_WIDTH
        else:
            x_min = 0.0
            x_max = COURT_WIDTH_DOUBLES

        return np.array([
            [x_min, 0],
            [x_max, 0],
            [x_max, COURT_LENGTH],
            [x_min, COURT_LENGTH],
        ], dtype=np.float32)

    def judge(self, trajectory_world, match_type='singles'):
        return self.judge_details(trajectory_world, match_type).get('auto_result', 'UNKNOWN')

    def judge_details(self, trajectory_world, match_type='singles'):
        valid_points = self._extract_valid_points(trajectory_world)
        if len(valid_points) < 5:
            return {
                'auto_result': 'UNKNOWN',
                'referee_confidence': 0.2,
                'referee_reason': 'Not enough valid trajectory points for a reliable call.',
                'landing_confidence': 0.2,
                'direction_consistency': 0.2,
                'landing_margin': 0.0,
                'court_context': 'unknown',
                'last_hitter': 'UNKNOWN',
                'is_in': None,
                'landing_point': None,
            }

        trajectory = np.array(valid_points, dtype=np.float32)
        court_polygon = self.get_court_polygon(match_type)
        last_point = tuple(trajectory[-1])

        direction_consistency, last_hitter = self._estimate_last_hitter(trajectory)
        landing_margin = float(cv2.pointPolygonTest(court_polygon, last_point, True))
        is_in = landing_margin >= 0
        landing_confidence = self._estimate_landing_confidence(trajectory, landing_margin)
        referee_confidence = float(np.clip(0.45 * direction_consistency + 0.55 * landing_confidence, 0.0, 1.0))
        court_context = self._infer_court_context(last_point)

        if referee_confidence < 0.33:
            auto_result = 'UNKNOWN'
            referee_reason = (
                f'Landing evidence is weak for a {match_type} call. '
                f'Direction consistency {direction_consistency:.2f}, landing confidence {landing_confidence:.2f}.'
            )
        else:
            if last_hitter == 'USER':
                auto_result = 'WIN' if is_in else 'LOSS'
            else:
                auto_result = 'LOSS' if is_in else 'WIN'
            verdict = 'in' if is_in else 'out'
            referee_reason = (
                f'Last hitter inferred as {last_hitter.lower()} with {direction_consistency:.2f} direction consistency; '
                f'landing appears {verdict} with a court margin of {landing_margin:.2f} m.'
            )

        return {
            'auto_result': auto_result,
            'referee_confidence': round(referee_confidence, 3),
            'referee_reason': referee_reason,
            'landing_confidence': round(landing_confidence, 3),
            'direction_consistency': round(direction_consistency, 3),
            'landing_margin': round(landing_margin, 3),
            'court_context': court_context,
            'last_hitter': last_hitter,
            'is_in': is_in,
            'landing_point': [float(last_point[0]), float(last_point[1])],
        }

    def _extract_valid_points(self, trajectory_world):
        return [point for point in trajectory_world if len(point) >= 2 and not (point[0] == 0 and point[1] == 0)]

    def _estimate_last_hitter(self, trajectory):
        tail = trajectory[-min(len(trajectory), 6):]
        deltas = np.diff(tail[:, 1])
        if len(deltas) == 0:
            return 0.2, 'UNKNOWN'

        signs = np.sign(deltas)
        non_zero = signs[signs != 0]
        if len(non_zero) == 0:
            return 0.25, 'UNKNOWN'

        dominant_sign = -1 if np.sum(non_zero < 0) >= np.sum(non_zero > 0) else 1
        direction_consistency = float(np.mean(non_zero == dominant_sign))
        last_hitter = 'USER' if dominant_sign < 0 else 'OPPONENT'
        return direction_consistency, last_hitter

    def _estimate_landing_confidence(self, trajectory, landing_margin):
        valid_points = len(trajectory)
        point_factor = min(valid_points / 12.0, 1.0)
        margin_factor = min(abs(landing_margin) / 0.45, 1.0)

        tail = trajectory[-min(valid_points, 5):]
        if len(tail) > 1:
            end_motion = np.mean(np.linalg.norm(np.diff(tail, axis=0), axis=1))
            stability_factor = float(np.clip(1.0 - min(end_motion / 1.2, 0.55), 0.45, 1.0))
        else:
            stability_factor = 0.6

        return float(np.clip(0.35 * point_factor + 0.4 * margin_factor + 0.25 * stability_factor, 0.0, 1.0))

    def _infer_court_context(self, landing_point):
        x, y = landing_point
        width_mid = COURT_WIDTH_DOUBLES / 2

        if y < COURT_LENGTH * 0.33:
            depth = 'front'
        elif y < COURT_LENGTH * 0.66:
            depth = 'mid'
        else:
            depth = 'rear'

        side_margin = min(abs(x), abs(COURT_WIDTH_DOUBLES - x))
        if side_margin < 0.7:
            width = 'wide'
        elif abs(x - width_mid) < 0.9:
            width = 'central'
        else:
            width = 'channel'

        return f'{depth}_{width}'
