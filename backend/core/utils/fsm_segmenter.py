import numpy as np


class BadmintonFSM:
    def __init__(self, fps, width, height):
        """
        Initialize the badminton finite-state machine.

        Args:
            fps: Video frame rate.
            width: Video width, used for normalization.
            height: Video height, used for normalization.
        """
        self.fps = fps
        self.width = width
        self.height = height

        # --- State Definitions ---
        # IDLE: dead ball / ball pickup
        # READY: serve preparation while the shuttle is held still
        # RALLY: rally in progress
        # COOLDOWN: short buffer after the shuttle lands
        self.state = "IDLE"

        # --- Tunable Thresholds ---
        self.speed_threshold_start = 0.015  # Normalized speed threshold to detect serve start
        self.speed_threshold_stop = 0.005   # Normalized speed threshold to detect shuttle stop
        self.ground_y_threshold = 0.85      # Bottom 15% of the frame is treated as ground area
        self.max_lost_frames = int(0.5 * fps)  # Allow 0.5 s of missing detections for occlusion tolerance
        self.cooldown_frames = int(1.5 * fps)  # Keep 1.5 s after landing for post-bounce context
        self.min_rally_frames = int(1.0 * fps)  # Minimum duration for a valid rally

        # --- Runtime State ---
        self.current_rally = []     # Buffer for the current rally trajectory
        self.all_rallies = []       # Final segmented rally list
        self.lost_counter = 0       # Consecutive missing-frame counter
        self.cooldown_counter = 0   # Cooldown countdown
        self.prev_coord = None      # Previous valid coordinate

    def update(self, frame_idx, coord):
        """
        Advance the FSM by one frame.

        Args:
            frame_idx: Current frame index.
            coord: Pixel coordinate tuple (x, y). Use (0, 0) for no detection.
        """
        # Normalize coordinates to 0.0 ~ 1.0.
        norm_x = coord[0] / self.width
        norm_y = coord[1] / self.height
        has_ball = coord[0] > 0 and coord[1] > 0

        # Compute instantaneous normalized speed.
        speed = 0.0
        if has_ball and self.prev_coord is not None:
            dx = norm_x - (self.prev_coord[0] / self.width)
            dy = norm_y - (self.prev_coord[1] / self.height)
            speed = np.sqrt(dx**2 + dy**2)

        # === State Transition Logic ===
        if self.state == "IDLE":
            if has_ball:
                # Start a rally when speed spikes and the shuttle is not near the ground.
                if speed > self.speed_threshold_start and norm_y < self.ground_y_threshold:
                    self._transition_to_rally(frame_idx, coord)
                self.prev_coord = coord
            else:
                self.prev_coord = None

        elif self.state == "RALLY":
            if has_ball:
                self.lost_counter = 0  # Reset lost-frame count.
                self.current_rally.append(coord)
                self.prev_coord = coord

                # End condition 1: shuttle touches the ground.
                if norm_y > self.ground_y_threshold:
                    self._transition_to_cooldown("Ground Touch")

                # End condition 2: shuttle speed drops to nearly zero.
                elif speed < self.speed_threshold_stop and len(self.current_rally) > 10:
                    self._transition_to_cooldown("Stop")

            else:
                # Handle missing detections.
                self.lost_counter += 1
                # Keep the time axis aligned with an empty placeholder if needed.
                self.current_rally.append((0, 0))

                # End condition 3: shuttle lost for too long.
                if self.lost_counter > self.max_lost_frames:
                    self._transition_to_cooldown("Lost Track")

        elif self.state == "COOLDOWN":
            # Keep recording during cooldown to preserve post-bounce details.
            if has_ball:
                self.current_rally.append(coord)
            else:
                self.current_rally.append((0, 0))

            self.cooldown_counter -= 1
            if self.cooldown_counter <= 0:
                self._finalize_rally()

    def _transition_to_rally(self, frame_idx, coord):
        print(f"[FSM] Frame {frame_idx}: State IDLE -> RALLY")
        self.state = "RALLY"
        self.current_rally = [coord]  # Initialize the rally buffer.
        self.lost_counter = 0

    def _transition_to_cooldown(self, reason):
        print(f"[FSM] State RALLY -> COOLDOWN ({reason})")
        self.state = "COOLDOWN"
        self.cooldown_counter = self.cooldown_frames

    def _finalize_rally(self):
        # Filter out accidental short sequences such as pickup tosses.
        valid_frames = [point for point in self.current_rally if point[0] > 0]
        if len(valid_frames) > self.min_rally_frames:
            print(f"[FSM] Rally Saved. Frames: {len(self.current_rally)}")
            # We currently store coordinate lists, but frame ranges would also work.
            self.all_rallies.append(list(self.current_rally))
        else:
            print("[FSM] Rally Discarded (Too short/Noise)")

        self.state = "IDLE"
        self.current_rally = []
        self.prev_coord = None

    def get_segments(self):
        """Return the segmented rally trajectory list."""
        return self.all_rallies
