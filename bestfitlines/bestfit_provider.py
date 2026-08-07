# -*- coding: utf-8 -*-

from qgis.core import QgsProcessingProvider
from qgis.PyQt.QtGui import QIcon
import os

class BestFitLinesProvider(QgsProcessingProvider):

    def __init__(self):
        super().__init__()

    def loadAlgorithms(self):
        from .algorithms.bestfit_selection import BestFitSelectionAlgorithm
        from .algorithms.bestfit_attribute import BestFitAttributeAlgorithm
        self.addAlgorithm(BestFitSelectionAlgorithm())
        self.addAlgorithm(BestFitAttributeAlgorithm())

    def id(self):
        return 'bestfit'

    def name(self):
        return self.tr('Best Fit Lines')

    def icon(self):
        return QIcon(os.path.join(os.path.dirname(__file__), 'icon.png'))
