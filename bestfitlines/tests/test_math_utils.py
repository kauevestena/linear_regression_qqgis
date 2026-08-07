import numpy as np
import pytest

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.math_utils import (
    total_least_squares,
    compute_residuals,
    compute_extreme_projections,
    project_point_to_line,
    chi_squared_test
)

def test_total_least_squares_basic():
    # Points exactly on y = 2x + 1
    x = np.array([0, 1, 2, 3])
    y = np.array([1, 3, 5, 7])

    A, B, C, a, b, r2 = total_least_squares(x, y)

    assert a == pytest.approx(2.0)
    assert b == pytest.approx(1.0)
    assert r2 == pytest.approx(1.0)

    # Check general form: Ax + By + C = 0
    # For y = 2x + 1, -2x + y - 1 = 0
    # Normalize: A = -2/sqrt(5), B = 1/sqrt(5), C = -1/sqrt(5)
    # Our function enforces A > 0 or A=0, B>0
    # So: A = 2/sqrt(5), B = -1/sqrt(5), C = 1/sqrt(5)

    norm = np.sqrt(5)
    assert A == pytest.approx(2 / norm)
    assert B == pytest.approx(-1 / norm)
    assert C == pytest.approx(1 / norm)

def test_total_least_squares_vertical():
    # Vertical line at x = 5
    x = np.array([5, 5, 5, 5])
    y = np.array([0, 1, 2, 3])

    A, B, C, a, b, r2 = total_least_squares(x, y)

    assert a is None
    assert b is None
    assert r2 == pytest.approx(1.0)

    # Equation: x - 5 = 0
    # A=1, B=0, C=-5
    assert A == pytest.approx(1.0)
    assert B == pytest.approx(0.0)
    assert C == pytest.approx(-5.0)

def test_total_least_squares_horizontal():
    # Horizontal line at y = -2
    x = np.array([-1, 0, 1, 2])
    y = np.array([-2, -2, -2, -2])

    A, B, C, a, b, r2 = total_least_squares(x, y)

    assert a == pytest.approx(0.0)
    assert b == pytest.approx(-2.0)
    assert r2 == pytest.approx(1.0)

    # Equation: y + 2 = 0
    # Our function enforces A>0 or (A=0, B>0), so B=1, C=2
    assert A == pytest.approx(0.0)
    assert B == pytest.approx(1.0)
    assert C == pytest.approx(2.0)

def test_compute_residuals():
    x = np.array([0, 1, 2])
    y = np.array([1, 2, 3])

    A, B, C, _, _, _ = total_least_squares(x, y)
    res = compute_residuals(x, y, A, B, C)

    assert np.allclose(res, 0)

    # Check off-line points
    x = np.array([0, 1])
    y = np.array([1, 1])  # horizontal line y=1
    A, B, C, _, _, _ = total_least_squares(x, y)
    # A=0, B=1, C=-1

    # Distance of point (0, 3) from y=1 is 2
    res = compute_residuals(np.array([0]), np.array([3]), A, B, C)
    assert np.abs(res[0]) == pytest.approx(2.0)

def test_compute_extreme_projections():
    # Points roughly around y = x
    x = np.array([0, 1, 4, 5])
    y = np.array([0.1, 0.9, 4.1, 4.9])

    A, B, C, _, _, _ = total_least_squares(x, y)
    (x1, y1), (x2, y2) = compute_extreme_projections(x, y, A, B, C)

    # Extremes should be close to (0,0) and (5,5)
    assert x1 == pytest.approx(0, abs=0.2)
    assert y1 == pytest.approx(0, abs=0.2)
    assert x2 == pytest.approx(5, abs=0.2)
    assert y2 == pytest.approx(5, abs=0.2)

    # The projected points MUST lie on the line
    assert (A*x1 + B*y1 + C) == pytest.approx(0, abs=1e-10)
    assert (A*x2 + B*y2 + C) == pytest.approx(0, abs=1e-10)

def test_chi_squared():
    # A perfect line
    x = np.array([0, 1, 2])
    y = np.array([0, 1, 2])
    A, B, C, _, _, _ = total_least_squares(x, y)
    res = compute_residuals(x, y, A, B, C)

    sigma_x = 0.1
    sigma_y = 0.1

    chi2_val, passed = chi_squared_test(res, sigma_x, sigma_y, A, B)
    assert chi2_val == pytest.approx(0.0)
    assert bool(passed) is True

    # Points with noise
    x = np.array([0, 1, 2, 3])
    y = np.array([0.1, 0.9, 2.1, 2.9])
    A, B, C, _, _, _ = total_least_squares(x, y)
    res = compute_residuals(x, y, A, B, C)

    sigma_x = 0.5
    sigma_y = 0.5

    chi2_val, passed = chi_squared_test(res, sigma_x, sigma_y, A, B)
    assert bool(passed) is True
