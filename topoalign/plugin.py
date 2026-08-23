# -*- coding: utf-8 -*-

from qgis.core import QgsApplication
from .bestfit_provider import BestFitLinesProvider

class BestFitLinesPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None

    def initProcessing(self):
        self.provider = BestFitLinesProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
