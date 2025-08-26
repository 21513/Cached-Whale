import sys
import os
import json
import numpy as np
# PyQt5 imports for GUI components and image manipulation
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QFileDialog, QVBoxLayout, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QHBoxLayout, QLabel, QStackedLayout,
    QMenuBar, QMenu, QAction, QSplitter, QDialog, QFormLayout, QLineEdit,
    QCheckBox, QDialogButtonBox, QSlider, QComboBox,
)
from PyQt5.QtGui import QPixmap, QMouseEvent, QWheelEvent, QImage, QColor, QFontDatabase, QFont, QPainter, QTransform
from PyQt5 import QtGui  # For QIntValidator used in HalftoneDialog
from PyQt5.QtCore import Qt, pyqtSignal, QBuffer, QIODevice, QEvent, QTimer
import random
from scipy.ndimage import gaussian_filter

# Constants for recent file management
MAX_RECENT = 5
RECENT_FILE = os.path.join(os.getenv("APPDATA"), "ManipulateRecent.json")

# Application-wide stylesheet for a retro dark look
DARK_RETRO_STYLE = """
QWidget {
    background-color: #010101;
    font-family: 'Minecraft';
    font-size: 16px;
    color: #ffffff;
}
QGraphicsView {
    background-image:
}
QLabel {
    color: #ffffff;
}
QPushButton {
    background-color: #010101;
    border: 2px solid #888888;
    padding: 8px;
    font-size: 16px;
    color: #ffffff;
    margin-bottom: 8px;
    min-width: 140px;
}
QPushButton:hover {
    background-color: #202020;
    border: 2px solid #ffffff;
}
QMenuBar {
    background-color: #010101;
}
QMenuBar:hover {
    background-color: #101010;
}
QMenuBar:hover {
    background-color: #101010;
}
QMenu {
    background-color: #010101;
    color: #ffffff;
}
Qmenu::item:hover {
    background-color: #202020;
}
QMenu:hover {
    background-color: #202020;
}
"""

# --- CanvasView: Custom QGraphicsView for displaying and interacting with images ---
from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPainter, QPixmap, QBrush, QColor
from PyQt5.QtWidgets import QGraphicsView

