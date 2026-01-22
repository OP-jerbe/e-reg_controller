from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QLineEdit


class ScrollingLineEdit(QLineEdit):
    def wheelEvent(self, event: QWheelEvent) -> None:
        # Only process if there is a number and the box has focus
        text = self.text().strip()
        if not text.isdigit():
            super().wheelEvent(event)
            return

        # 1. Determine the "magnitude" based on cursor position
        # Position is index from the left.
        # Example: "1234" -> Length 4.
        # Cursor at end (pos 4) -> 4 - 4 = 0 -> 10^0 = 1
        # Cursor between 2 and 3 (pos 2) -> 4 - 2 = 2 -> 10^1 = 10 (Correction needed for 0-indexing)

        pos: int = self.cursorPosition()
        length = len(text)

        # Calculate power of 10. We use max/min to stay within string bounds.
        # If cursor is at the very end, power is 0 (units).
        # If cursor is one to the left, power is 1 (tens), etc.
        power = max(0, length - pos)
        if power == 4:
            power = 0
        magnitude = 10**power

        # 2. Determine direction (angleDelta.y > 0 is scroll up)
        current_val = int(text)
        if event.angleDelta().y() > 0:
            new_val = current_val + magnitude
        else:
            new_val = current_val - magnitude

        # 3. Apply bounds
        new_val = max(0, min(3033, new_val))

        # 4. Update text and maintain cursor position
        self.setText(str(new_val))
        self.setCursorPosition(pos)

        # Trigger the editingFinished signal manually so logic updates
        self.editingFinished.emit()

        event.accept()
