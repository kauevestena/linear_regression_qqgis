# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterField,
    QgsProcessingParameterNumber,
    QgsProcessingParameterBoolean,
    QgsProcessingOutputNumber,
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
    from ..core.transform_utils import (
        helmert_2d_fit,
        helmert_2d_transform
    )
except (ImportError, ValueError):
    from core.i18n_utils import tr
    from core.transform_utils import (
        helmert_2d_fit,
        helmert_2d_transform
    )



class Helmert2DTransformAlgorithm(QgsProcessingAlgorithm):
    """
    Computes 2D Helmert Transformation parameters and transforms layer geometries.
    """
    INPUT = 'INPUT'
    SOURCE_POINTS = 'SOURCE_POINTS'
    SOURCE_ID_FIELD = 'SOURCE_ID_FIELD'
    TARGET_POINTS = 'TARGET_POINTS'
    TARGET_ID_FIELD = 'TARGET_ID_FIELD'

    USE_MANUAL = 'USE_MANUAL'
    MANUAL_TX = 'MANUAL_TX'
    MANUAL_TY = 'MANUAL_TY'
    MANUAL_SCALE = 'MANUAL_SCALE'
    MANUAL_ROTATION = 'MANUAL_ROTATION'

    OUTPUT = 'OUTPUT'
    OUTPUT_RESIDUALS = 'OUTPUT_RESIDUALS'

    OUT_TX = 'OUT_TX'
    OUT_TY = 'OUT_TY'
    OUT_SCALE = 'OUT_SCALE'
    OUT_ROTATION = 'OUT_ROTATION'
    OUT_RMSE = 'OUT_RMSE'

    def tr(self, string):
        return tr(string, context='TopoALign')

    def createInstance(self):
        return Helmert2DTransformAlgorithm()

    def name(self):
        return 'helmert2d'

    def displayName(self):
        return self.tr('2D Helmert Transformation')

    def group(self):
        return self.tr('Transform')

    def groupId(self):
        return 'transform'

    def shortHelpString(self):
        return self.tr("Estimates 4-parameter conformal transformation (Tx, Ty, Scale, Rotation) and transforms layer coordinates.")

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Source Layer (To Transform)'),
                [QgsProcessing.TypeVectorAnyGeometry]
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.SOURCE_POINTS,
                self.tr('Source Control Points'),
                [QgsProcessing.TypeVectorPoint],
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.SOURCE_ID_FIELD,
                self.tr('Source Point ID Field'),
                optional=True,
                parentLayerParameterName=self.SOURCE_POINTS
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.TARGET_POINTS,
                self.tr('Target Control Points'),
                [QgsProcessing.TypeVectorPoint],
                optional=True
            )
        )

        self.addParameter(
            QgsProcessingParameterField(
                self.TARGET_ID_FIELD,
                self.tr('Target Point ID Field'),
                optional=True,
                parentLayerParameterName=self.TARGET_POINTS
            )
        )

        self.addParameter(
            QgsProcessingParameterBoolean(
                self.USE_MANUAL,
                self.tr('Use Manual Parameters'),
                defaultValue=False
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MANUAL_TX,
                self.tr('Manual Tx (Translation X)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MANUAL_TY,
                self.tr('Manual Ty (Translation Y)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MANUAL_SCALE,
                self.tr('Manual Scale Factor (s)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=1.0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.MANUAL_ROTATION,
                self.tr('Manual Rotation (degrees)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT,
                self.tr('Transformed Layer')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_RESIDUALS,
                self.tr('Residuals / Control Point Errors'),
                optional=True
            )
        )

        self.addOutput(QgsProcessingOutputNumber(self.OUT_TX, 'Tx (m)'))
        self.addOutput(QgsProcessingOutputNumber(self.OUT_TY, 'Ty (m)'))
        self.addOutput(QgsProcessingOutputNumber(self.OUT_SCALE, 'Scale Factor'))
        self.addOutput(QgsProcessingOutputNumber(self.OUT_ROTATION, 'Rotation (deg)'))
        self.addOutput(QgsProcessingOutputNumber(self.OUT_RMSE, 'RMSE'))

    def _transform_geom(self, geom, tx, ty, scale, rot_deg):
        """Applies 2D Helmert to all vertices of a QgsGeometry."""
        if not geom or geom.isEmpty():
            return geom

        g = QgsGeometry(geom)
        g.transform(lambda pt: QgsPointXY(*helmert_2d_transform(pt.x(), pt.y(), tx, ty, scale, rot_deg)))
        return g

    def processAlgorithm(self, parameters, context, feedback):
        input_source = self.parameterAsSource(parameters, self.INPUT, context)
        if input_source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        use_manual = self.parameterAsBool(parameters, self.USE_MANUAL, context)

        if use_manual:
            tx = self.parameterAsDouble(parameters, self.MANUAL_TX, context)
            ty = self.parameterAsDouble(parameters, self.MANUAL_TY, context)
            scale = self.parameterAsDouble(parameters, self.MANUAL_SCALE, context)
            rot_deg = self.parameterAsDouble(parameters, self.MANUAL_ROTATION, context)
            rmse = 0.0
            residuals_data = None
        else:
            src_pts_source = self.parameterAsSource(parameters, self.SOURCE_POINTS, context)
            tgt_pts_source = self.parameterAsSource(parameters, self.TARGET_POINTS, context)
            src_id_field = self.parameterAsString(parameters, self.SOURCE_ID_FIELD, context)
            tgt_id_field = self.parameterAsString(parameters, self.TARGET_ID_FIELD, context)

            if src_pts_source is None or tgt_pts_source is None:
                raise QgsProcessingException(
                    self.tr("At least 2 common control points are required for 2D Helmert transformation.")
                )

            # Collect source points
            src_dict = {}
            for i, f in enumerate(src_pts_source.getFeatures()):
                geom = f.geometry()
                if not geom or geom.isEmpty():
                    continue
                pt = geom.asPoint()
                key = str(f.attribute(src_id_field)) if src_id_field else str(i)
                src_dict[key] = (pt.x(), pt.y())

            # Collect target points
            tgt_dict = {}
            for i, f in enumerate(tgt_pts_source.getFeatures()):
                geom = f.geometry()
                if not geom or geom.isEmpty():
                    continue
                pt = geom.asPoint()
                key = str(f.attribute(tgt_id_field)) if tgt_id_field else str(i)
                tgt_dict[key] = (pt.x(), pt.y())

            # Match common keys
            common_keys = [k for k in src_dict if k in tgt_dict]
            if len(common_keys) < 2:
                raise QgsProcessingException(
                    self.tr("At least 2 common control points are required for 2D Helmert transformation.")
                )

            src_x = np.array([src_dict[k][0] for k in common_keys])
            src_y = np.array([src_dict[k][1] for k in common_keys])
            tgt_x = np.array([tgt_dict[k][0] for k in common_keys])
            tgt_y = np.array([tgt_dict[k][1] for k in common_keys])

            fit_res = helmert_2d_fit(src_x, src_y, tgt_x, tgt_y)
            tx = fit_res['tx']
            ty = fit_res['ty']
            scale = fit_res['scale']
            rot_deg = fit_res['rotation_deg']
            rmse = fit_res['rmse']
            residuals_data = (common_keys, tgt_x, tgt_y, fit_res['residuals_x'], fit_res['residuals_y'], fit_res['residuals_dist'])

            feedback.pushInfo(
                self.tr("Helmert 2D Transformation calculated successfully: Tx={tx:.4f}, Ty={ty:.4f}, Scale={scale:.6f}, Rotation={rot_deg:.4f}°, RMSE={rmse:.4f}").format(
                    tx=tx, ty=ty, scale=scale, rot_deg=rot_deg, rmse=rmse
                )
            )

        # Output Layer Sink
        (sink_out, dest_id_out) = self.parameterAsSink(
            parameters,
            self.OUTPUT,
            context,
            input_source.fields(),
            input_source.wkbType(),
            input_source.sourceCrs()
        )

        total_feats = input_source.featureCount()
        total_feats = total_feats if total_feats > 0 else 1

        for i, f in enumerate(input_source.getFeatures()):
            if feedback.isCanceled():
                break
            out_f = QgsFeature(f)
            geom = f.geometry()
            if geom and not geom.isEmpty():
                out_f.setGeometry(self._transform_geom(geom, tx, ty, scale, rot_deg))
            sink_out.addFeature(out_f, QgsFeatureSink.FastInsert)
            feedback.setProgress(int((i + 1) / total_feats * 80))

        # Output Residuals Sink (optional)
        dest_id_res = None
        if residuals_data is not None and parameters.get(self.OUTPUT_RESIDUALS):
            res_fields = QgsFields()
            res_fields.append(QgsField('point_id', QVariant.String))
            res_fields.append(QgsField('vx', QVariant.Double))
            res_fields.append(QgsField('vy', QVariant.Double))
            res_fields.append(QgsField('v_dist', QVariant.Double))

            (sink_res, dest_id_res) = self.parameterAsSink(
                parameters,
                self.OUTPUT_RESIDUALS,
                context,
                res_fields,
                QgsWkbTypes.Point,
                input_source.sourceCrs()
            )

            keys, tx_arr, ty_arr, vx_arr, vy_arr, vd_arr = residuals_data
            for k, x_val, y_val, vx_val, vy_val, vd_val in zip(keys, tx_arr, ty_arr, vx_arr, vy_arr, vd_arr):
                rf = QgsFeature(res_fields)
                rf.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(x_val, y_val)))
                rf.setAttribute('point_id', str(k))
                rf.setAttribute('vx', float(vx_val))
                rf.setAttribute('vy', float(vy_val))
                rf.setAttribute('v_dist', float(vd_val))
                sink_res.addFeature(rf, QgsFeatureSink.FastInsert)

        feedback.setProgress(100)

        results = {
            self.OUTPUT: dest_id_out,
            self.OUT_TX: tx,
            self.OUT_TY: ty,
            self.OUT_SCALE: scale,
            self.OUT_ROTATION: rot_deg,
            self.OUT_RMSE: rmse
        }
        if dest_id_res:
            results[self.OUTPUT_RESIDUALS] = dest_id_res

        return results