class CanvasView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setRenderHints(self.renderHints() | QPainter.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.zoom_factor = 1.25
        self.middle_mouse_pressed = False
        self.last_mouse_pos = None

        self.setSceneRect(-16384, -16384, 32768, 32768)

        # Create checkerboard tile
        tile_size = 64
        pixmap = QPixmap(tile_size * 2, tile_size * 2)
        pixmap.fill(QColor(19, 19, 19))
        painter = QPainter(pixmap)
        painter.fillRect(0, 0, tile_size, tile_size, QColor(1, 1, 1))
        painter.fillRect(tile_size, tile_size, tile_size, tile_size, QColor(1, 1, 1))
        painter.end()
        self.checkerboard_brush = QBrush(pixmap)

    def drawBackground(self, painter: QPainter, rect: QRectF):
        # Draw the checkerboard pattern first
        painter.fillRect(rect, self.checkerboard_brush)
        super().drawBackground(painter, rect)

    def wheelEvent(self, event):
        if event.angleDelta().y() > 0:
            self.scale(self.zoom_factor, self.zoom_factor)
        else:
            self.scale(1 / self.zoom_factor, 1 / self.zoom_factor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.middle_mouse_pressed = True
            self.setCursor(Qt.ClosedHandCursor)
            self.last_mouse_pos = event.pos()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.middle_mouse_pressed and self.last_mouse_pos is not None:
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()

            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MiddleButton:
            self.middle_mouse_pressed = False
            self.setCursor(Qt.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)

# --- StartPage: Initial landing page with recent images and import button ---
class StartPage(QWidget):
    def __init__(self, recent_images, import_callback, recent_callback):
        super().__init__()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        # Title
        title = QLabel("Manipulate")
        title.setStyleSheet("font-family: 'LCDMono'; font-size: 64px; margin-bottom: 12px;")
        layout.addWidget(title, alignment=Qt.AlignLeft)
        # Import button
        import_btn = QPushButton("Import Image")
        import_btn.setStyleSheet("margin-bottom: 16px; min-width: 160px; padding: 8px;")
        import_btn.clicked.connect(import_callback)
        layout.addWidget(import_btn, alignment=Qt.AlignLeft)
        # Recent images list
        recent_label = QLabel("Recent Images:")
        recent_label.setStyleSheet("margin-bottom: 8px;")
        layout.addWidget(recent_label, alignment=Qt.AlignLeft)
        self.recent_buttons = []
        for path in recent_images:
            btn = QPushButton(path)
            btn.setStyleSheet("text-align: left; min-width: 320px; margin-bottom: 4px; padding: 8px;")
            btn.clicked.connect(lambda _, p=path: recent_callback(p))
            layout.addWidget(btn, alignment=Qt.AlignLeft)
            self.recent_buttons.append(btn)
        self.setLayout(layout)

    # Update recent images list
    def update_recents(self, recent_images, recent_callback):
        for btn in self.recent_buttons:
            btn.setParent(None)
        self.recent_buttons.clear()
        for path in recent_images:
            btn = QPushButton(path)
            btn.setStyleSheet("text-align: left; min-width: 320px; margin-bottom: 4px; padding: 8px;")
            btn.clicked.connect(lambda _, p=path: recent_callback(p))
            self.layout().addWidget(btn, alignment=Qt.AlignLeft)
            self.recent_buttons.append(btn)

# --- ResizeDialog: Dialog for resizing images with aspect ratio lock ---
class ResizeDialog(QDialog):
    resized = pyqtSignal(int, int)
    def __init__(self, orig_w, orig_h):
        super().__init__()
        self.setWindowTitle("Resize Image")
        self.setFixedSize(260, 120)
        self.orig_w = orig_w
        self.orig_h = orig_h
        self.aspect = orig_w / orig_h if orig_h != 0 else 1
        layout = QFormLayout()
        self.width_edit = QLineEdit(str(orig_w))
        self.height_edit = QLineEdit(str(orig_h))
        self.lock_aspect = QCheckBox("Lock Aspect Ratio")
        self.lock_aspect.setChecked(True)
        layout.addRow("Width:", self.width_edit)
        layout.addRow("Height:", self.height_edit)
        layout.addRow(self.lock_aspect)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addRow(buttons)
        self.setLayout(layout)

        # Aspect ratio logic
        self.width_edit.textChanged.connect(self.update_height)
        self.height_edit.textChanged.connect(self.update_width)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

    def update_height(self, text):
        if self.lock_aspect.isChecked():
            try:
                w = int(text)
                h = int(round(w / self.aspect))
                self.height_edit.blockSignals(True)
                self.height_edit.setText(str(h))
                self.height_edit.blockSignals(False)
            except Exception:
                pass

    def update_width(self, text):
        if self.lock_aspect.isChecked():
            try:
                h = int(text)
                w = int(round(h * self.aspect))
                self.width_edit.blockSignals(True)
                self.width_edit.setText(str(w))
                self.width_edit.blockSignals(False)
            except Exception:
                pass

    def get_size(self):
        try:
            w = int(self.width_edit.text())
            h = int(self.height_edit.text())
            return w, h
        except Exception:
            return self.orig_w, self.orig_h

# --- Effect Dialogs ---
# Each dialog below allows the user to preview and apply a specific image effect.
# All dialogs use sliders/input boxes for parameters, show current value, and preview on open.

# CompressionDialog: JPEG compression Compression
class CompressionDialog(QDialog):
    def __init__(self, parent, orig_pixmap, apply_callback, default_quality=10):
        super().__init__(parent)
        self.setWindowTitle("JPEG Compression")
        self.setFixedSize(320, 180)  # Increased size
        self.orig_pixmap = orig_pixmap
        self.apply_callback = apply_callback
        layout = QVBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(100)
        self.slider.setValue(default_quality)
        layout.addWidget(QLabel("JPEG Quality (1-100):"))
        layout.addWidget(self.slider)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self.slider.valueChanged.connect(self.on_slider_changed)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._last_pixmap = orig_pixmap

        # Debounce timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.apply_current)

    def on_slider_changed(self, value):
        self.timer.start(500)

    def apply_current(self):
        value = self.slider.value()
        image = self.orig_pixmap.toImage()
        buffer = QBuffer()
        buffer.open(QIODevice.ReadWrite)
        image.save(buffer, "JPEG", quality=value)
        ba = buffer.data()
        qimg = QImage.fromData(ba, "JPEG")
        pixmap = QPixmap.fromImage(qimg)
        self._last_pixmap = pixmap
        self.apply_callback(pixmap)

    def get_pixmap(self):
        return self._last_pixmap

# DitherDialog: Dithering effect (threshold as percentage)
class DitherDialog(QDialog):
    def __init__(self, parent, orig_pixmap, apply_callback, default_threshold=50):
        super().__init__(parent)
        self.setWindowTitle("Dither Effect")
        self.setFixedSize(320, 180)  # Increased size
        self.orig_pixmap = orig_pixmap
        self.apply_callback = apply_callback
        layout = QVBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(100)
        self.slider.setValue(default_threshold)
        self.threshold_label = QLabel(f"Threshold: {default_threshold}%")
        layout.addWidget(self.threshold_label)
        layout.addWidget(self.slider)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self.slider.valueChanged.connect(self.on_slider_changed)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._last_pixmap = orig_pixmap

        # Debounce timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.apply_current)

        # Preview on open
        self.apply_current()

    def on_slider_changed(self, value):
        self.threshold_label.setText(f"Threshold: {self.slider.value()}%")
        self.timer.start(500)

    def apply_current(self):
        value = self.slider.value()
        orig_pixmap = self.orig_pixmap
        image = orig_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = np.frombuffer(ptr, np.uint8).reshape((image.height(), image.width(), 4))
        gray = (0.299 * arr[..., 2] + 0.587 * arr[..., 1] + 0.114 * arr[..., 0]).astype(np.int16)
        threshold = int(255 * value / 100)
        dithered = np.zeros_like(gray)
        err = np.zeros_like(gray, dtype=np.int16)
        h, w = gray.shape
        for y in range(h):
            old_row = gray[y] + err[y]
            new_row = np.where(old_row < threshold, 0, 255)
            dithered[y] = new_row
            quant_error = old_row - new_row
            if y + 1 < h:
                err[y + 1, :-1] += (quant_error[1:] * 3) // 16
                err[y + 1] += (quant_error * 5) // 16
                err[y + 1, 1:] += (quant_error[:-1] * 1) // 16
            if y < h and w > 1:
                err[y, 1:] += (quant_error[:-1] * 7) // 16
        arr[..., 0] = dithered.clip(0, 255)
        arr[..., 1] = dithered.clip(0, 255)
        arr[..., 2] = dithered.clip(0, 255)
        pixmap = QPixmap.fromImage(image)
        self._last_pixmap = pixmap
        self.apply_callback(pixmap)

    def get_pixmap(self):
        return self._last_pixmap

# SaturationDialog: Adjust image saturation (0-200%)
class SaturationDialog(QDialog):
    def __init__(self, parent, orig_pixmap, apply_callback, default_saturation=100):
        super().__init__(parent)
        self.setWindowTitle("Saturation Effect")
        self.setFixedSize(320, 180)
        self.orig_pixmap = orig_pixmap
        self.apply_callback = apply_callback
        layout = QVBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(200)
        self.slider.setValue(default_saturation)
        self.sat_label = QLabel(f"Saturation: {default_saturation}%")
        layout.addWidget(self.sat_label)
        layout.addWidget(self.slider)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self.slider.valueChanged.connect(self.on_slider_changed)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._last_pixmap = orig_pixmap

        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.apply_current)

        # Preview on open
        self.apply_current()

    def on_slider_changed(self, value):
        self.sat_label.setText(f"Saturation: {self.slider.value()}%")
        self.timer.start(500)

    def apply_current(self):
        value = self.slider.value()
        orig_pixmap = self.orig_pixmap
        image = orig_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        # Try GPU-accelerated saturation adjustment using QPainter and ColorMatrix
        try:
            factor = value / 100.0
            result_img = QImage(image.size(), QImage.Format_ARGB32)
            result_img.fill(Qt.transparent)
            painter = QPainter(result_img)
            # Color matrix for saturation
            s = factor
            # Luminance coefficients
            lr, lg, lb = 0.299, 0.587, 0.114
            matrix = [
                lr*(1-s)+s, lg*(1-s),     lb*(1-s),     0, 0,
                lr*(1-s),   lg*(1-s)+s,   lb*(1-s),     0, 0,
                lr*(1-s),   lg*(1-s),     lb*(1-s)+s,   0, 0,
                0,          0,            0,            1, 0
            ]
            color_transform = QTransform(
                matrix[0], matrix[1], matrix[2],
                matrix[5], matrix[6], matrix[7],
                matrix[10], matrix[11], matrix[12]
            )
            # QPainter doesn't support color matrix directly, so fallback to numpy if needed
            painter.drawImage(0, 0, image)
            painter.end()
            arr = np.frombuffer(result_img.bits(), np.uint8).reshape((result_img.height(), result_img.width(), 4))
            # Apply saturation using numpy for each pixel
            r = arr[..., 2].astype(np.float32)
            g = arr[..., 1].astype(np.float32)
            b = arr[..., 0].astype(np.float32)
            gray = lr * r + lg * g + lb * b
            arr[..., 2] = np.clip(gray + s * (r - gray), 0, 255).astype(np.uint8)
            arr[..., 1] = np.clip(gray + s * (g - gray), 0, 255).astype(np.uint8)
            arr[..., 0] = np.clip(gray + s * (b - gray), 0, 255).astype(np.uint8)
            pixmap = QPixmap.fromImage(result_img)
        except Exception:
            # Fallback to numpy only
            ptr = image.bits()
            ptr.setsize(image.byteCount())
            arr = np.frombuffer(ptr, np.uint8).reshape((image.height(), image.width(), 4))
            r = arr[..., 2].astype(np.float32)
            g = arr[..., 1].astype(np.float32)
            b = arr[..., 0].astype(np.float32)
            gray = 0.299 * r + 0.587 * g + 0.114 * b
            s = value / 100.0
            arr[..., 2] = np.clip(gray + s * (r - gray), 0, 255).astype(np.uint8)
            arr[..., 1] = np.clip(gray + s * (g - gray), 0, 255).astype(np.uint8)
            arr[..., 0] = np.clip(gray + s * (b - gray), 0, 255).astype(np.uint8)
            pixmap = QPixmap.fromImage(image)
        self._last_pixmap = pixmap
        self.apply_callback(pixmap)

    def get_pixmap(self):
        return self._last_pixmap

# ScanlinesDialog: Draw black scanlines over image
class ScanlinesDialog(QDialog):
    def __init__(self, parent, orig_pixmap, apply_callback, default_intensity=50, default_thickness=2):
        super().__init__(parent)
        self.setWindowTitle("Scanlines Effect")
        self.setFixedSize(320, 180)
        self.orig_pixmap = orig_pixmap
        self.apply_callback = apply_callback
        layout = QVBoxLayout()
        self.intensity_slider = QSlider(Qt.Horizontal)
        self.intensity_slider.setMinimum(0)
        self.intensity_slider.setMaximum(100)
        self.intensity_slider.setValue(default_intensity)
        self.intensity_label = QLabel(f"Intensity: {default_intensity}%")
        layout.addWidget(self.intensity_label)
        layout.addWidget(self.intensity_slider)
        self.thickness_slider = QSlider(Qt.Horizontal)
        self.thickness_slider.setMinimum(1)
        self.thickness_slider.setMaximum(10)
        self.thickness_slider.setValue(default_thickness)
        self.thickness_label = QLabel(f"Thickness: {default_thickness}px")
        layout.addWidget(self.thickness_label)
        layout.addWidget(self.thickness_slider)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self.intensity_slider.valueChanged.connect(self.on_slider_changed)
        self.thickness_slider.valueChanged.connect(self.on_slider_changed)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._last_pixmap = orig_pixmap
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.apply_current)
        # Preview on open
        self.apply_current()

    def on_slider_changed(self, value):
        self.intensity_label.setText(f"Intensity: {self.intensity_slider.value()}%")
        self.thickness_label.setText(f"Thickness: {self.thickness_slider.value()}px")
        self.timer.start(300)

    def apply_current(self):
        intensity = self.intensity_slider.value()
        thickness = self.thickness_slider.value()
        orig_pixmap = self.orig_pixmap
        image = orig_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        # Only add scanlines (draw black lines)
        painter = QPainter(image)
        pen = QColor(0, 0, 0, int(255 * intensity / 100))
        painter.setPen(pen)
        for y in range(0, image.height(), thickness * 2):
            for t in range(thickness):
                if y + t < image.height():
                    painter.drawLine(0, y + t, image.width(), y + t)
        painter.end()
        pixmap = QPixmap.fromImage(image)
        self._last_pixmap = pixmap
        self.apply_callback(pixmap)

    def get_pixmap(self):
        return self._last_pixmap

