# TopoALign - QGIS Processing Plugin

**TopoALign** is a bilingual (English / Portuguese) QGIS Processing Provider Plugin providing topographic alignment analysis and 2D coordinate transformation tools.

Fully compatible with **QGIS 3.28+** and ready for **QGIS 4.x** APIs. Core mathematical calculations are implemented entirely in pure NumPy for optimal speed and reliability.

---

## 🌐 Bilingual Support (i18n)

TopoALign includes full native internationalization for both **English (en)** and **Portuguese (pt-BR / pt)**. The user interface (tool names, groups, parameters, descriptions, log messages) automatically adapts to your QGIS locale settings.

---

## 🛠️ Algorithm Sections & Features

TopoALign organizes tools into two main processing sections:

### 1. Best Fit (`Melhor Ajuste` / `best_fit`)

Tools for estimating best-fitting lines from sets of points using **Total Least Squares (TLS / Orthogonal Distance Regression)**:

*   **Best Fit Line (All/Selection)** (`bestfitselection` / `Linha de Melhor Ajuste (Tudo/Seleção)`)
    *   Computes a single best-fit line for selected points or all points in a layer.
    *   Outputs a Line layer with general ($Ax + By + C = 0$) and slope-intercept ($y = ax + b$) parameters, $R^2_{TLS}$, and $\chi^2$ test metrics.
    *   Outputs a Point layer with calculated orthogonal residuals appended.

*   **Best Fit Lines (By Attribute)** (`bestfitattribute` / `Linhas de Melhor Ajuste (Por Atributo)`)
    *   Groups points by a specified attribute and computes TLS best-fit lines for each group.
    *   Auto-detects common grouping field names (e.g., `linha`, `alinhamento`, `line`, `alignment`).
    *   Outputs aggregated lines and points with residuals.

#### Attributes & Statistics Generated:
*   **A, B, C**: General line coefficients ($Ax + By + C = 0$, normalized $A^2 + B^2 = 1$).
*   **a_slope, b_inter**: Slope and Y-intercept for $y = ax + b$ (`NULL` for vertical lines).
*   **r2_tls**: Total Least Squares $R^2$ calculated from covariance eigenvalues.
*   **chi2_stat**: Chi-squared goodness-of-fit test statistic.
*   **chi2_pass**: Boolean indicating if fit satisfies 95% confidence interval ($\alpha = 0.05$).

---

### 2. Transform (`Transformar` / `transform`)

Coordinate and alignment transformation tools:

*   **2D Helmert Transformation** (`helmert2d` / `Transformação 2D de Helmert`)
    *   Estimates 4-parameter conformal transformation ($T_x, T_y$, scale $s$, rotation $\theta$) from source and target control point pairs using Least Squares, or applies manual parameters.
    *   Transforms input geometries (points, lines, polygons) and computes RMSE and point residuals ($V_x, V_y, V_{dist}$).

*   **Station and Offset (Alignment Transformation)** (`stationoffset` / `Estaqueamento e Afastamento`)
    *   Projects points onto a reference alignment / baseline polyline.
    *   Computes cumulative chainage/station ($s$), station number (e.g., `Estaca`), plus distance ($+m$), and signed transverse offset ($d$, positive for right side, negative for left side).
    *   Outputs points with station attributes and optionally generates projected point geometries along the alignment.

---

## 📦 Installation

Copy or symlink the `topoalign` folder into your QGIS plugin directory:

*   **Linux:** `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/topoalign`
*   **Windows:** `%APPDATA%\QGIS\QGIS3\profiles\default\python\plugins\topoalign`
*   **macOS:** `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/topoalign`

Enable **TopoALign** in QGIS via **Plugins > Manage and Install Plugins... > Installed**.

---

## 🧪 Testing & Development

Run unit tests directly with `pytest`:

```bash
# Run all tests
python3 -m pytest topoalign/tests/

# Recompile translation binaries (.qm)
lrelease topoalign/i18n/*.ts
```

---

## 📄 License
MIT License

