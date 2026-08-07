import numpy as np

def total_least_squares(x, y):
    """
    Computes Total Least Squares (Orthogonal Distance Regression) line.
    Minimizes orthogonal distances from points to the line.

    Returns:
        A, B, C: Coefficients for general line equation Ax + By + C = 0
                 Normalized such that A^2 + B^2 = 1.
        a, b: Coefficients for slope-intercept form y = ax + b. (a=slope, b=intercept)
              Returns (None, None) if the line is vertical.
        r2_tls: TLS R-squared based on eigenvalues.
    """
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    if len(x) < 2:
        return None, None, None, None, None, None

    # Check for points being too close (less than 1mm apart).
    # This will be handled in the QGIS logic for warnings, but we should ensure math doesn't crash.
    # For now, just compute normally unless points are identical.

    x_mean = np.mean(x)
    y_mean = np.mean(y)

    # Center the points
    dx = x - x_mean
    dy = y - y_mean

    # Covariance matrix (using centered data to avoid precision issues)
    # C = (1/N) * X^T * X, but we can just use SVD on the design matrix

    # Stack them into a matrix
    D = np.vstack([dx, dy]).T

    # Perform SVD (Singular Value Decomposition)
    U, S, Vt = np.linalg.svd(D, full_matrices=False)

    # The normal vector is the right singular vector corresponding to the smallest singular value
    # Vt has rows as right singular vectors. Smallest SV is the last row.
    normal_vec = Vt[-1, :]

    A, B = normal_vec

    # General equation: A*x + B*y + C = 0
    # Since it passes through the mean: A*x_mean + B*y_mean + C = 0
    C = -(A * x_mean + B * y_mean)

    # Ensure standard sign orientation for consistency (e.g., A > 0)
    if A < 0 or (A == 0 and B < 0):
        A, B, C = -A, -B, -C

    # Slope-intercept form
    if np.abs(B) > 1e-10:
        a = -A / B
        b = -C / B
    else:
        a = None
        b = None

    # TLS R-squared
    # It represents the proportion of total variance explained by the line.
    # Eigenvalues of covariance matrix are proportional to S^2
    eigenvals = S**2
    if np.sum(eigenvals) == 0:
        r2_tls = 1.0 # Perfect fit if points are identical (though handled upstream)
    else:
        # Largest eigenvalue / sum of eigenvalues
        r2_tls = eigenvals[0] / np.sum(eigenvals)

    return A, B, C, a, b, r2_tls

def compute_residuals(x, y, A, B, C):
    """
    Computes orthogonal residuals (distances) from points to the line Ax + By + C = 0.
    Since A^2 + B^2 = 1 (enforced in our TLS function), the distance is just |Ax + By + C|.
    We preserve the sign to indicate which side of the line the point is on.
    """
    return (A * x + B * y + C) / np.sqrt(A**2 + B**2)

def compute_extreme_projections(x, y, A, B, C):
    """
    Projects the extreme points onto the line to define the line segment.
    """
    # The line direction vector is (-B, A)
    # We parameterize the line passing through origin (or any point on line).
    # Best is to project all points onto the direction vector and find min/max.

    # Direction vector (dx, dy)
    dx_dir = -B
    dy_dir = A

    # Project all points onto the direction vector
    projections = x * dx_dir + y * dy_dir

    min_idx = np.argmin(projections)
    max_idx = np.argmax(projections)

    x_min, y_min = project_point_to_line(x[min_idx], y[min_idx], A, B, C)
    x_max, y_max = project_point_to_line(x[max_idx], y[max_idx], A, B, C)

    return (x_min, y_min), (x_max, y_max)

def project_point_to_line(px, py, A, B, C):
    """
    Projects a point (px, py) onto the line Ax + By + C = 0.
    """
    norm_sq = A**2 + B**2
    x_proj = (B * (B * px - A * py) - A * C) / norm_sq
    y_proj = (A * (-B * px + A * py) - B * C) / norm_sq
    return x_proj, y_proj

def chi_squared_test(residuals, sigma_x, sigma_y, A, B):
    """
    Calculates the chi-squared statistic and the 95% confidence result.

    residuals: orthogonal distances from points to the line.
    sigma_x, sigma_y: global scalar or arrays of same length as residuals.
    A, B: Coefficients of the line.

    Returns:
        chi2_stat: The calculated chi-squared statistic.
        passed_95: Boolean, True if the fit passes the 95% confidence level.
    """
    # The variance of the orthogonal distance for point i is:
    # sigma_d_i^2 = (A * sigma_x_i)^2 + (B * sigma_y_i)^2

    var_d = (A * sigma_x)**2 + (B * sigma_y)**2

    # Chi-squared statistic: sum( residual_i^2 / sigma_d_i^2 )
    chi2_stat = np.sum(residuals**2 / var_d)

    # Degrees of freedom: N points - 2 parameters (slope, intercept)
    dof = len(residuals) - 2

    if dof <= 0:
        return None, None

    # The critical value for 95% confidence.
    # We want to know if the errors are consistent with our error model.
    # Null hypothesis: the line is a good fit given the assumed errors.
    # We reject the null hypothesis if chi2_stat > critical value (usually upper tail).
    # Since we use 95% confidence, alpha = 0.05
    # Since the user requested it strictly in numpy and no scipy, we can implement
    # a simple approximation or interpolation for the critical values of chi-square
    # for alpha=0.05 (95% confidence).

    # We use the Wilson-Hilferty transformation which approximates chi-square to normal distribution
    # For a given degrees of freedom k, chi^2 is approximately:
    # chi^2 ≈ k * (1 - 2/(9k) + Z * sqrt(2/(9k)))^3
    # where Z is the standard normal critical value. For 95% (one-sided upper tail), Z ≈ 1.64485

    if dof <= 0:
        return None, None

    Z = 1.64485
    critical_value = dof * (1 - 2/(9*dof) + Z * np.sqrt(2/(9*dof)))**3

    passed_95 = chi2_stat <= critical_value

    return chi2_stat, passed_95
