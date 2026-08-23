# -*- coding: utf-8 -*-

import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.transform_utils import (
    helmert_2d_fit,
    helmert_2d_transform,
    helmert_2d_inverse_transform,
    project_points_to_alignment
)


def test_helmert_2d_identity():
    # Identical source and target
    src_x = np.array([0.0, 10.0, 10.0, 0.0])
    src_y = np.array([0.0, 0.0, 10.0, 10.0])
    tgt_x = src_x.copy()
    tgt_y = src_y.copy()

    res = helmert_2d_fit(src_x, src_y, tgt_x, tgt_y)

    assert res['tx'] == pytest.approx(0.0, abs=1e-9)
    assert res['ty'] == pytest.approx(0.0, abs=1e-9)
    assert res['scale'] == pytest.approx(1.0, abs=1e-9)
    assert res['rotation_deg'] == pytest.approx(0.0, abs=1e-9)
    assert res['rmse'] == pytest.approx(0.0, abs=1e-9)


def test_helmert_2d_pure_translation():
    src_x = np.array([10.0, 20.0, 30.0])
    src_y = np.array([5.0, 15.0, 25.0])
    tgt_x = src_x + 100.0
    tgt_y = src_y - 50.0

    res = helmert_2d_fit(src_x, src_y, tgt_x, tgt_y)

    assert res['tx'] == pytest.approx(100.0, abs=1e-9)
    assert res['ty'] == pytest.approx(-50.0, abs=1e-9)
    assert res['scale'] == pytest.approx(1.0, abs=1e-9)
    assert res['rotation_deg'] == pytest.approx(0.0, abs=1e-9)
    assert res['rmse'] == pytest.approx(0.0, abs=1e-9)


def test_helmert_2d_rotation_and_scale():
    # 90 degrees rotation counter-clockwise, scale = 2.0, tx = 10, ty = 20
    # X = 2*(x*cos(90) - y*sin(90)) + 10 = -2*y + 10
    # Y = 2*(x*sin(90) + y*cos(90)) + 20 =  2*x + 20
    src_x = np.array([0.0, 5.0, 5.0, 0.0])
    src_y = np.array([0.0, 0.0, 5.0, 5.0])

    tgt_x = -2.0 * src_y + 10.0
    tgt_y = 2.0 * src_x + 20.0

    res = helmert_2d_fit(src_x, src_y, tgt_x, tgt_y)

    assert res['tx'] == pytest.approx(10.0, abs=1e-7)
    assert res['ty'] == pytest.approx(20.0, abs=1e-7)
    assert res['scale'] == pytest.approx(2.0, abs=1e-7)
    assert res['rotation_deg'] == pytest.approx(90.0, abs=1e-7)
    assert res['rmse'] == pytest.approx(0.0, abs=1e-7)

    # Test forward and inverse transform functions
    tx_pts, ty_pts = helmert_2d_transform(src_x, src_y, res['tx'], res['ty'], res['scale'], res['rotation_deg'])
    assert np.allclose(tx_pts, tgt_x)
    assert np.allclose(ty_pts, tgt_y)

    ix_pts, iy_pts = helmert_2d_inverse_transform(tgt_x, tgt_y, res['tx'], res['ty'], res['scale'], res['rotation_deg'])
    assert np.allclose(ix_pts, src_x)
    assert np.allclose(iy_pts, src_y)


def test_helmert_2d_degenerate():
    with pytest.raises(ValueError):
        helmert_2d_fit(np.array([1.0]), np.array([1.0]), np.array([2.0]), np.array([2.0]))

    with pytest.raises(ValueError):
        helmert_2d_fit(np.array([1.0, 1.0]), np.array([1.0, 1.0]), np.array([2.0, 3.0]), np.array([2.0, 3.0]))


def test_station_offset_straight_line():
    # Straight horizontal line from (0,0) to (100,0)
    line_verts = [(0.0, 0.0), (100.0, 0.0)]

    # Test points:
    # 1. (10, 0) -> on line at 10m, station 0+10, offset 0
    # 2. (30, -5) -> at 30m, 5m to the Right (Y=-5 is right of east-heading line)
    # 3. (50, 10) -> at 50m, 10m to the Left (Y=+10 is left of east-heading line)
    px = np.array([10.0, 30.0, 50.0])
    py = np.array([0.0, -5.0, 10.0])

    res = project_points_to_alignment(px, py, line_verts, start_station=0.0, station_interval=20.0)

    assert res['station_m'][0] == pytest.approx(10.0)
    assert res['offset'][0] == pytest.approx(0.0)
    assert res['station_num'][0] == 0
    assert res['station_plus'][0] == pytest.approx(10.0)

    assert res['station_m'][1] == pytest.approx(30.0)
    assert res['offset'][1] == pytest.approx(5.0)  # Positive for Right side
    assert res['station_num'][1] == 1  # 30m = station 1 + 10m
    assert res['station_plus'][1] == pytest.approx(10.0)

    assert res['station_m'][2] == pytest.approx(50.0)
    assert res['offset'][2] == pytest.approx(-10.0)  # Negative for Left side
    assert res['station_num'][2] == 2  # 50m = station 2 + 10m
    assert res['station_plus'][2] == pytest.approx(10.0)


def test_station_offset_multi_segment():
    # L-shaped alignment: (0,0) -> (100,0) -> (100,100)
    line_verts = [(0.0, 0.0), (100.0, 0.0), (100.0, 100.0)]

    # Point near second segment: (90, 50) -> projected on second segment at (100, 50)
    # Cumulative station: 100m + 50m = 150m
    # Direction of second segment is North (0, +1). Point is at X=90 (West / Left), so offset is -10m
    px = np.array([90.0])
    py = np.array([50.0])

    res = project_points_to_alignment(px, py, line_verts, start_station=1000.0, station_interval=20.0)

    assert res['station_m'][0] == pytest.approx(1150.0)
    assert res['offset'][0] == pytest.approx(-10.0)
    assert res['proj_x'][0] == pytest.approx(100.0)
    assert res['proj_y'][0] == pytest.approx(50.0)
