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

try:
    from ..core.i18n_utils import tr
    from ..core.math_utils import (
        total_least_squares,
        compute_extreme_projections,
        compute_residuals,
        chi_squared_test
    )
except (ImportError, ValueError):
    from core.i18n_utils import tr
    from core.math_utils import (
        total_least_squares,
        compute_extreme_projections,
        compute_residuals,
        chi_squared_test
    )


class BestFitAttributeAlgorithm(QgsProcessingAlgorithm):
    """
    Computes a best fit line grouped by an attribute.
    """
    INPUT = 'INPUT'
    GROUP_FIELD = 'GROUP_FIELD'
    OUTPUT_LINE = 'OUTPUT_LINE'
    OUTPUT_POINTS = 'OUTPUT_POINTS'
    SIGMA_GLOBAL = 'SIGMA_GLOBAL'
    SIGMA_X_FIELD = 'SIGMA_X_FIELD'
    SIGMA_Y_FIELD = 'SIGMA_Y_FIELD'

    def tr(self, string):
        return tr(string, context='TopoALign')

    def createInstance(self):
        return BestFitAttributeAlgorithm()

    def name(self):
        return 'bestfitattribute'

    def displayName(self):
        return self.tr('Best Fit Lines (By Attribute)')

    def group(self):
        return self.tr('Best Fit')

    def groupId(self):
        return 'best_fit'


    def shortHelpString(self):
        return self.tr("Estimates best fitting lines grouped by an attribute using Total Least Squares.")

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input Point Layer'),
                [QgsProcessing.TypeVectorPoint]
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.GROUP_FIELD,
                self.tr('Grouping Field'),
                parentLayerParameterName=self.INPUT,
                type=QgsProcessingParameterField.Any
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
                parentLayerParameterName=self.INPUT,
                defaultValue='sigmaX'
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.SIGMA_Y_FIELD,
                self.tr('Sigma Y Field (Overrides Global)'),
                optional=True,
                type=QgsProcessingParameterField.Numeric,
                parentLayerParameterName=self.INPUT,
                defaultValue='sigmaY'
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_LINE,
                self.tr('Best Fit Lines')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_POINTS,
                self.tr('Points with Residuals')
            )
        )

    def _detect_default_group_field(self, layer):
        """Attempts to find a default grouping field if none specified."""
        defaults = ["linha", "alinhamento", "line", "alignment"]
        field_names = [f.name().lower() for f in layer.fields()]
        for d in defaults:
            if d in field_names:
                # Return original case
                for f in layer.fields():
                    if f.name().lower() == d:
                        return f.name()
        return None

    def _get_line_fields(self, source_fields, group_field_name):
        fields = QgsFields()
        # Find the group field type to copy it
        group_idx = source_fields.indexOf(group_field_name)
        if group_idx != -1:
            fields.append(QgsField(source_fields.field(group_idx)))
        else:
            fields.append(QgsField(group_field_name, QVariant.String))

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

        group_field = self.parameterAsString(parameters, self.GROUP_FIELD, context)

        # If user left it blank or invalid, try to auto-detect
        if not group_field or source.fields().indexOf(group_field) == -1:
            detected = self._detect_default_group_field(source)
            if detected:
                group_field = detected
                feedback.pushInfo(f"Auto-detected grouping field: {group_field}")
            else:
                raise QgsProcessingException("Invalid or missing Grouping Field.")

        sigma_global = self.parameterAsDouble(parameters, self.SIGMA_GLOBAL, context)
        sigma_x_field = self.parameterAsString(parameters, self.SIGMA_X_FIELD, context)
        sigma_y_field = self.parameterAsString(parameters, self.SIGMA_Y_FIELD, context)

        # Output Line Sink
        line_fields = self._get_line_fields(source.fields(), group_field)
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

        # Group features
        grouped_features = {}
        for f in source.getFeatures():
            val = f.attribute(group_field)
            if val is None:
                val = "NULL"
            if val not in grouped_features:
                grouped_features[val] = []
            grouped_features[val].append(f)

        if not grouped_features:
            return {self.OUTPUT_LINE: dest_id_line, self.OUTPUT_POINTS: dest_id_points}

        total_groups = len(grouped_features)

        id_to_res = {}

        for i, (grp_val, features) in enumerate(grouped_features.items()):
            if feedback.isCanceled():
                break

            if len(features) < 2:
                feedback.pushInfo(f"Group '{grp_val}' has less than 2 points. Skipping.")
                continue

            x_coords = []
            y_coords = []
            sigmas_x = []
            sigmas_y = []
            feat_ids = []

            for f in features:
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

            x = np.array(x_coords)
            y = np.array(y_coords)
            sx = np.array(sigmas_x)
            sy = np.array(sigmas_y)

            if len(x) < 2:
                continue

            if len(x) == 2:
                dist = np.sqrt((x[0] - x[1])**2 + (y[0] - y[1])**2)
                if dist < 0.001:
                    feedback.reportError(f"Warning: Group '{grp_val}' points are less than 1mm apart. Line may be unstable.")

            A, B, C, a, b, r2 = total_least_squares(x, y)
            if A is None:
                continue

            residuals = compute_residuals(x, y, A, B, C)
            chi2_stat, passed_95 = chi_squared_test(residuals, sx, sy, A, B)
            p1, p2 = compute_extreme_projections(x, y, A, B, C)

            for fid, res in zip(feat_ids, residuals):
                id_to_res[fid] = res

            line_feat = QgsFeature(line_fields)
            line_geom = QgsGeometry.fromPolylineXY([QgsPointXY(*p1), QgsPointXY(*p2)])
            line_feat.setGeometry(line_geom)
            line_feat.setAttribute(group_field, grp_val)
            line_feat.setAttribute('A', A)
            line_feat.setAttribute('B', B)
            line_feat.setAttribute('C', C)
            line_feat.setAttribute('a_slope', a if a is not None else QVariant())
            line_feat.setAttribute('b_inter', b if b is not None else QVariant())
            line_feat.setAttribute('r2_tls', r2)
            line_feat.setAttribute('chi2_stat', chi2_stat if chi2_stat is not None else QVariant())
            line_feat.setAttribute('chi2_pass', bool(passed_95) if passed_95 is not None else QVariant())

            sink_line.addFeature(line_feat, QgsFeatureSink.FastInsert)

            feedback.setProgress(int((i + 1) / total_groups * 50))

        # Write points
        feat_count = source.featureCount()
        total = feat_count if feat_count > 0 else 1
        for current, f in enumerate(source.getFeatures()):
            if feedback.isCanceled():
                break

            out_f = QgsFeature(points_fields)
            out_f.setGeometry(f.geometry())

            attrs = f.attributes()
            res_val = id_to_res.get(f.id(), None)
            attrs.append(res_val if res_val is not None else QVariant())
            out_f.setAttributes(attrs)

            sink_points.addFeature(out_f, QgsFeatureSink.FastInsert)
            feedback.setProgress(int(50 + (current / total) * 50))

        return {self.OUTPUT_LINE: dest_id_line, self.OUTPUT_POINTS: dest_id_points}