# --- Noise Effect (was Film Grain) ---
class NoiseDialog(QDialog):
    def __init__(self, parent, orig_pixmap, apply_callback, default_amount=20):
        super().__init__(parent)
        self.setWindowTitle("Noise Effect")
        self.setFixedSize(320, 180)
        self.orig_pixmap = orig_pixmap
        self.apply_callback = apply_callback
        layout = QVBoxLayout()
        self.amount_slider = QSlider(Qt.Horizontal)
        self.amount_slider.setMinimum(0)
        self.amount_slider.setMaximum(100)
        self.amount_slider.setValue(default_amount)
        self.amount_label = QLabel(f"Noise Amount: {default_amount}%")
        layout.addWidget(self.amount_label)
        layout.addWidget(self.amount_slider)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self.amount_slider.valueChanged.connect(self.on_slider_changed)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._last_pixmap = orig_pixmap
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.apply_current)
        # Preview on open
        self.apply_current()

    def on_slider_changed(self, value):
        self.amount_label.setText(f"Noise Amount: {self.amount_slider.value()}%")
        self.timer.start(300)

    def apply_current(self):
        amount = self.amount_slider.value()
        orig_pixmap = self.orig_pixmap
        image = orig_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = np.frombuffer(ptr, np.uint8).reshape((image.height(), image.width(), 4))
        max_noise = int(128 * amount / 100)
        noise = np.random.randint(-max_noise, max_noise+1, arr[..., 0:3].shape, dtype=np.int16)
        arr[..., 0:3] = np.clip(arr[..., 0:3] + noise, 0, 255).astype(np.uint8)
        pixmap = QPixmap.fromImage(image)
        self._last_pixmap = pixmap
        self.apply_callback(pixmap)

    def get_pixmap(self):
        return self._last_pixmap

