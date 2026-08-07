# Best Fit Lines - QGIS Processing Plugin

A QGIS Processing Provider Plugin to estimate best fitting lines from a set of XY points using **Total Least Squares (Orthogonal Distance Regression)**.

This plugin is designed to be fully compatible with QGIS 3.28+ and ready for QGIS 4 APIs. The core mathematical logic is implemented entirely in NumPy.

## Features

This plugin provides a processing provider ("Best Fit") with two algorithms:

1. **Best Fit Line (All/Selection)**
   - Computes a single best fit line for the selected points (or all points in a layer).
   - Returns a Line layer with mathematical attributes.
   - Returns a new Point layer with the calculated orthogonal `residual` appended.

2. **Best Fit Lines (By Attribute)**
   - Groups points by a specified attribute and computes a best fit line for each group.
   - Automatically detects common attribute names (e.g., `linha`, `alinhamento`, `line`, `alignment`).
   - Returns a Line layer containing all the computed lines.
   - Returns a Point layer with residuals for all points.

## Attributes and Output

For each line generated, the following attributes are populated:

*   **A, B, C**: Coefficients for the general line equation $Ax + By + C = 0$. (Normalized such that $A^2 + B^2 = 1$).
*   **a_slope, b_inter**: Coefficients for the slope-intercept form $y = ax + b$. `NULL` if the line is perfectly vertical.
*   **r2_tls**: R-squared statistic specifically calculated for TLS using eigenvalues.
*   **chi2_stat**: The Chi-squared statistic based on the orthogonal residuals and provided standard errors.
*   **chi2_pass**: Boolean indicating if the fit passes the 95% confidence interval for the Chi-squared test.

### Standard Errors

Users can provide standard errors via:
1.  **Global Standard Error (Sigma)**: A single value applied to all points.
2.  **Sigma X / Sigma Y Fields**: Field names in the point layer to use for individual standard errors (overrides the global sigma).

## Installation

You can install this plugin manually in QGIS by copying the `bestfitlines` folder into your QGIS profiles plugin directory:

*   **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\`
*   **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
*   **macOS:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`

## Development and Testing

The core math utilities are built strictly on NumPy and are designed to be tested independently of QGIS.

### Running Tests

Dependencies for testing:
```bash
pip install numpy pytest
```

Run the tests from the root of the repository:
```bash
python3 -m pytest bestfitlines/tests/
```

## License
MIT License
