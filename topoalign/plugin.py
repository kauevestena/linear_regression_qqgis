# -*- coding: utf-8 -*-

import os
from qgis.core import QgsApplication
from qgis.PyQt.QtCore import QCoreApplication, QTranslator, QLocale, QSettings
from .topoalign_provider import TopoALignProvider


class TopoALignPlugin:
    def __init__(self, iface):
        self.iface = iface
        self.provider = None
        self.translator = None

        # Setup internationalization
        self._init_translation()

    def _init_translation(self):
        override_locale = QSettings().value("locale/overrideFlag", False, type=bool)
        if override_locale:
            locale_name = str(QSettings().value("locale/userLocale", ""))
        else:
            locale_name = QLocale.system().name()

        # Candidates to try: 'pt_BR', 'pt', etc.
        candidates = [locale_name]
        if "_" in locale_name:
            candidates.append(locale_name.split("_")[0])

        i18n_dir = os.path.join(os.path.dirname(__file__), "i18n")
        for loc in candidates:
            qm_path = os.path.join(i18n_dir, f"topoalign_{loc}.qm")
            if os.path.exists(qm_path):
                self.translator = QTranslator()
                if self.translator.load(qm_path):
                    QCoreApplication.installTranslator(self.translator)
                    break

    def initProcessing(self):
        self.provider = TopoALignProvider()
        QgsApplication.processingRegistry().addProvider(self.provider)

    def initGui(self):
        self.initProcessing()

    def unload(self):
        if self.provider:
            QgsApplication.processingRegistry().removeProvider(self.provider)
            self.provider = None
        if self.translator:
            QCoreApplication.removeTranslator(self.translator)
            self.translator = None

