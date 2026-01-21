from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy


class ScalableImageLabel(QLabel):
    def __init__(self, pixmap: QPixmap | None = None) -> None:
        super().__init__()
        self.setMinimumSize(1, 1)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.original_pixmap = pixmap
        if pixmap:
            self.setPixmap(pixmap)

    def update_pixmap(self, pixmap: QPixmap) -> None:
        self.original_pixmap = pixmap
        self._set_scaled_pixmap()

    def _set_scaled_pixmap(self) -> None:
        if self.original_pixmap and not self.original_pixmap.isNull():
            # Get the size of the label itself
            size = self.size()

            # Scale the pixmap.
            scaled_pix = self.original_pixmap.scaled(
                size,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.setPixmap(scaled_pix)

    def resizeEvent(self, event) -> None:
        self._set_scaled_pixmap()
        super().resizeEvent(event)
