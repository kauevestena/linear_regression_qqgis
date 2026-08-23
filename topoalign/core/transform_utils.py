# -*- coding: utf-8 -*-
"""
Pure NumPy mathematical utilities for coordinate transformations and alignment projections.
Includes:
- 2D Helmert Transformation (4-parameter Conformal)
- Station & Offset (Chainage and transverse offset along alignments)
"""

import numpy as np
from typing import Tuple, Optional, Dict, Any, List


def helmert_2d_fit(
    src_x: np.ndarray,
    src_y: np.ndarray,
    tgt_x: np.ndarray,
    tgt_y: np.ndarray
) -> Dict[str, Any]:
    """
    Computes 2D Helmert (4-parameter Conformal) Transformation using Least Squares.
    Model:
        [X] = [ a  -b ] [x] + [Tx]
        [Y]   [ b   a ] [y]   [Ty]
    where a = s*cos(theta), b = s*sin(theta).

    Args:
        src_x: 1D array of source X coordinates (at least 2 points)
        src_y: 1D array of source Y coordinates
        tgt_x: 1D array of target X coordinates
        tgt_y: 1D array of target Y coordinates

    Returns:
        Dictionary containing:
        - 'tx': Translation in X (Tx)
        - 'ty': Translation in Y (Ty)
        - 'scale': Scale factor (s)
        - 'rotation_rad': Rotation angle in radians
        - 'rotation_deg': Rotation angle in degrees
        - 'a': Conformal parameter a = s*cos(theta)
        - 'b': Conformal parameter b = s*sin(theta)
        - 'residuals_x': Residuals in X (Vx = X_calc - X_tgt)
        - 'residuals_y': Residuals in Y (Vy = Y_calc - Y_tgt)
        - 'residuals_dist': Euclidean residuals sqrt(Vx^2 + Vy^2)
        - 'rmse': Root Mean Square Error of the transformation
    """
    src_x = np.asarray(src_x, dtype=float)
    src_y = np.asarray(src_y, dtype=float)
    tgt_x = np.asarray(tgt_x, dtype=float)
    tgt_y = np.asarray(tgt_y, dtype=float)

    n = len(src_x)
    if n < 2 or len(src_y) != n or len(tgt_x) != n or len(tgt_y) != n:
        raise ValueError("At least 2 common control points with valid coordinates are required.")

    x_mean = np.mean(src_x)
    y_mean = np.mean(src_y)
    X_mean = np.mean(tgt_x)
    Y_mean = np.mean(tgt_y)

    dx = src_x - x_mean
    dy = src_y - y_mean
    dX = tgt_x - X_mean
    dY = tgt_y - Y_mean

    denom = np.sum(dx**2 + dy**2)
    if denom == 0:
        raise ValueError("Source control points are degenerate (identical coordinates).")

    a = np.sum(dx * dX + dy * dY) / denom
    b = np.sum(dx * dY - dy * dX) / denom

    tx = X_mean - (a * x_mean - b * y_mean)
    ty = Y_mean - (b * x_mean + a * y_mean)

    scale = np.sqrt(a**2 + b**2)
    rotation_rad = np.arctan2(b, a)
    rotation_deg = np.degrees(rotation_rad)

    # Compute transformed points and residuals
    calc_X = a * src_x - b * src_y + tx
    calc_Y = b * src_x + a * src_y + ty

    vx = calc_X - tgt_x
    vy = calc_Y - tgt_y
    res_dist = np.sqrt(vx**2 + vy**2)

    # RMSE: degrees of freedom = 2n - 4 (if n > 2)
    dof = 2 * n - 4
    if dof > 0:
        rmse = np.sqrt(np.sum(vx**2 + vy**2) / dof)
    else:
        rmse = np.sqrt(np.sum(vx**2 + vy**2) / (2 * n))

    return {
        'tx': float(tx),
        'ty': float(ty),
        'scale': float(scale),
        'rotation_rad': float(rotation_rad),
        'rotation_deg': float(rotation_deg),
        'a': float(a),
        'b': float(b),
        'residuals_x': vx,
        'residuals_y': vy,
        'residuals_dist': res_dist,
        'rmse': float(rmse)
    }


