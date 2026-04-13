# core/vision/tracker.py

from __future__ import annotations

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset
from tqdm import tqdm

from config import COOR_TH, HEIGHT, INPAINTNET_PATH, TRACKNET_PATH, WIDTH
from core.vision.trajectory_postprocess import TrajectoryPostProcessor
from core.vision.utils import (
    generate_frames,
    generate_inpaint_mask,
    get_ensemble_weight,
    get_model,
    predict_location,
)


class VideoDataset(Dataset):
    def __init__(self, frames, seq_len, sliding_step=1, bg_frame=None):
        self.frames = frames
        self.seq_len = seq_len
        self.sliding_step = sliding_step
        self.bg_frame = bg_frame

    def __len__(self):
        return (len(self.frames) - self.seq_len) // self.sliding_step + 1

    def __getitem__(self, idx):
        base_idx = idx * self.sliding_step
        chunk = self.frames[base_idx: base_idx + self.seq_len]
        chunk = np.array(chunk, dtype=np.float32) / 255.0
        chunk = chunk.transpose(0, 3, 1, 2).reshape(-1, HEIGHT, WIDTH)

        if self.bg_frame is not None:
            bg = np.array(self.bg_frame, dtype=np.float32) / 255.0
            bg = bg.transpose(2, 0, 1)
            chunk = np.concatenate([chunk, bg], axis=0)

        indices = np.arange(base_idx, base_idx + self.seq_len)
        return torch.from_numpy(chunk), indices


class CoordinateDataset(Dataset):
    def __init__(self, coords, masks, seq_len):
        self.coords = coords
        self.masks = masks
        self.seq_len = seq_len
        pad_len = seq_len - 1
        self.coords = np.pad(self.coords, ((0, pad_len), (0, 0)), mode='edge')
        self.masks = np.pad(self.masks, (0, pad_len), mode='edge')

    def __len__(self):
        return len(self.coords) - self.seq_len + 1

    def __getitem__(self, idx):
        c = self.coords[idx: idx + self.seq_len]
        m = self.masks[idx: idx + self.seq_len]
        indices = np.arange(idx, idx + self.seq_len)
        return torch.from_numpy(c), torch.from_numpy(m), indices


