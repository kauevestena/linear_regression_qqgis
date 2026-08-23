# -*- coding: utf-8 -*-

from qgis.PyQt.QtCore import QCoreApplication, QVariant
from qgis.core import (
    QgsProcessing,
    QgsProcessingAlgorithm,
    QgsProcessingParameterFeatureSource,
    QgsProcessingParameterFeatureSink,
    QgsProcessingParameterNumber,
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
    from ..core.transform_utils import project_points_to_alignment
except (ImportError, ValueError):
    from core.i18n_utils import tr
    from core.transform_utils import project_points_to_alignment



class StationOffsetAlgorithm(QgsProcessingAlgorithm):
    """
    Computes Station (Chainage) and Transverse Offset along a reference alignment line.
    """
    INPUT = 'INPUT'
    ALIGNMENT = 'ALIGNMENT'
    STATION_INTERVAL = 'STATION_INTERVAL'
    START_STATION = 'START_STATION'

    OUTPUT_POINTS = 'OUTPUT_POINTS'
    OUTPUT_PROJECTED = 'OUTPUT_PROJECTED'

    def tr(self, string):
        return tr(string, context='TopoALign')

    def createInstance(self):
        return StationOffsetAlgorithm()

    def name(self):
        return 'stationoffset'

    def displayName(self):
        return self.tr('Station and Offset (Alignment Transformation)')

    def group(self):
        return self.tr('Transform')

    def groupId(self):
        return 'transform'

    def shortHelpString(self):
        return self.tr("Projects points onto a reference alignment line to compute chainage (station) and transverse offset.")

    def initAlgorithm(self, config=None):
        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.INPUT,
                self.tr('Input Point Layer'),
                [QgsProcessing.TypeVectorPoint]
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSource(
                self.ALIGNMENT,
                self.tr('Reference Alignment (Line Layer)'),
                [QgsProcessing.TypeVectorLine]
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.STATION_INTERVAL,
                self.tr('Station Interval (e.g. 20m for 20m stations)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=20.0
            )
        )

        self.addParameter(
            QgsProcessingParameterNumber(
                self.START_STATION,
                self.tr('Start Station Value (m)'),
                type=QgsProcessingParameterNumber.Double,
                defaultValue=0.0
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_POINTS,
                self.tr('Points with Station and Offset')
            )
        )

        self.addParameter(
            QgsProcessingParameterFeatureSink(
                self.OUTPUT_PROJECTED,
                self.tr('Projected Points on Alignment'),
                optional=True
            )
        )

    def processAlgorithm(self, parameters, context, feedback):
        source = self.parameterAsSource(parameters, self.INPUT, context)
        if source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.INPUT))

        alignment_source = self.parameterAsSource(parameters, self.ALIGNMENT, context)
        if alignment_source is None:
            raise QgsProcessingException(self.invalidSourceError(parameters, self.ALIGNMENT))

        interval = self.parameterAsDouble(parameters, self.STATION_INTERVAL, context)
        start_station = self.parameterAsDouble(parameters, self.START_STATION, context)

        # Extract alignment line vertices
        line_vertices = []
        for f in alignment_source.getFeatures():
            geom = f.geometry()
            if not geom or geom.isEmpty():
                continue
            if geom.isMultipart():
                polyline = geom.asMultiPolyline()
                for line in polyline:
                    for pt in line:
                        line_vertices.append((pt.x(), pt.y()))
            else:
                polyline = geom.asPolyline()
                for pt in polyline:
                    line_vertices.append((pt.x(), pt.y()))

        if len(line_vertices) < 2:
            raise QgsProcessingException(
                self.tr("Reference alignment layer has no valid line geometries.")
            )

        # Output Points Sink
        points_fields = QgsFields(source.fields())
        points_fields.append(QgsField('station_m', QVariant.Double))
        points_fields.append(QgsField('station_num', QVariant.Int))
        points_fields.append(QgsField('station_plus', QVariant.Double))
        points_fields.append(QgsField('offset', QVariant.Double))
        points_fields.append(QgsField('proj_x', QVariant.Double))
        points_fields.append(QgsField('proj_y', QVariant.Double))

        (sink_points, dest_id_points) = self.parameterAsSink(
            parameters,
            self.OUTPUT_POINTS,
            context,
            points_fields,
            source.wkbType(),
            source.sourceCrs()
        )

        # Output Projected Points Sink (optional)
        sink_proj = None
        dest_id_proj = None
        if parameters.get(self.OUTPUT_PROJECTED):
            (sink_proj, dest_id_proj) = self.parameterAsSink(
                parameters,
                self.OUTPUT_PROJECTED,
                context,
                points_fields,
                QgsWkbTypes.Point,
                source.sourceCrs()
            )

        # Read all point coordinates
        px_list = []
        py_list = []
        features = []
        for f in source.getFeatures():
            geom = f.geometry()
            if not geom or geom.isEmpty():
                continue
            pt = geom.asPoint()
            px_list.append(pt.x())
            py_list.append(pt.y())
            features.append(f)

        if not px_list:
            return {self.OUTPUT_POINTS: dest_id_points}

        proj_res = project_points_to_alignment(
            np.array(px_list),
            np.array(py_list),
            line_vertices,
            start_station=start_station,
            station_interval=interval
        )

        total_pts = len(features)
        for i, f in enumerate(features):
            if feedback.isCanceled():
                break

            s_m = float(proj_res['station_m'][i])
            s_num = int(proj_res['station_num'][i])
            s_plus = float(proj_res['station_plus'][i])
            off_val = float(proj_res['offset'][i])
            px_val = float(proj_res['proj_x'][i])
            py_val = float(proj_res['proj_y'][i])

            attrs = f.attributes()
            attrs.extend([s_m, s_num, s_plus, off_val, px_val, py_val])

            out_f = QgsFeature(points_fields)
            out_f.setGeometry(f.geometry())
            out_f.setAttributes(attrs)
            sink_points.addFeature(out_f, QgsFeatureSink.FastInsert)

            if sink_proj:
                proj_f = QgsFeature(points_fields)
                proj_f.setGeometry(QgsGeometry.fromPointXY(QgsPointXY(px_val, py_val)))
                proj_f.setAttributes(attrs)
                sink_proj.addFeature(proj_f, QgsFeatureSink.FastInsert)

            feedback.setProgress(int((i + 1) / total_pts * 100))

        results = {self.OUTPUT_POINTS: dest_id_points}
        if dest_id_proj:
            results[self.OUTPUT_PROJECTED] = dest_id_proj

        return results
