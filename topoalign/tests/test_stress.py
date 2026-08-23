import numpy as np
import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.math_utils import total_least_squares

def test_stress_total_least_squares():
    np.random.seed(42)  # For reproducibility

    # Generate 1000 random a and b coefficients from 1 to 5
    num_tests = 1000
    a_coeffs = np.random.uniform(1, 5, num_tests)
    b_coeffs = np.random.uniform(1, 5, num_tests)

    # Base x values: 100 points, starting at -50, incrementing by 5
    base_x = np.arange(-50, -50 + 100 * 5, 5)

    for i in range(num_tests):
        a = a_coeffs[i]
        b = b_coeffs[i]

        # Base y values
        base_y = a * base_x + b

        # The line is a*x - y + b = 0 -> A = a, B = -1, C = b
        # To project orthogonal noise, the normal vector to the line is (a, -1)
        # We need to normalize it
        norm = np.sqrt(a**2 + (-1)**2)
        nx = a / norm
        ny = -1 / norm

        # Generate normally distributed random fluctuations (standard deviation = 2)
        noise = np.random.normal(loc=0.0, scale=2.0, size=100)

        # Apply noise orthogonally
        noisy_x = base_x + noise * nx
        noisy_y = base_y + noise * ny

        A_out, B_out, C_out, a_out, b_out, r2_tls = total_least_squares(noisy_x, noisy_y)

        # As no degenerated cases are expected with a>0 and b>0, these should compute successfully
        assert A_out is not None
        assert B_out is not None
        assert C_out is not None
        assert a_out is not None
        assert b_out is not None
        assert r2_tls is not None
