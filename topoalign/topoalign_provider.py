# -*- coding: utf-8 -*-

import os
from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
try:
    from .core.i18n_utils import tr
except (ImportError, ValueError):
    from core.i18n_utils import tr


class TopoALignProvider(QgsProcessingProvider):

    def __init__(self):
        super().__init__()

    def tr(self, string):
        return tr(string, context="TopoALign")

    def loadAlgorithms(self):
        # Best Fit section algorithms
        try:
            from .algorithms.bestfit_selection import BestFitSelectionAlgorithm
            from .algorithms.bestfit_attribute import BestFitAttributeAlgorithm
            from .algorithms.transform_helmert import Helmert2DTransformAlgorithm
            from .algorithms.transform_station_offset import StationOffsetAlgorithm
        except (ImportError, ValueError):
            from algorithms.bestfit_selection import BestFitSelectionAlgorithm
            from algorithms.bestfit_attribute import BestFitAttributeAlgorithm
            from algorithms.transform_helmert import Helmert2DTransformAlgorithm
            from algorithms.transform_station_offset import StationOffsetAlgorithm


        self.addAlgorithm(BestFitSelectionAlgorithm())
        self.addAlgorithm(BestFitAttributeAlgorithm())
        self.addAlgorithm(Helmert2DTransformAlgorithm())
        self.addAlgorithm(StationOffsetAlgorithm())

    def id(self):
        return 'topoalign'

    def name(self):
        return self.tr('TopoALign')

    def icon(self):
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        if os.path.exists(icon_path):
            return QIcon(icon_path)
        return super().icon()
