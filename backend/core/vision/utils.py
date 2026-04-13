import cv2
import numpy as np
import scipy.signal
import torch

from config import HEIGHT, WIDTH


def get_ensemble_weight(seq_len, mode='weight'):
    """
    Build the temporal fusion weight vector.
    In `weight` mode, a Gaussian window emphasizes the center frames.
    """
    if mode == 'nonoverlap':
        return torch.ones(seq_len)
    if mode == 'average':
        return torch.ones(seq_len) / seq_len
    if mode == 'weight':
        # Use a Gaussian curve with std = seq_len / 3 to cover the main region.
        gaussian_weights = scipy.signal.gaussian(seq_len, std=seq_len / 3)
        return torch.from_numpy(gaussian_weights).float()
    raise ValueError('Invalid evaluation mode')


def generate_frames(video_path):
    """Read the video and resize frames to the model input resolution."""
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise IOError(f"Cannot open video: {video_path}")

    frames = []
    fps = cap.get(cv2.CAP_PROP_FPS)

    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # Force resize to TrackNet's expected 512x288 input.
        frame_resized = cv2.resize(frame, (WIDTH, HEIGHT))
        frames.append(frame_resized)

    cap.release()
    return frames, fps


def predict_location(heatmap):
    """Extract the center of the largest connected component from a heatmap."""
    heatmap = np.array(heatmap, dtype=np.uint8)
    _, thresh = cv2.threshold(heatmap, 127, 255, 0)
    contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    if len(contours) > 0:
        contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(contour)
        return (int(x + w / 2), int(y + h / 2))
    return (0, 0)


def generate_inpaint_mask(pred_dict):
    """
    Build the mask required by InpaintNet.
    If Visibility == 0 or the coordinate is (0, 0), mark it as missing.
    """
    frames = pred_dict['Frame']
    x_list = pred_dict['X']
    y_list = pred_dict['Y']
    vis_list = pred_dict['Visibility']

    mask = []
    for i in range(len(frames)):
        if vis_list[i] == 0 or (x_list[i] == 0 and y_list[i] == 0):
            mask.append(1.0)
        else:
            mask.append(0.0)
    return np.array(mask)


def get_model(model_name, seq_len=None, bg_mode=None):
    # Import lazily to avoid circular imports.
    from core.vision.models import InpaintNet, TrackNet

    if model_name == 'TrackNet':
        in_dim = seq_len * 3
        if bg_mode:
            # seq_len * 3 + 3 = 27 channels (8 RGB frames + 1 RGB background frame)
            in_dim = seq_len * 3 + 3
        out_dim = seq_len
        return TrackNet(in_dim, out_dim)
    if model_name == 'InpaintNet':
        return InpaintNet()
    raise ValueError(f"Unsupported model name: {model_name}")