# --- Halftone Effect ---
class HalftoneDialog(QDialog):
    def __init__(self, parent, orig_pixmap, apply_callback, default_dot_size=6):
        super().__init__(parent)
        self.setWindowTitle("Halftone Effect")
        self.setFixedSize(340, 180)
        self.orig_pixmap = orig_pixmap
        self.apply_callback = apply_callback
        layout = QVBoxLayout()
        self.dot_edit = QLineEdit(str(default_dot_size))
        self.dot_edit.setValidator(QtGui.QIntValidator(2, 512))
        self.dot_label = QLabel(f"Dot Size: {default_dot_size}px")
        layout.addWidget(self.dot_label)
        layout.addWidget(self.dot_edit)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self.dot_edit.textChanged.connect(self.on_edit_changed)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._last_pixmap = orig_pixmap
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.apply_current)
        # Preview on open
        self.apply_current()

    def on_edit_changed(self, value):
        try:
            val = int(value)
            self.dot_label.setText(f"Dot Size: {val}px")
        except Exception:
            self.dot_label.setText("Dot Size: ?px")
        self.timer.start(300)

    def apply_current(self):
        try:
            dot_size = int(self.dot_edit.text())
        except Exception:
            dot_size = 6
        orig_pixmap = self.orig_pixmap
        image = orig_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        result_img = QImage(image.size(), QImage.Format_ARGB32)
        result_img.fill(Qt.white)
        painter = QPainter(result_img)
        painter.setRenderHint(QPainter.Antialiasing, True)
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = np.frombuffer(ptr, np.uint8).reshape((image.height(), image.width(), 4))
        h, w = arr.shape[:2]
        for y in range(0, h, dot_size):
            for x in range(0, w, dot_size):
                block = arr[y:y+dot_size, x:x+dot_size]
                avg = block[..., 0:3].mean(axis=(0,1))
                gray = int(avg.mean())
                radius = int((gray / 255) * (dot_size // 2))
                cy, cx = y + dot_size // 2, x + dot_size // 2
                color = QColor(gray, gray, gray)
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(cx-radius, cy-radius, radius*2, radius*2)
        painter.end()
        pixmap = QPixmap.fromImage(result_img)
        self._last_pixmap = pixmap
        self.apply_callback(pixmap)

    def get_pixmap(self):
        return self._last_pixmap

# --- Pixelate Effect ---
class PixelateDialog(QDialog):
    def __init__(self, parent, orig_pixmap, apply_callback, default_blocksize=8):
        super().__init__(parent)
        self.setWindowTitle("Pixelate Effect")
        self.setFixedSize(320, 180)
        self.orig_pixmap = orig_pixmap
        self.apply_callback = apply_callback
        layout = QVBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(2)
        self.slider.setMaximum(128)
        self.slider.setValue(default_blocksize)
        self.block_label = QLabel(f"Pixel Size: {default_blocksize}px")
        layout.addWidget(self.block_label)
        layout.addWidget(self.slider)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self.slider.valueChanged.connect(self.on_slider_changed)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._last_pixmap = orig_pixmap
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.apply_current)
        # Preview on open
        self.apply_current()

    def on_slider_changed(self, value):
        self.block_label.setText(f"Pixel Size: {self.slider.value()}px")
        self.timer.start(500)

    def apply_current(self):
        blocksize = self.slider.value()
        orig_pixmap = self.orig_pixmap
        image = orig_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = np.frombuffer(ptr, np.uint8).reshape((image.height(), image.width(), 4))
        h, w = arr.shape[:2]
        for y in range(0, h, blocksize):
            for x in range(0, w, blocksize):
                block = arr[y:y+blocksize, x:x+blocksize]
                avg = block.mean(axis=(0,1)).astype(np.uint8)
                block[...] = avg
        pixmap = QPixmap.fromImage(image)
        self._last_pixmap = pixmap
        self.apply_callback(pixmap)

    def get_pixmap(self):
        return self._last_pixmap

# PixelSortDialog: Sort pixels by brightness, direction and offset, threshold as percentage
class PixelSortDialog(QDialog):
    def __init__(self, parent, orig_pixmap, apply_callback, default_axis=0):
        super().__init__(parent)
        self.setWindowTitle("Pixel Sort Effect")
        self.setFixedSize(340, 260)
        self.orig_pixmap = orig_pixmap
        self.apply_callback = apply_callback
        layout = QVBoxLayout()

        # Dropdown for sort direction
        self.direction_combo = QComboBox()
        self.direction_combo.addItems([
            "Horizontal Left", "Horizontal Right", "Vertical Top", "Vertical Bottom"
        ])
        self.direction_combo.setStyleSheet("padding: 8px;")
        layout.addWidget(QLabel("Sort Direction:"))
        layout.addWidget(self.direction_combo)

        # Slider for brightness threshold (percentage)
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(0)
        self.threshold_slider.setMaximum(100)
        self.threshold_slider.setValue(0)
        self.threshold_label = QLabel("Brightness Threshold: 0%")
        layout.addWidget(self.threshold_label)
        layout.addWidget(self.threshold_slider)

        # Slider for offset position
        self.offset_slider = QSlider(Qt.Horizontal)
        self.offset_slider.setMinimum(0)
        self.offset_slider.setMaximum(0)  # will be set dynamically
        self.offset_slider.setValue(0)
        self.offset_label = QLabel("Offset Position: 0px")
        layout.addWidget(self.offset_label)
        layout.addWidget(self.offset_slider)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        self.setLayout(layout)

        self.direction_combo.currentIndexChanged.connect(self.on_direction_changed)
        self.threshold_slider.valueChanged.connect(self.on_slider_changed)
        self.offset_slider.valueChanged.connect(self.on_slider_changed)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._last_pixmap = orig_pixmap
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.apply_current)

        # Set offset slider range based on image size and direction
        self._update_offset_slider()
        # Preview on open
        self.apply_current()

    def on_direction_changed(self, idx):
        self._update_offset_slider()
        self.on_slider_changed(idx)

    def _update_offset_slider(self):
        if self.orig_pixmap:
            img = self.orig_pixmap.toImage()
            if self.direction_combo.currentIndex() in [0, 1]:  # Horizontal
                self.offset_slider.setMaximum(img.width() - 1)
            else:  # Vertical
                self.offset_slider.setMaximum(img.height() - 1)
            self.offset_slider.setValue(0)

    def on_slider_changed(self, value):
        self.threshold_label.setText(f"Brightness Threshold: {self.threshold_slider.value()}%")
        self.offset_label.setText(f"Offset Position: {self.offset_slider.value()}px")
        self.timer.start(300)

    def apply_current(self):
        direction = self.direction_combo.currentIndex()
        threshold_percent = self.threshold_slider.value()
        offset = self.offset_slider.value()
        orig_pixmap = self.orig_pixmap
        image = orig_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = np.frombuffer(ptr, np.uint8).reshape((image.height(), image.width(), 4))

        threshold = int(255 * threshold_percent / 100)
        if direction in [0, 1]:  # Horizontal
            for y in range(arr.shape[0]):
                row = arr[y, :, 0:3]
                brightness = row.mean(axis=1)
                mask = (brightness > threshold) & (np.arange(row.shape[0]) >= offset)
                if direction == 0:  # Left
                    sorted_row = row.copy()
                    sorted_row[mask] = row[mask][np.argsort(brightness[mask])]
                else:  # Right
                    sorted_row = row.copy()
                    sorted_row[mask] = row[mask][np.argsort(brightness[mask])[::-1]]
                arr[y, :, 0:3] = sorted_row
        else:  # Vertical
            for x in range(arr.shape[1]):
                col = arr[:, x, 0:3]
                brightness = col.mean(axis=1)
                mask = (brightness > threshold) & (np.arange(col.shape[0]) >= offset)
                if direction == 2:  # Top
                    sorted_col = col.copy()
                    sorted_col[mask] = col[mask][np.argsort(brightness[mask])]
                else:  # Bottom
                    sorted_col = col.copy()
                    sorted_col[mask] = col[mask][np.argsort(brightness[mask])[::-1]]
                arr[:, x, 0:3] = sorted_col
        pixmap = QPixmap.fromImage(image)
        self._last_pixmap = pixmap
        self.apply_callback(pixmap)

    def get_pixmap(self):
        return self._last_pixmap

