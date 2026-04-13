import cv2
import numpy as np

from config import COURT_LENGTH, COURT_WIDTH_DOUBLES, SIDE_ALLEY_WIDTH


class AutoReferee:
    def __init__(self):
        pass

    def get_court_polygon(self, match_type):
        """Build the in-bounds polygon for singles or doubles mode."""
        if match_type == 'singles':
            # Singles: shrink inward by 0.46 m on both sides.
            x_min = SIDE_ALLEY_WIDTH
            x_max = COURT_WIDTH_DOUBLES - SIDE_ALLEY_WIDTH
        else:
            # Doubles: use the full court width.
            x_min = 0.0
            x_max = COURT_WIDTH_DOUBLES

        # Rectangle ordered as TL, TR, BR, BL.
        return np.array([
            [x_min, 0],
            [x_max, 0],
            [x_max, COURT_LENGTH],
            [x_min, COURT_LENGTH],
        ], dtype=np.float32)

    def judge(self, trajectory_world, match_type='singles'):
        """
        Args:
            trajectory_world: Shuttle trajectory in world coordinates.
            match_type: 'singles' or 'doubles'.
        """
        if len(trajectory_world) < 5:
            return 'UNKNOWN'

        trajectory = np.array(trajectory_world)
        court_polygon = self.get_court_polygon(match_type)

        # 1. Infer who hit last, assuming the camera sits behind the user.
        # dy < 0: shuttle travels away from the camera -> user hit
        # dy > 0: shuttle travels toward the camera -> opponent hit
        start_node = trajectory[-5]
        end_node = trajectory[-1]
        dy = end_node[1] - start_node[1]

        last_hitter = "USER" if dy < 0 else "OPPONENT"

        # 2. Check whether the landing point is in or out.
        last_point = tuple(end_node)
        # pointPolygonTest >= 0 means the point is inside or on the boundary.
        is_in = cv2.pointPolygonTest(court_polygon, last_point, False) >= 0

        # 3. Convert the call into a user-centric win/loss result.
        if last_hitter == "USER":
            return "WIN" if is_in else "LOSS"
        return "LOSS" if is_in else "WIN"