class BallTracker:
    def __init__(self):
        self.device = torch.device('cuda:0' if torch.cuda.is_available() else 'cpu')
        self.postprocessor = TrajectoryPostProcessor()
        self.last_diagnostics = {}

        tn_ckpt = torch.load(TRACKNET_PATH, map_location=self.device)
        self.tn_seq_len = tn_ckpt['param_dict']['seq_len']
        self.bg_mode = tn_ckpt['param_dict'].get('bg_mode', None)

        self.tracknet = get_model('TrackNet', self.tn_seq_len, self.bg_mode).to(self.device)
        self.tracknet.load_state_dict(tn_ckpt['model'])
        self.tracknet.eval()

        self.inpaintnet = None
        if INPAINTNET_PATH:
            try:
                in_ckpt = torch.load(INPAINTNET_PATH, map_location=self.device)
                self.in_seq_len = in_ckpt['param_dict']['seq_len']
                self.inpaintnet = get_model('InpaintNet').to(self.device)
                self.inpaintnet.load_state_dict(in_ckpt['model'])
                self.inpaintnet.eval()
            except Exception as error:
                print(f"Warning: Failed to load InpaintNet: {error}")

    def infer(self, video_path):
        trajectory, fps, diagnostics = self.infer_detailed(video_path)
        self.last_diagnostics = diagnostics
        return trajectory, fps

    def infer_detailed(self, video_path):
        frames, fps = generate_frames(video_path)
        video_len = len(frames)

        bg_frame = None
        if self.bg_mode:
            print("Calculating background median...")
            if len(frames) > 50:
                indices = np.linspace(0, len(frames) - 1, 50, dtype=int)
                sample_frames = [frames[i] for i in indices]
                bg_frame = np.median(sample_frames, axis=0).astype(np.uint8)
            else:
                bg_frame = np.median(frames, axis=0).astype(np.uint8)

        dataset = VideoDataset(frames, self.tn_seq_len, sliding_step=1, bg_frame=bg_frame)
        loader = DataLoader(dataset, batch_size=16, shuffle=False)

        heatmap_accum = torch.zeros((video_len, HEIGHT, WIDTH), device='cpu')
        count_accum = torch.zeros((video_len, 1, 1), device='cpu')
        weight = get_ensemble_weight(self.tn_seq_len, mode='weight').view(self.tn_seq_len, 1, 1)

        with torch.no_grad():
            for x, indices in tqdm(loader, desc="TrackNet"):
                x = x.to(self.device)
                y_pred = self.tracknet(x).detach().cpu()

                for batch_index in range(y_pred.shape[0]):
                    idx = indices[batch_index]
                    heatmap_accum[idx] += y_pred[batch_index] * weight
                    count_accum[idx] += weight

        avg_heatmap = heatmap_accum / (count_accum + 1e-6)

        pred_dict = {'Frame': [], 'X': [], 'Y': [], 'Visibility': []}
        for frame_index in range(video_len):
            heatmap = avg_heatmap[frame_index].numpy() * 255
            cx, cy = predict_location(heatmap)
            pred_dict['Frame'].append(frame_index)
            pred_dict['X'].append(cx)
            pred_dict['Y'].append(cy)
            pred_dict['Visibility'].append(1 if (cx > 0 or cy > 0) else 0)

        raw_traj = list(zip(pred_dict['X'], pred_dict['Y']))
        if self.inpaintnet:
            mask = generate_inpaint_mask(pred_dict)
            coords = np.stack([pred_dict['X'], pred_dict['Y']], axis=1)

            coord_ds = CoordinateDataset(coords, mask, self.in_seq_len)
            coord_loader = DataLoader(coord_ds, batch_size=64, shuffle=False)

            coord_accum = torch.zeros((video_len, 2), device='cpu')
            coord_count = torch.zeros((video_len, 1), device='cpu')
            in_weight = get_ensemble_weight(self.in_seq_len, mode='weight').view(self.in_seq_len, 1)

            with torch.no_grad():
                for c_seq, m_seq, indices in tqdm(coord_loader, desc="InpaintNet"):
                    c_seq = c_seq.float().to(self.device)
                    m_seq = m_seq.float().to(self.device).unsqueeze(-1)
                    c_pred = self.inpaintnet(c_seq, m_seq).detach().cpu()

                    for batch_index in range(c_pred.shape[0]):
                        idx = indices[batch_index]
                        valid_mask = idx < video_len
                        valid_idx = idx[valid_mask]
                        if len(valid_idx) > 0:
                            valid_pred = c_pred[batch_index][valid_mask]
                            valid_weight = in_weight[valid_mask]
                            coord_accum[valid_idx] += valid_pred * valid_weight
                            coord_count[valid_idx] += valid_weight

            refined_coords = (coord_accum / (coord_count + 1e-6)).numpy()
            final_traj = []
            for frame_index in range(video_len):
                if mask[frame_index] > 0.5:
                    cx, cy = refined_coords[frame_index]
                    if cx < COOR_TH or cy < COOR_TH:
                        cx, cy = 0, 0
                else:
                    cx, cy = coords[frame_index]
                final_traj.append((int(cx), int(cy)))
        else:
            final_traj = raw_traj

        processed = self.postprocessor.postprocess(final_traj)
        diagnostics = {
            "video_frames": video_len,
            "raw_visible_frames": int(sum(1 for x, y in raw_traj if x > 0 and y > 0)),
            **processed['diagnostics'],
        }
        self.last_diagnostics = diagnostics
        return processed['trajectory'], fps, diagnostics
