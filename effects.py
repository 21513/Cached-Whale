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

# CompressionDialog: JPEG compression Compression
class CompressionDialog(QDialog):
    def __init__(self, parent, original_image, apply_callback, default_quality=10):
        super().__init__(parent)
        self.setWindowTitle("JPEG Compression")
        self.setFixedSize(320, 180)  # Increased size
        self.original_image = original_image
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
        self._last_pixmap = original_image

        # Debounce timer
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.timeout.connect(self.apply_current)

    def on_slider_changed(self, value):
        self.timer.start(500)

    def apply_current(self):
        value = self.slider.value()
        image = self.original_image.toImage()
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
    def __init__(self, parent, original_image, apply_callback, default_threshold=50):
        super().__init__(parent)
        self.setWindowTitle("Dither Effect")
        self.setFixedSize(320, 180)  # Increased size
        self.original_image = original_image
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
        self._last_pixmap = original_image

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
        original_image = self.original_image
        image = original_image.toImage().convertToFormat(QImage.Format_ARGB32)
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
    def __init__(self, parent, original_image, apply_callback, default_saturation=100):
        super().__init__(parent)
        self.setWindowTitle("Saturation Effect")
        self.setFixedSize(320, 180)
        self.original_image = original_image
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
        self._last_pixmap = original_image

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
        original_image = self.original_image
        image = original_image.toImage().convertToFormat(QImage.Format_ARGB32)
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
    def __init__(self, parent, original_image, apply_callback, default_intensity=50, default_thickness=2):
        super().__init__(parent)
        self.setWindowTitle("Scanlines Effect")
        self.setFixedSize(320, 180)
        self.original_image = original_image
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
        self._last_pixmap = original_image
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
        original_image = self.original_image
        image = original_image.toImage().convertToFormat(QImage.Format_ARGB32)
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
    def __init__(self, parent, original_image, apply_callback, default_amount=20):
        super().__init__(parent)
        self.setWindowTitle("Noise Effect")
        self.setFixedSize(320, 180)
        self.original_image = original_image
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
        self._last_pixmap = original_image
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
        original_image = self.original_image
        image = original_image.toImage().convertToFormat(QImage.Format_ARGB32)
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
    def __init__(self, parent, original_image, apply_callback, default_dot_size=6):
        super().__init__(parent)
        self.setWindowTitle("Halftone Effect")
        self.setFixedSize(340, 180)
        self.original_image = original_image
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
        self._last_pixmap = original_image
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
        original_image = self.original_image
        image = original_image.toImage().convertToFormat(QImage.Format_ARGB32)
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
    def __init__(self, parent, original_image, apply_callback, default_blocksize=8):
        super().__init__(parent)
        self.setWindowTitle("Pixelate Effect")
        self.setFixedSize(320, 180)
        self.original_image = original_image
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
        self._last_pixmap = original_image
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
        original_image = self.original_image
        image = original_image.toImage().convertToFormat(QImage.Format_ARGB32)
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
    def __init__(self, parent, original_image, apply_callback, default_axis=0):
        super().__init__(parent)
        self.setWindowTitle("Pixel Sort Effect")
        self.setFixedSize(340, 260)
        self.original_image = original_image
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
        self._last_pixmap = original_image
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
        if self.original_image:
            img = self.original_image.toImage()
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
        original_image = self.original_image
        image = original_image.toImage().convertToFormat(QImage.Format_ARGB32)
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = np.frombuffer(ptr, np.uint8).reshape((image.height(), image.width(), 4))

        threshold = int(255 * threshold_percent / 100)
        if threshold == 0:
            threshold = -1
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