# --- ImageEditor: Main application window and logic ---
class ImageEditor(QWidget):
    def __init__(self):
        super().__init__()
        # Set up main window, font, and style
        self.setWindowTitle("Image Editor with Canvas")
        self.resize(900, 600)
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "lcd.TTF")
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                self.setFont(QFont(families[0], 12))
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "minecraft.ttf")
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                self.setFont(QFont(families[0], 12))
        self.setStyleSheet(DARK_RETRO_STYLE)

        # Recent images management
        self.recent_images = self.load_recent_images()

        # Graphics scene and canvas for image display
        self.scene = QGraphicsScene()
        self.canvas = CanvasView()
        self.canvas.setScene(self.scene)
        self.image_item = None
        self.current_image_path = None
        self.inverted_pixmap = None

        # Undo/Redo stacks for image edits
        self.undo_stack = []
        self.redo_stack = []

        # Stacked layout: start page and canvas page
        self.stacked_layout = QStackedLayout()
        self.start_page = StartPage(
            self.recent_images,
            self.load_image_dialog,
            self.load_recent_image
        )

        # Sidebar with effect/action buttons
        self.sidebar = QWidget()
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setAlignment(Qt.AlignTop)
        # Add buttons for all effects and actions
        self.invert_btn = QPushButton("Invert Colors")
        self.invert_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.invert_btn.clicked.connect(self.invert_image)
        self.dither_btn = QPushButton("Dither Effect")
        self.dither_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.dither_btn.clicked.connect(self.dither_dialog)
        self.compression_btn = QPushButton("JPEG Compression")
        self.compression_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.compression_btn.clicked.connect(self.compression_dialog)
        self.grayscale_btn = QPushButton("Saturation")
        self.grayscale_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.grayscale_btn.clicked.connect(self.saturation_dialog)
        self.pixelate_btn = QPushButton("Pixelate")
        self.pixelate_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.pixelate_btn.clicked.connect(self.pixelate_dialog)
        self.save_image_btn = QPushButton("Save Image As")
        self.save_image_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.save_image_btn.clicked.connect(self.save_image_as)
        self.save_image_btn.setEnabled(False)
        sidebar_layout.addWidget(self.invert_btn)
        sidebar_layout.addWidget(self.dither_btn)
        sidebar_layout.addWidget(self.compression_btn)
        sidebar_layout.addWidget(self.grayscale_btn)
        sidebar_layout.addWidget(self.pixelate_btn)
        sidebar_layout.addWidget(self.save_image_btn)
        self.sidebar.setLayout(sidebar_layout)
        self.sidebar.setStyleSheet("background-color: #222; border-left: 2px solid #444;")

        # --- Add these lines for new effects ---
        self.scanlines_btn = QPushButton("Scanlines")
        self.scanlines_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.scanlines_btn.clicked.connect(self.scanlines_dialog)
        sidebar_layout.addWidget(self.scanlines_btn)

        self.filmgrain_btn = QPushButton("Noise")
        self.filmgrain_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.filmgrain_btn.clicked.connect(self.noise_dialog)
        sidebar_layout.addWidget(self.filmgrain_btn)

        self.halftone_btn = QPushButton("Halftone")
        self.halftone_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.halftone_btn.clicked.connect(self.halftone_dialog)
        sidebar_layout.addWidget(self.halftone_btn)

        self.pixelsort_btn = QPushButton("Pixel Sort")
        self.pixelsort_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.pixelsort_btn.clicked.connect(self.pixelsort_dialog)
        sidebar_layout.addWidget(self.pixelsort_btn)
        # --- End new effect buttons ---

        # Canvas page with sidebar
        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.canvas)
        self.splitter.addWidget(self.sidebar)
        self.splitter.setSizes([600, 200])
        canvas_page = QWidget()
        canvas_layout = QHBoxLayout()
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(self.splitter)
        canvas_page.setLayout(canvas_layout)

        self.stacked_layout.addWidget(self.start_page)
        self.stacked_layout.addWidget(canvas_page)

        # Menu bar setup (File/Edit)
        self.menu_bar = QMenuBar(self)
        file_menu = QMenu("&File", self)
        # ...add actions for open, close, undo, redo, recent, exit...
        open_action = QAction("&Open Image...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.load_image_dialog)
        file_menu.addAction(open_action)

        close_action = QAction("&Close Image", self)
        close_action.setShortcut("Ctrl+W")
        close_action.triggered.connect(self.close_image)
        file_menu.addAction(close_action)

        undo_action = QAction("&Undo", self)
        undo_action.setShortcut("Ctrl+Z")
        undo_action.triggered.connect(self.undo)
        file_menu.addAction(undo_action)

        redo_action = QAction("&Redo", self)
        redo_action.setShortcut("Ctrl+Shift+Z")
        redo_action.triggered.connect(self.redo)
        file_menu.addAction(redo_action)

        self.recent_menu = QMenu("Open &Recent", self)
        self.update_recent_menu()
        file_menu.addMenu(self.recent_menu)

        clear_recents_action = QAction("Clear &Recents", self)
        clear_recents_action.setShortcut("Ctrl+Shift+C")
        clear_recents_action.triggered.connect(self.clear_recents)
        file_menu.addAction(clear_recents_action)

        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(QApplication.instance().quit)
        file_menu.addAction(exit_action)

        self.menu_bar.addMenu(file_menu)

        # Edit menu (resize)
        edit_menu = QMenu("&Edit", self)
        resize_action = QAction("&Resize Image...", self)
        resize_action.triggered.connect(self.open_resize_dialog)
        edit_menu.addAction(resize_action)
        self.menu_bar.addMenu(edit_menu)

        # Keyboard shortcut for zoom (Z)
        self.shortcut_zoom = QAction(self)
        self.shortcut_zoom.setShortcut("Z")
        self.shortcut_zoom.triggered.connect(self.zoom_100)
        self.addAction(self.shortcut_zoom)

        # Main layout
        main_layout = QVBoxLayout()
        main_layout.setMenuBar(self.menu_bar)
        main_layout.addLayout(self.stacked_layout)
        self.setLayout(main_layout)
        self.show_start_page()

    # --- Image loading, saving, undo/redo, and effect application methods ---
    # Each method is commented to explain its purpose and logic

    def close_image(self):
        # Clear current image and reset state
        self.scene.clear()
        self.image_item = None
        self.current_image_path = None
        self.inverted_pixmap = None
        self.save_image_btn.setEnabled(False)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.show_start_page()

    def clear_recents(self):
        # Clear recent images list
        self.recent_images = []
        self.save_recent_images()
        self.start_page.update_recents(self.recent_images, self.load_recent_image)
        self.update_recent_menu()

    def update_recent_menu(self):
        # Update recent images menu
        self.recent_menu.clear()
        for path in self.recent_images:
            action = QAction(path, self)
            action.triggered.connect(lambda checked, p=path: self.load_recent_image(p))
            self.recent_menu.addAction(action)
        if not self.recent_images:
            no_recent_action = QAction("(No recent images)", self)
            no_recent_action.setEnabled(False)
            self.recent_menu.addAction(no_recent_action)

    def show_start_page(self):
        # Show start page
        self.stacked_layout.setCurrentIndex(0)

    def show_canvas(self):
        # Show canvas page
        self.stacked_layout.setCurrentIndex(1)

    def add_to_recent(self, path):
        # Add image path to recent list
        if path in self.recent_images:
            self.recent_images.remove(path)
        self.recent_images.insert(0, path)
        if len(self.recent_images) > MAX_RECENT:
            self.recent_images = self.recent_images[:MAX_RECENT]
        self.save_recent_images()
        self.start_page.update_recents(self.recent_images, self.load_recent_image)
        self.update_recent_menu()

    def load_image_dialog(self):
        # Open file dialog to load image
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "",
                                                   "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            self.load_image(file_path)

    def load_recent_image(self, path):
        # Load image from recent list
        self.load_image(path)

    def load_image(self, file_path):
        # Load image and display on canvas
        pixmap = QPixmap(file_path)
        if not pixmap.isNull():
            self.scene.clear()
            self.image_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.image_item)
            self.scene.setSceneRect(self.image_item.boundingRect())
            self.canvas.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.canvas.centerOn(self.image_item)
            self.add_to_recent(file_path)
            self.current_image_path = file_path
            self.inverted_pixmap = None
            self.save_image_btn.setEnabled(True)
            self.undo_stack.clear()
            self.redo_stack.clear()
            self.push_undo(pixmap)
            self.show_canvas()

    def push_undo(self, pixmap):
        # Add current image to undo stack
        self.undo_stack.append(pixmap.copy())
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
        # Undo last image edit
        if len(self.undo_stack) > 1:
            current = self.undo_stack.pop()
            self.redo_stack.append(current)
            pixmap = self.undo_stack[-1]
            self.scene.clear()
            self.image_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.image_item)
            self.scene.setSceneRect(self.image_item.boundingRect())
            self.canvas.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.canvas.centerOn(self.image_item)
            self.save_image_btn.setEnabled(True)

    def redo(self):
        # Redo last undone edit
        if self.redo_stack:
            pixmap = self.redo_stack.pop()
            self.push_undo(pixmap)
            self.scene.clear()
            self.image_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(self.image_item)
            self.scene.setSceneRect(self.image_item.boundingRect())
            self.canvas.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.canvas.centerOn(self.image_item)
            self.save_image_btn.setEnabled(True)

    def invert_image(self):
        # Invert image colors
        if self.image_item:
            orig_pixmap = self.image_item.pixmap()
            image = orig_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
            ptr = image.bits()
            ptr.setsize(image.byteCount())
            arr = np.frombuffer(ptr, np.uint8).reshape((image.height(), image.width(), 4))
            arr[..., 0:3] = 255 - arr[..., 0:3]  # Invert RGB
            new_pixmap = QPixmap.fromImage(image)
            self.scene.clear()
            self.image_item = QGraphicsPixmapItem(new_pixmap)
            self.scene.addItem(self.image_item)
            self.scene.setSceneRect(self.image_item.boundingRect())
            self.canvas.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.canvas.centerOn(self.image_item)
            self.save_image_btn.setEnabled(True)
            self.push_undo(new_pixmap)

    def save_image_as(self):
        # Save current image to file
        if self.image_item:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Image As", "",
                                                       "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;Bitmap Image (*.bmp)")
            if file_path:
                self.image_item.pixmap().save(file_path)

    def open_resize_dialog(self):
        # Open resize dialog
        if self.image_item:
            img = self.image_item.pixmap().toImage()
            orig_w = img.width()
            orig_h = img.height()
            dlg = ResizeDialog(orig_w, orig_h)
            if dlg.exec_() == QDialog.Accepted:
                w, h = dlg.get_size()
                self.resize_image(w, h)

    def resize_image(self, w, h):
        # Resize image to given dimensions
        if self.image_item:
            orig_pixmap = self.image_item.pixmap()
            scaled = orig_pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.scene.clear()
            self.image_item = QGraphicsPixmapItem(scaled)
            self.scene.addItem(self.image_item)
            self.scene.setSceneRect(self.image_item.boundingRect())
            self.canvas.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.canvas.centerOn(self.image_item)
            self.save_image_btn.setEnabled(True)
            self.push_undo(scaled)

    def zoom_100(self):
        # Fit image to canvas window, like initial import
        if self.image_item:
            self.canvas.resetTransform()
            self.canvas.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.canvas.centerOn(self.image_item)

    # --- Effect dialog launchers ---
    # Each launches the corresponding dialog and handles undo stack

    def compression_dialog(self):
        if self.image_item:
            orig_pixmap = self.image_item.pixmap()
            dlg = CompressionDialog(self, orig_pixmap, self.set_canvas_pixmap, default_quality=10)
            result = dlg.exec_()
            if result == QDialog.Accepted:
                pixmap = dlg.get_pixmap()
                self.push_undo(pixmap)
            else:
                self.set_canvas_pixmap(orig_pixmap)

    def dither_dialog(self):
        if self.image_item:
            orig_pixmap = self.image_item.pixmap()
            dlg = DitherDialog(self, orig_pixmap, self.set_canvas_pixmap, default_threshold=128)
            result = dlg.exec_()
            if result == QDialog.Accepted:
                pixmap = dlg.get_pixmap()
                self.push_undo(pixmap)
            else:
                self.set_canvas_pixmap(orig_pixmap)

    def saturation_dialog(self):
        if self.image_item:
            orig_pixmap = self.image_item.pixmap()
            dlg = SaturationDialog(self, orig_pixmap, self.set_canvas_pixmap, default_saturation=100)
            result = dlg.exec_()
            if result == QDialog.Accepted:
                pixmap = dlg.get_pixmap()
                self.push_undo(pixmap)
            else:
                self.set_canvas_pixmap(orig_pixmap)

    def pixelate_dialog(self):
        if self.image_item:
            orig_pixmap = self.image_item.pixmap()
            dlg = PixelateDialog(self, orig_pixmap, self.set_canvas_pixmap, default_blocksize=8)
            result = dlg.exec_()
            if result == QDialog.Accepted:
                pixmap = dlg.get_pixmap()
                self.push_undo(pixmap)
            else:
                self.set_canvas_pixmap(orig_pixmap)

    def scanlines_dialog(self):
        if self.image_item:
            orig_pixmap = self.image_item.pixmap()
            dlg = ScanlinesDialog(self, orig_pixmap, self.set_canvas_pixmap)
            result = dlg.exec_()
            if result == QDialog.Accepted:
                pixmap = dlg.get_pixmap()
                self.push_undo(pixmap)
            else:
                self.set_canvas_pixmap(orig_pixmap)

    def noise_dialog(self):
        if self.image_item:
            orig_pixmap = self.image_item.pixmap()
            dlg = NoiseDialog(self, orig_pixmap, self.set_canvas_pixmap)
            result = dlg.exec_()
            if result == QDialog.Accepted:
                pixmap = dlg.get_pixmap()
                self.push_undo(pixmap)
            else:
                self.set_canvas_pixmap(orig_pixmap)

    def halftone_dialog(self):
        if self.image_item:
            orig_pixmap = self.image_item.pixmap()
            dlg = HalftoneDialog(self, orig_pixmap, self.set_canvas_pixmap)
            result = dlg.exec_()
            if result == QDialog.Accepted:
                pixmap = dlg.get_pixmap()
                self.push_undo(pixmap)
            else:
                self.set_canvas_pixmap(orig_pixmap)

    def pixelsort_dialog(self):
        if self.image_item:
            orig_pixmap = self.image_item.pixmap()
            dlg = PixelSortDialog(self, orig_pixmap, self.set_canvas_pixmap)
            result = dlg.exec_()
            if result == QDialog.Accepted:
                pixmap = dlg.get_pixmap()
                self.push_undo(pixmap)
            else:
                self.set_canvas_pixmap(orig_pixmap)

    def set_canvas_pixmap(self, pixmap):
        # Set image on canvas and enable save
        self.scene.clear()
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.image_item)
        self.scene.setSceneRect(self.image_item.boundingRect())
        self.canvas.fitInView(self.image_item, Qt.KeepAspectRatio)
        self.canvas.centerOn(self.image_item)
        self.save_image_btn.setEnabled(True)

    def load_recent_images(self):
        # Load recent images from file
        if os.path.exists(RECENT_FILE):
            try:
                with open(RECENT_FILE, "r") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass
        return []

    def save_recent_images(self):
        # Save recent images to file
        try:
            with open(RECENT_FILE, "w") as f:
                json.dump(self.recent_images, f)
        except Exception:
            pass

# --- Application entry point ---
if __name__ == "__main__":
    # Create and run the application
    app = QApplication(sys.argv)
    editor = ImageEditor()
    editor.show()
    sys.exit(app.exec_())