# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
    QgsProcessingParameterField,
    QgsFeatureSink,
    QgsFeature,
    QgsGeometry,
    QgsPointXY,
    QgsFields,
    QgsField,
    QgsWkbTypes,
    QgsProcessingException
)
import numpy as np

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from core.math_utils import (
    total_least_squares,
    compute_extreme_projections,
    compute_residuals,
    chi_squared_test
)

class BestFitSelectionAlgorithm(QgsProcessingAlgorithm):
    """
    Computes a single best fit line for the selected (or all) points.
    Outputs a line layer and a points layer with residuals.
    """
    INPUT = 'INPUT'
    OUTPUT_LINE = 'OUTPUT_LINE'
    OUTPUT_POINTS = 'OUTPUT_POINTS'
    SIGMA_GLOBAL = 'SIGMA_GLOBAL'
    SIGMA_X_FIELD = 'SIGMA_X_FIELD'
    SIGMA_Y_FIELD = 'SIGMA_Y_FIELD'

    def tr(self, string):
        return QCoreApplication.translate('Processing', string)

    def createInstance(self):
        return BestFitSelectionAlgorithm()

    def name(self):
        return 'bestfitselection'

    def displayName(self):
        return self.tr('Best Fit Line (All/Selection)')

    def group(self):
        return self.tr('Best Fit')

    def groupId(self):
        return 'bestfit'

    def shortHelpString(self):
        return self.tr("Estimates a best fitting line using Total Least Squares for a set of points.")

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input Point Layer'),
                [QgsProcessing.TypeVectorPoint]
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.SIGMA_GLOBAL,
                self.tr('Global Standard Error (Sigma)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=1.0,
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.SIGMA_X_FIELD,
                self.tr('Sigma X Field (Overrides Global)'),
                optional=True,
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName=self.INPUT
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.SIGMA_Y_FIELD,
                self.tr('Sigma Y Field (Overrides Global)'),
                optional=True,
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName=self.INPUT
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_LINE,
                self.tr('Best Fit Line')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_POINTS,
                self.tr('Points with Residuals')
            )
        )

    def _get_line_fields(self):
        fields = QgsFields()
        fields.append(QgsField('A', QVariant.Double))
        fields.append(QgsField('B', QVariant.Double))
        fields.append(QgsField('C', QVariant.Double))
        fields.append(QgsField('a_slope', QVariant.Double))
        fields.append(QgsField('b_inter', QVariant.Double))
        fields.append(QgsField('r2_tls', QVariant.Double))
        fields.append(QgsField('chi2_stat', QVariant.Double))
        fields.append(QgsField('chi2_pass', QVariant.Bool))
        return fields

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        sigma_global = self.parameterAsDouble(parameters, self.SIGMA_GLOBAL, context)
        sigma_x_field = self.parameterAsString(parameters, self.SIGMA_X_FIELD, context)
        sigma_y_field = self.parameterAsString(parameters, self.SIGMA_Y_FIELD, context)

        # Output Line Sink
        line_fields = self._get_line_fields()
        (sink_line, dest_id_line) = self.parameterAsSink(
            parameters,
            self.OUTPUT_LINE,
            context,
            line_fields,
            QgsWkbTypes.LineString,
            source.sourceCrs()
        )

        # Output Points Sink
        points_fields = QgsFields(source.fields())
        points_fields.append(QgsField('residual', QVariant.Double))
        (sink_points, dest_id_points) = self.parameterAsSink(
            parameters,
            self.OUTPUT_POINTS,
            context,
            points_fields,
            source.wkbType(),
            source.sourceCrs()
        )

        features = list(source.getFeatures())
        total = 100.0 / (len(features) if len(features) > 0 else 1)

        if len(features) < 2:
            feedback.pushInfo("Less than 2 points provided. Skipping line generation.")
            return {self.OUTPUT_LINE: dest_id_line, self.OUTPUT_POINTS: dest_id_points}

        x_coords = []
        y_coords = []
        sigmas_x = []
        sigmas_y = []
        feat_ids = []

        for current, f in enumerate(features):
            if feedback.isCanceled():
                break

            geom = f.geometry()
            if not geom or geom.isEmpty():
                continue

            pt = geom.asPoint()
            x_coords.append(pt.x())
            y_coords.append(pt.y())
            feat_ids.append(f.id())

            s_x = sigma_global
            s_y = sigma_global
            if sigma_x_field and f.attribute(sigma_x_field) is not None:
                s_x = float(f.attribute(sigma_x_field))
            if sigma_y_field and f.attribute(sigma_y_field) is not None:
                s_y = float(f.attribute(sigma_y_field))

            sigmas_x.append(s_x)
            sigmas_y.append(s_y)

            feedback.setProgress(int(current * total * 0.5))

        x = np.array(x_coords)
        y = np.array(y_coords)
        sx = np.array(sigmas_x)
        sy = np.array(sigmas_y)

        # Check for points < 1mm apart warning (only if exactly 2 points, per requirements, to avoid O(N^2) memory blowout on large datasets)
        if len(x) == 2:
            dist = np.sqrt((x[0] - x[1])**2 + (y[0] - y[1])**2)
            if dist < 0.001:
                feedback.reportError("Warning: The provided points are less than 1mm apart. The calculated line may be unstable.")

        # Compute Total Least Squares
        A, B, C, a, b, r2 = total_least_squares(x, y)

        if A is None:
            feedback.reportError("Could not calculate TLS (not enough valid points).")
            return {self.OUTPUT_LINE: dest_id_line, self.OUTPUT_POINTS: dest_id_points}

        # Residuals
        residuals = compute_residuals(x, y, A, B, C)

        # Chi Squared
        chi2_stat, passed_95 = chi_squared_test(residuals, sx, sy, A, B)

        # Line Extremes
        p1, p2 = compute_extreme_projections(x, y, A, B, C)

        # Create Line Feature
        line_feat = QgsFeature(line_fields)
        line_geom = QgsGeometry.fromPolylineXY([QgsPointXY(*p1), QgsPointXY(*p2)])
        line_feat.setGeometry(line_geom)
        line_feat.setAttribute('A', A)
        line_feat.setAttribute('B', B)
        line_feat.setAttribute('C', C)
        line_feat.setAttribute('a_slope', a if a is not None else QVariant())
        line_feat.setAttribute('b_inter', b if b is not None else QVariant())
        line_feat.setAttribute('r2_tls', r2)
        line_feat.setAttribute('chi2_stat', chi2_stat if chi2_stat is not None else QVariant())
        line_feat.setAttribute('chi2_pass', bool(passed_95) if passed_95 is not None else QVariant())
        sink_line.addFeature(line_feat, QgsFeatureSink.FastInsert)

        # Write Points with Residuals
        id_to_res = {fid: res for fid, res in zip(feat_ids, residuals)}
        for current, f in enumerate(features):
            if feedback.isCanceled():
                break

            out_f = QgsFeature(points_fields)
            out_f.setGeometry(f.geometry())

            # Copy old attributes
            attrs = f.attributes()
            # Append residual
            res_val = id_to_res.get(f.id(), None)
            attrs.append(res_val if res_val is not None else QVariant())
            out_f.setAttributes(attrs)

            sink_points.addFeature(out_f, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(50 + current * total * 0.5))

        return {self.OUTPUT_LINE: dest_id_line, self.OUTPUT_POINTS: dest_id_points}
