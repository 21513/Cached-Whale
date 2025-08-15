import sys
import os
import json
import numpy as np
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QPushButton,
    QFileDialog,
    QVBoxLayout,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QHBoxLayout,
    QLabel,
    QStackedLayout,
    QMenuBar,
    QMenu,
    QAction,
    QSplitter,
    QDialog,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QDialogButtonBox,
    QSlider,
)
from PyQt5.QtGui import QPixmap, QMouseEvent, QWheelEvent, QImage, QColor, QFontDatabase, QFont
from PyQt5.QtCore import Qt, pyqtSignal, QBuffer, QIODevice, QEvent

MAX_RECENT = 5
RECENT_FILE = os.path.join(os.getenv("APPDATA"), "ManipulateRecent.json")

DARK_RETRO_STYLE = """
QWidget {
    background-color: #181818;
    font-family: 'lcd', 'Tahoma', 'Verdana', 'Arial', sans-serif;
    color: #e0e0e0;
}
QLabel {
    color: #e0e0e0;
}
QPushButton {
    background-color: #232323;
    border: 2px solid #444;
    border-radius: 4px;
    padding: 8px;
    font-size: 14px;
    color: #e0e0e0;
    margin-bottom: 8px;
    min-width: 140px;
}
QPushButton:hover {
    background-color: #333;
    border: 2px solid #888;
}
QMenuBar {
    background-color: #222;
    border-bottom: 2px solid #444;
}
QMenu {
    background-color: #232323;
    color: #e0e0e0;
}
"""

class CanvasView(QGraphicsView):
    def __init__(self):
        super().__init__()
        self.setRenderHints(self.renderHints() | Qt.SmoothTransformation)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.zoom_factor = 1.25
        self.middle_mouse_pressed = False
        self.last_mouse_pos = None

    def wheelEvent(self, event: QWheelEvent):
        if event.angleDelta().y() > 0:
            self.scale(self.zoom_factor, self.zoom_factor)
        else:
            self.scale(1 / self.zoom_factor, 1 / self.zoom_factor)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            self.middle_mouse_pressed = True
            self.setCursor(Qt.ClosedHandCursor)
            self.last_mouse_pos = event.pos()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.middle_mouse_pressed and self.last_mouse_pos is not None:
            delta = event.pos() - self.last_mouse_pos
            self.last_mouse_pos = event.pos()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - delta.x())
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - delta.y())
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        if event.button() == Qt.MiddleButton:
            self.middle_mouse_pressed = False
            self.setCursor(Qt.ArrowCursor)
        else:
            super().mouseReleaseEvent(event)

class StartPage(QWidget):
    def __init__(self, recent_images, import_callback, recent_callback):
        super().__init__()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        title = QLabel("Manipulate")
        title.setStyleSheet("font-size: 28px; font-weight: bold; margin-bottom: 12px;")
        layout.addWidget(title, alignment=Qt.AlignLeft)
        import_btn = QPushButton("Import Image")
        import_btn.setStyleSheet("margin-bottom: 16px; min-width: 160px; padding: 8px;")
        import_btn.clicked.connect(import_callback)
        layout.addWidget(import_btn, alignment=Qt.AlignLeft)
        recent_label = QLabel("Recent Images:")
        recent_label.setStyleSheet("font-size: 16px; margin-bottom: 8px;")
        layout.addWidget(recent_label, alignment=Qt.AlignLeft)
        self.recent_buttons = []
        for path in recent_images:
            btn = QPushButton(path)
            btn.setStyleSheet("text-align: left; min-width: 320px; margin-bottom: 4px; padding: 8px;")
            btn.clicked.connect(lambda _, p=path: recent_callback(p))
            layout.addWidget(btn, alignment=Qt.AlignLeft)
            self.recent_buttons.append(btn)
        self.setLayout(layout)

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

class CompressionDialog(QDialog):
    def __init__(self, parent, orig_pixmap, apply_callback, default_quality=10):
        super().__init__(parent)
        self.setWindowTitle("Compression Artefacts")
        self.setFixedSize(260, 140)
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
        self.slider.valueChanged.connect(self.apply_current)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._last_pixmap = orig_pixmap

    def apply_current(self, value):
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

class DitherDialog(QDialog):
    def __init__(self, parent, orig_pixmap, apply_callback, default_threshold=128):
        super().__init__(parent)
        self.setWindowTitle("Dither Effect")
        self.setFixedSize(260, 140)
        self.orig_pixmap = orig_pixmap
        self.apply_callback = apply_callback
        layout = QVBoxLayout()
        self.slider = QSlider(Qt.Horizontal)
        self.slider.setMinimum(0)
        self.slider.setMaximum(255)
        self.slider.setValue(default_threshold)
        layout.addWidget(QLabel("Threshold (0-255):"))
        layout.addWidget(self.slider)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        self.setLayout(layout)
        self.slider.valueChanged.connect(self.apply_current)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._last_pixmap = orig_pixmap

    def apply_current(self, value):
        orig_pixmap = self.orig_pixmap
        image = orig_pixmap.toImage().convertToFormat(QImage.Format_ARGB32)
        ptr = image.bits()
        ptr.setsize(image.byteCount())
        arr = np.frombuffer(ptr, np.uint8).reshape((image.height(), image.width(), 4))
        gray = (0.299 * arr[..., 2] + 0.587 * arr[..., 1] + 0.114 * arr[..., 0]).astype(np.int16)
        dithered = np.zeros_like(gray)
        err = np.zeros_like(gray, dtype=np.int16)
        h, w = gray.shape
        for y in range(h):
            old_row = gray[y] + err[y]
            new_row = np.where(old_row < value, 0, 255)
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

class ImageEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Editor with Canvas")
        self.resize(800, 600)

        # Load retro font from /fonts/
        font_path = os.path.join(os.path.dirname(__file__), "fonts", "lcd.ttf")
        if os.path.exists(font_path):
            font_id = QFontDatabase.addApplicationFont(font_path)
            families = QFontDatabase.applicationFontFamilies(font_id)
            if families:
                self.setFont(QFont(families[0], 12))
        self.setStyleSheet(DARK_RETRO_STYLE)

        self.recent_images = self.load_recent_images()

        self.scene = QGraphicsScene()
        self.canvas = CanvasView()
        self.canvas.setScene(self.scene)
        self.image_item = None
        self.current_image_path = None
        self.inverted_pixmap = None

        # Undo/Redo stacks
        self.undo_stack = []
        self.redo_stack = []

        self.stacked_layout = QStackedLayout()
        self.start_page = StartPage(
            self.recent_images,
            self.load_image_dialog,
            self.load_recent_image
        )

        # Sidebar for image actions
        self.sidebar = QWidget()
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setAlignment(Qt.AlignTop)
        self.invert_btn = QPushButton("Invert Colors")
        self.invert_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.invert_btn.clicked.connect(self.invert_image)
        self.dither_btn = QPushButton("Dither Effect")
        self.dither_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.dither_btn.clicked.connect(self.dither_dialog)
        self.compression_btn = QPushButton("Compression Artefacts")
        self.compression_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.compression_btn.clicked.connect(self.compression_dialog)
        self.save_image_btn = QPushButton("Save Image As")
        self.save_image_btn.setStyleSheet("padding: 8px; margin-bottom: 8px;")
        self.save_image_btn.clicked.connect(self.save_image_as)
        self.save_image_btn.setEnabled(False)
        sidebar_layout.addWidget(self.invert_btn)
        sidebar_layout.addWidget(self.dither_btn)
        sidebar_layout.addWidget(self.compression_btn)
        sidebar_layout.addWidget(self.save_image_btn)
        self.sidebar.setLayout(sidebar_layout)
        self.sidebar.setStyleSheet("background-color: #222; border-left: 2px solid #444;")

        # Canvas page with resizable sidebar
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

        # Menu Bar
        self.menu_bar = QMenuBar(self)
        self.menu_bar.setStyleSheet("font-size: 14px;")
        file_menu = QMenu("&File", self)

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

        # Edit Menu
        edit_menu = QMenu("&Edit", self)
        resize_action = QAction("&Resize Image...", self)
        resize_action.triggered.connect(self.open_resize_dialog)
        edit_menu.addAction(resize_action)
        self.menu_bar.addMenu(edit_menu)

        # Add shortcut for Z (zoom 100%)
        self.shortcut_zoom = QAction(self)
        self.shortcut_zoom.setShortcut("Z")
        self.shortcut_zoom.triggered.connect(self.zoom_100)
        self.addAction(self.shortcut_zoom)

        # Layout
        main_layout = QVBoxLayout()
        main_layout.setMenuBar(self.menu_bar)
        main_layout.addLayout(self.stacked_layout)
        self.setLayout(main_layout)
        self.show_start_page()

    def close_image(self):
        self.scene.clear()
        self.image_item = None
        self.current_image_path = None
        self.inverted_pixmap = None
        self.save_image_btn.setEnabled(False)
        self.undo_stack.clear()
        self.redo_stack.clear()
        self.show_start_page()

    def clear_recents(self):
        self.recent_images = []
        self.save_recent_images()
        self.start_page.update_recents(self.recent_images, self.load_recent_image)
        self.update_recent_menu()

    def update_recent_menu(self):
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
        self.stacked_layout.setCurrentIndex(0)

    def show_canvas(self):
        self.stacked_layout.setCurrentIndex(1)

    def add_to_recent(self, path):
        if path in self.recent_images:
            self.recent_images.remove(path)
        self.recent_images.insert(0, path)
        if len(self.recent_images) > MAX_RECENT:
            self.recent_images = self.recent_images[:MAX_RECENT]
        self.save_recent_images()
        self.start_page.update_recents(self.recent_images, self.load_recent_image)
        self.update_recent_menu()

    def load_image_dialog(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "",
                                                   "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            self.load_image(file_path)

    def load_recent_image(self, path):
        self.load_image(path)

    def load_image(self, file_path):
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
        self.undo_stack.append(pixmap.copy())
        if len(self.undo_stack) > 20:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def undo(self):
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
        if self.image_item:
            file_path, _ = QFileDialog.getSaveFileName(self, "Save Image As", "",
                                                       "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;Bitmap Image (*.bmp)")
            if file_path:
                self.image_item.pixmap().save(file_path)

    def open_resize_dialog(self):
        if self.image_item:
            img = self.image_item.pixmap().toImage()
            orig_w = img.width()
            orig_h = img.height()
            dlg = ResizeDialog(orig_w, orig_h)
            if dlg.exec_() == QDialog.Accepted:
                w, h = dlg.get_size()
                self.resize_image(w, h)

    def resize_image(self, w, h):
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
        if self.image_item:
            self.canvas.resetTransform()
            self.canvas.setSceneRect(self.image_item.boundingRect())
            self.canvas.centerOn(self.image_item)

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

    def set_canvas_pixmap(self, pixmap):
        self.scene.clear()
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.image_item)
        self.scene.setSceneRect(self.image_item.boundingRect())
        self.canvas.fitInView(self.image_item, Qt.KeepAspectRatio)
        self.canvas.centerOn(self.image_item)
        self.save_image_btn.setEnabled(True)

    def load_recent_images(self):
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
        try:
            with open(RECENT_FILE, "w") as f:
                json.dump(self.recent_images, f)
        except Exception:
            pass

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = ImageEditor()
    editor.show()
    sys.exit(app.exec_())