def helmert_2d_transform(
    x: np.ndarray,
    y: np.ndarray,
    tx: float,
    ty: float,
    scale: float,
    rotation_deg: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Applies 2D Helmert transformation parameters to given coordinates.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    rot_rad = np.radians(rotation_deg)
    a = scale * np.cos(rot_rad)
    b = scale * np.sin(rot_rad)

    X = a * x - b * y + tx
    Y = b * x + a * y + ty
    return X, Y


def helmert_2d_inverse_transform(
    X: np.ndarray,
    Y: np.ndarray,
    tx: float,
    ty: float,
    scale: float,
    rotation_deg: float
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Applies inverse 2D Helmert transformation.
    """
    X = np.asarray(X, dtype=float)
    Y = np.asarray(Y, dtype=float)

    if scale == 0:
        raise ValueError("Scale factor cannot be zero.")

    rot_rad = np.radians(rotation_deg)
    a = scale * np.cos(rot_rad)
    b = scale * np.sin(rot_rad)
    det = a**2 + b**2

    dX = X - tx
    dY = Y - ty

    x = (a * dX + b * dY) / det
    y = (-b * dX + a * dY) / det
    return x, y


def project_points_to_alignment(
    px: np.ndarray,
    py: np.ndarray,
    line_vertices: List[Tuple[float, float]],
    start_station: float = 0.0,
    station_interval: float = 20.0
) -> Dict[str, np.ndarray]:
    """
    Projects points onto a multi-segment reference alignment line.

    Args:
        px, py: Arrays of point coordinates.
        line_vertices: Ordered list of (x, y) tuples defining the alignment polyline.
        start_station: Initial station/chainage value at the start of the line (in meters).
        station_interval: Interval for station numbering (e.g., 20.0m for standard 20m stations).

    Returns:
        Dictionary with arrays:
        - 'station_m': Total cumulative station in meters along the alignment.
        - 'station_num': Station number (station_m / station_interval).
        - 'station_plus': Plus distance beyond the station number (station_m % station_interval).
        - 'offset': Transverse orthogonal offset (+ for Right, - for Left of line direction).
        - 'proj_x': Projected X coordinate on the alignment line.
        - 'proj_y': Projected Y coordinate on the alignment line.
    """
    px = np.asarray(px, dtype=float)
    py = np.asarray(py, dtype=float)

    if len(line_vertices) < 2:
        raise ValueError("Alignment must have at least 2 vertices.")

    verts = np.asarray(line_vertices, dtype=float)
    v_start = verts[:-1]  # Shape: (num_segs, 2)
    v_end = verts[1:]     # Shape: (num_segs, 2)

    seg_vecs = v_end - v_start  # (num_segs, 2)
    seg_lens = np.linalg.norm(seg_vecs, axis=1)  # (num_segs,)

    # Remove zero-length segments if any
    valid_mask = seg_lens > 1e-9
    v_start = v_start[valid_mask]
    v_end = v_end[valid_mask]
    seg_vecs = seg_vecs[valid_mask]
    seg_lens = seg_lens[valid_mask]

    if len(seg_lens) == 0:
        raise ValueError("Alignment line has zero total length.")

    cum_lengths = np.insert(np.cumsum(seg_lens), 0, 0.0)  # Length at each vertex

    num_pts = len(px)
    out_station = np.zeros(num_pts, dtype=float)
    out_offset = np.zeros(num_pts, dtype=float)
    out_proj_x = np.zeros(num_pts, dtype=float)
    out_proj_y = np.zeros(num_pts, dtype=float)

    # For each point, find the closest projection across all segments
    for i in range(num_pts):
        pt = np.array([px[i], py[i]])

        # Vector from start of each segment to point: (num_segs, 2)
        pt_vecs = pt - v_start

        # Dot product with segment direction vector
        # t = (pt_vec . seg_vec) / |seg_vec|^2
        t = np.sum(pt_vecs * seg_vecs, axis=1) / (seg_lens**2)
        t_clamped = np.clip(t, 0.0, 1.0)

        # Projected point coordinates on each segment
        proj_pts = v_start + t_clamped[:, np.newaxis] * seg_vecs  # (num_segs, 2)

        # Distance from point to projected point on each segment
        dists = np.linalg.norm(pt - proj_pts, axis=1)

        best_seg = np.argmin(dists)
        best_proj = proj_pts[best_seg]
        t_best = t_clamped[best_seg]

        # Station in meters
        s_m = start_station + cum_lengths[best_seg] + t_best * seg_lens[best_seg]

        # Signed transverse offset (Cross product in 2D: seg_vec_x * dy - seg_vec_y * dx)
        # > 0 means Right side of alignment, < 0 means Left side
        sv = seg_vecs[best_seg]
        pv = pt - best_proj
        cross = sv[0] * pv[1] - sv[1] * pv[0]
        # Cross product (sv_x * pv_y - sv_y * pv_x):
        # If line goes (0,0) to (0,10) [North], sv=(0,10). Pt=(5, 5) [East, Right], pv=(5,0).
        # cross = 0*0 - 10*5 = -50.
        # Standard convention: Right is positive (+), Left is negative (-).
        # So signed_offset = -cross / seg_len:
        signed_offset = -cross / seg_lens[best_seg]

        out_station[i] = s_m
        out_offset[i] = signed_offset
        out_proj_x[i] = best_proj[0]
        out_proj_y[i] = best_proj[1]

    if station_interval <= 0:
        station_interval = 20.0

    station_num = np.floor(out_station / station_interval)
    station_plus = out_station - (station_num * station_interval)

    return {
        'station_m': out_station,
        'station_num': station_num,
        'station_plus': station_plus,
        'offset': out_offset,
        'proj_x': out_proj_x,
        'proj_y': out_proj_y
    }
