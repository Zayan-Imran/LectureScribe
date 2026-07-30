"""Application bootstrap for LectureScribe."""

from __future__ import annotations

import logging
import sys

from PySide6.QtWidgets import QApplication

from lecturescribe import __app_name__
from lecturescribe.logging_config import configure_logging
from lecturescribe.ui.main_window import MainWindow

logger = logging.getLogger(__name__)


def run() -> int:
    """Start the Qt application event loop."""
    configure_logging()
    logger.info("Starting %s", __app_name__)

    app = QApplication(sys.argv)
    app.setApplicationName(__app_name__)
    app.setOrganizationName("LectureScribe")

    window = MainWindow()
    window.show()

    return app.exec()
