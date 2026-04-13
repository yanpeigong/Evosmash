import numpy as np


class BadmintonFSM:
    def __init__(self, fps, width, height):
        self.fps = fps
        self.width = width
        self.height = height

        self.state = "IDLE"
        self.speed_threshold_start = 0.015
        self.speed_threshold_stop = 0.005
        self.ground_y_threshold = 0.85
        self.max_lost_frames = int(0.5 * fps)
        self.cooldown_frames = int(1.5 * fps)
        self.min_rally_frames = int(1.0 * fps)

        self.current_rally = []
        self.all_rallies = []
        self.segment_meta = []
        self.lost_counter = 0
        self.cooldown_counter = 0
        self.prev_coord = None
        self.current_meta = self._new_meta()

    def update(self, frame_idx, coord):
        norm_x = coord[0] / self.width
        norm_y = coord[1] / self.height
        has_ball = coord[0] > 0 and coord[1] > 0

        speed = 0.0
        if has_ball and self.prev_coord is not None:
            dx = norm_x - (self.prev_coord[0] / self.width)
            dy = norm_y - (self.prev_coord[1] / self.height)
            speed = np.sqrt(dx**2 + dy**2)

        if self.state == "IDLE":
            if has_ball:
                if speed > self.speed_threshold_start and norm_y < self.ground_y_threshold:
                    self._transition_to_rally(frame_idx, coord)
                self.prev_coord = coord
            else:
                self.prev_coord = None

        elif self.state == "RALLY":
            if has_ball:
                self.lost_counter = 0
                self.current_rally.append(coord)
                self.prev_coord = coord
                self.current_meta["speed_samples"].append(float(speed))

                if norm_y > self.ground_y_threshold:
                    self.current_meta["end_reason"] = "ground_touch"
                    self._transition_to_cooldown("Ground Touch")
                elif speed < self.speed_threshold_stop and len(self.current_rally) > 10:
                    self.current_meta["end_reason"] = "speed_stop"
                    self._transition_to_cooldown("Stop")
            else:
                self.lost_counter += 1
                self.current_meta["lost_frames"] += 1
                self.current_rally.append((0, 0))

                if self.lost_counter > self.max_lost_frames:
                    self.current_meta["end_reason"] = "lost_track"
                    self._transition_to_cooldown("Lost Track")

        elif self.state == "COOLDOWN":
            if has_ball:
                self.current_rally.append(coord)
            else:
                self.current_rally.append((0, 0))
                self.current_meta["lost_frames"] += 1

            self.cooldown_counter -= 1
            if self.cooldown_counter <= 0:
                self._finalize_rally()

    def _transition_to_rally(self, frame_idx, coord):
        print(f"[FSM] Frame {frame_idx}: State IDLE -> RALLY")
        self.state = "RALLY"
        self.current_rally = [coord]
        self.lost_counter = 0
        self.current_meta = self._new_meta()
        self.current_meta["start_frame"] = frame_idx

    def _transition_to_cooldown(self, reason):
        print(f"[FSM] State RALLY -> COOLDOWN ({reason})")
        self.state = "COOLDOWN"
        self.cooldown_counter = self.cooldown_frames

    def _finalize_rally(self):
        valid_frames = [point for point in self.current_rally if point[0] > 0]
        if len(valid_frames) > self.min_rally_frames:
            print(f"[FSM] Rally Saved. Frames: {len(self.current_rally)}")
            self.all_rallies.append(list(self.current_rally))
            self.segment_meta.append(self._segment_summary(valid_frames))
        else:
            print("[FSM] Rally Discarded (Too short/Noise)")

        self.state = "IDLE"
        self.current_rally = []
        self.prev_coord = None
        self.current_meta = self._new_meta()

    def get_segments(self):
        return self.all_rallies

    def get_segment_summaries(self):
        return self.segment_meta

    def _segment_summary(self, valid_frames):
        coords = np.array(valid_frames, dtype=np.float32)
        x_span = float(coords[:, 0].max() - coords[:, 0].min()) / max(self.width, 1)
        y_span = float(coords[:, 1].max() - coords[:, 1].min()) / max(self.height, 1)
        speed_samples = self.current_meta.get("speed_samples", [])
        mean_speed = float(np.mean(speed_samples)) if speed_samples else 0.0
        quality = float(np.clip(
            0.35 * min(len(valid_frames) / max(self.min_rally_frames * 1.8, 1), 1.0) +
            0.25 * (1.0 - self.current_meta.get("lost_frames", 0) / max(len(self.current_rally), 1)) +
            0.2 * min((x_span + y_span) / 0.9, 1.0) +
            0.2 * min(mean_speed / (self.speed_threshold_start * 2.5), 1.0),
            0.0,
            1.0,
        ))
        return {
            "quality_score": round(quality, 3),
            "coverage_span": {
                "x": round(x_span, 3),
                "y": round(y_span, 3),
            },
            "lost_frames": self.current_meta.get("lost_frames", 0),
            "mean_normalized_speed": round(mean_speed, 4),
            "end_reason": self.current_meta.get("end_reason", "unknown"),
        }

    def _new_meta(self):
        return {
            "start_frame": 0,
            "lost_frames": 0,
            "speed_samples": [],
            "end_reason": "unknown",
        }
