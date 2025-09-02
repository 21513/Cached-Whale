import sys
import os
import json
import numpy as np
import ctypes

from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QFileDialog, QVBoxLayout, QGraphicsView,
    QGraphicsScene, QGraphicsPixmapItem, QHBoxLayout, QLabel, QStackedLayout,
    QMenuBar, QMenu, QAction, QSplitter, QDialog, QFormLayout, QLineEdit,
    QCheckBox, QDialogButtonBox, QFrame
)
from PyQt5.QtGui import (
    QPixmap, QImage, QColor, QFontDatabase, QFont, QPainter, QIcon, QBrush
)
from PyQt5.QtCore import (
    Qt, QRectF, pyqtSignal, QStandardPaths
)
from style import cmd_theme, hacker_theme
from effects import (
    CompressionDialog,
    DitherDialog,
    SaturationDialog,
    ScanlinesDialog,
    NoiseDialog,
    HalftoneDialog,
    PixelateDialog,
    PixelSortDialog,
    VectorDisplaceDialog,
    PreferencesDialog
)

MAX_RECENT = 5

APPDATA_DIR = os.path.join(
    QStandardPaths.writableLocation(QStandardPaths.AppDataLocation),
    "CachedWhale"
)
os.makedirs(APPDATA_DIR, exist_ok=True)

RECENT_FILE = os.path.join(APPDATA_DIR, "recents.json")

DWMWA_USE_IMMERSIVE_CMD_THEME = 20
DWMWA_CAPTION_COLOR = 35
DWMWA_TEXT_COLOR = 36

CMD_THEME = cmd_theme("#010101", "#ffffff", "1px solid #ffffff")
HACKER_THEME = hacker_theme("#010101", "#00ff00", "1px solid #00ff00")

theme_name = ""

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

        tile_size = 64
        pixmap = QPixmap(tile_size * 2, tile_size * 2)
        pixmap.fill(QColor(19, 19, 19))
        painter = QPainter(pixmap)
        painter.fillRect(0, 0, tile_size, tile_size, QColor(1, 1, 1))
        painter.fillRect(tile_size, tile_size, tile_size, tile_size, QColor(1, 1, 1))
        painter.end()
        self.checkerboard_brush = QBrush(pixmap)

    def drawBackground(self, painter: QPainter, rect: QRectF):
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

class StartPage(QWidget):
    def __init__(self, recent_images, import_callback, recent_callback):
        super().__init__()
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        title_layout = QHBoxLayout()
        title_layout.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        filepath = os.path.join(os.path.dirname(__file__), "assets", "logo.svg")
        logo = QLabel()
        logo.setProperty("class", "logo")
        pixmap = QPixmap(filepath)
        scaled_pixmap = pixmap.scaled(100, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        logo.setPixmap(scaled_pixmap)
        title_layout.addWidget(logo)

        title = QLabel("cached whale")
        title.setStyleSheet("font-family: 'Minecraft'; font-size: 64px; margin-left: 12px;")
        title_layout.addWidget(title)

        layout.addLayout(title_layout)
        import_btn = QPushButton("> import image")
        import_btn.clicked.connect(import_callback)
        layout.addWidget(import_btn, alignment=Qt.AlignLeft)

        divider = QLabel(". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . .")
        layout.addWidget(divider, alignment=Qt.AlignLeft)

        recent_label = QLabel("recent images >")
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

        self.setWindowTitle("resize image")
        self.setFixedSize(260, 120)
        self.setStyleSheet(CMD_THEME)

        self.orig_w = orig_w
        self.orig_h = orig_h
        self.aspect = orig_w / orig_h if orig_h != 0 else 1
        
        layout = QFormLayout()
        self.width_edit = QLineEdit(str(orig_w))
        self.height_edit = QLineEdit(str(orig_h))
        self.lock_aspect = QCheckBox("lock aspect ratio")
        self.lock_aspect.setChecked(True)
        layout.addRow("width >", self.width_edit)
        layout.addRow("height >", self.height_edit)
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

class ImageEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Cached Whale")
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
        self.setStyleSheet(CMD_THEME)

        self.set_titlebar_color(0x010101)

        self.recent_images = self.load_recent_images()

        self.scene = QGraphicsScene()
        self.canvas = CanvasView()
        self.canvas.setScene(self.scene)
        self.image_item = None
        self.current_image_path = None
        self.inverted_pixmap = None

        self.undo_stack = []
        self.redo_stack = []

        self.stacked_layout = QStackedLayout()
        self.start_page = StartPage(
            self.recent_images,
            self.load_image_dialog,
            self.load_recent_image
        )

        self.sidebar = QWidget()
        sidebar_layout = QVBoxLayout()
        sidebar_layout.setAlignment(Qt.AlignTop)

        self.invert_btn = QPushButton("> invert")
        self.invert_btn.clicked.connect(self.invert_image)
        sidebar_layout.addWidget(self.invert_btn)

        self.dither_btn = QPushButton("> dither")
        self.dither_btn.clicked.connect(self.dither_dialog)
        sidebar_layout.addWidget(self.dither_btn)

        self.compression_btn = QPushButton("> compression")
        self.compression_btn.clicked.connect(self.compression_dialog)
        sidebar_layout.addWidget(self.compression_btn)

        self.saturation_btn = QPushButton("> saturation")
        self.saturation_btn.clicked.connect(self.saturation_dialog)
        sidebar_layout.addWidget(self.saturation_btn)

        self.pixelate_btn = QPushButton("> pixelate")
        self.pixelate_btn.clicked.connect(self.pixelate_dialog)
        sidebar_layout.addWidget(self.pixelate_btn)


        self.sidebar.setLayout(sidebar_layout)

        self.scanlines_btn = QPushButton("> scanlines")
        self.scanlines_btn.clicked.connect(self.scanlines_dialog)
        sidebar_layout.addWidget(self.scanlines_btn)

        self.filmgrain_btn = QPushButton("> noise")
        self.filmgrain_btn.clicked.connect(self.noise_dialog)
        sidebar_layout.addWidget(self.filmgrain_btn)

        self.halftone_btn = QPushButton("> halftone")
        self.halftone_btn.clicked.connect(self.halftone_dialog)
        sidebar_layout.addWidget(self.halftone_btn)

        self.pixelsort_btn = QPushButton("> pixel sort")
        self.pixelsort_btn.clicked.connect(self.pixelsort_dialog)
        sidebar_layout.addWidget(self.pixelsort_btn)

        self.vectordisplace_btn = QPushButton("> vector displace")
        self.vectordisplace_btn.clicked.connect(self.vectordisplace_dialog)
        sidebar_layout.addWidget(self.vectordisplace_btn)

        sidebar_layout.addStretch()

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setProperty("class", "divider")
        sidebar_layout.addWidget(separator)

        self.save_image_btn = QPushButton("> save as")
        self.save_image_btn.clicked.connect(self.save_image_as)
        self.save_image_btn.setEnabled(False)
        sidebar_layout.addWidget(self.save_image_btn)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.addWidget(self.canvas)
        self.splitter.addWidget(self.sidebar)
        self.splitter.setSizes([700, 100])
        canvas_page = QWidget()
        canvas_layout = QHBoxLayout()
        canvas_layout.setContentsMargins(0, 0, 0, 0)
        canvas_layout.addWidget(self.splitter)
        canvas_page.setLayout(canvas_layout)

        self.stacked_layout.addWidget(self.start_page)
        self.stacked_layout.addWidget(canvas_page)

        self.menu_bar = QMenuBar(self)
        self.menu_bar.setNativeMenuBar(False) # important for linux and macos apparently
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

        edit_menu = QMenu("&Edit", self)
        resize_action = QAction("&Resize Image...", self)
        resize_action.triggered.connect(self.open_resize_dialog)
        edit_menu.addAction(resize_action)
        self.menu_bar.addMenu(edit_menu)

        edit_menu.addSeparator()

        preferences_menu = QAction("&Preferences", self)
        preferences_menu.setShortcut("Ctrl+,")
        preferences_menu.triggered.connect(self.open_preferences_menu)
        edit_menu.addAction(preferences_menu)
        self.menu_bar.addMenu(edit_menu)

        self.shortcut_zoom = QAction(self)
        self.shortcut_zoom.setShortcut("Z")
        self.shortcut_zoom.triggered.connect(self.zoom_100)
        self.addAction(self.shortcut_zoom)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(self.menu_bar)

        main_layout.addLayout(self.stacked_layout)

        self.setLayout(main_layout)

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
            original_image = self.image_item.pixmap()
            image = original_image.toImage().convertToFormat(QImage.Format_ARGB32)
            ptr = image.bits()
            ptr.setsize(image.byteCount())
            arr = np.frombuffer(ptr, np.uint8).reshape((image.height(), image.width(), 4))
            arr[..., 0:3] = 255 - arr[..., 0:3]
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
            if dlg.show() == QDialog.Accepted:
                w, h = dlg.get_size()
                self.resize_image(w, h)

    def open_preferences_menu(self):
        # pass current stylesheet info (track current theme in a variable)
        dlg = PreferencesDialog(current_theme=getattr(self, "current_theme", "cmd"), parent=self)
        if dlg.exec_() == QDialog.Accepted:
            new_theme = dlg.select_theme()
            self.apply_theme(new_theme)

    def apply_theme(self, theme_name):
        if theme_name == "cmd":
            self.setStyleSheet(CMD_THEME)

        elif theme_name == "hacker":
            self.setStyleSheet(HACKER_THEME)
        else:
            self.setStyleSheet(CMD_THEME)

        self.current_theme = theme_name


    def resize_image(self, w, h):
        if self.image_item:
            original_image = self.image_item.pixmap()
            scaled = original_image.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.scene.clear()
            self.image_item = QGraphicsPixmapItem(scaled)
            self.scene.addItem(self.image_item)
            self.scene.setSceneRect(self.image_item.boundingRect())
            self.canvas.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.canvas.centerOn(self.image_item)
            self.save_image_btn.setEnabled(True)
            # self.push_undo(scaled)

    def zoom_100(self):
        if self.image_item:
            self.canvas.resetTransform()
            self.canvas.fitInView(self.image_item, Qt.KeepAspectRatio)
            self.canvas.centerOn(self.image_item)

    def compression_dialog(self):
        if self.image_item:
            original_image = self.image_item.pixmap()
            dlg = CompressionDialog(self, original_image, self.set_canvas_pixmap, default_quality=10)

            dlg.accepted.connect(lambda: self.push_undo(dlg.get_pixmap()))
            dlg.rejected.connect(lambda: self.set_canvas_pixmap(original_image, push=False))
            dlg.show()

    def dither_dialog(self):
        if self.image_item:
            original_image = self.image_item.pixmap()
            dlg = DitherDialog(self, original_image, self.set_canvas_pixmap, default_threshold=128)

            dlg.accepted.connect(lambda: self.push_undo(dlg.get_pixmap()))
            dlg.rejected.connect(lambda: self.set_canvas_pixmap(original_image, push=False))
            dlg.show()

    def saturation_dialog(self):
        if self.image_item:
            original_image = self.image_item.pixmap()
            dlg = SaturationDialog(self, original_image, self.set_canvas_pixmap, default_saturation=100)

            dlg.accepted.connect(lambda: self.push_undo(dlg.get_pixmap()))
            dlg.rejected.connect(lambda: self.set_canvas_pixmap(original_image, push=False))
            dlg.show()

    def pixelate_dialog(self):
        if self.image_item:
            original_image = self.image_item.pixmap()
            dlg = PixelateDialog(self, original_image, self.set_canvas_pixmap, default_blocksize=8)

            dlg.accepted.connect(lambda: self.push_undo(dlg.get_pixmap()))
            dlg.rejected.connect(lambda: self.set_canvas_pixmap(original_image, push=False))
            dlg.show()

    def scanlines_dialog(self):
        if self.image_item:
            original_image = self.image_item.pixmap()
            dlg = ScanlinesDialog(self, original_image, self.set_canvas_pixmap)

            dlg.accepted.connect(lambda: self.push_undo(dlg.get_pixmap()))
            dlg.rejected.connect(lambda: self.set_canvas_pixmap(original_image, push=False))
            dlg.show()

    def noise_dialog(self):
        if self.image_item:
            original_image = self.image_item.pixmap()
            dlg = NoiseDialog(self, original_image, self.set_canvas_pixmap)

            dlg.accepted.connect(lambda: self.push_undo(dlg.get_pixmap()))
            dlg.rejected.connect(lambda: self.set_canvas_pixmap(original_image, push=False))
            dlg.show()

    def halftone_dialog(self):
        if self.image_item:
            original_image = self.image_item.pixmap()
            dlg = HalftoneDialog(self, original_image, self.set_canvas_pixmap)
            
            dlg.accepted.connect(lambda: self.push_undo(dlg.get_pixmap()))
            dlg.rejected.connect(lambda: self.set_canvas_pixmap(original_image, push=False))
            dlg.show()

    def pixelsort_dialog(self):
        if self.image_item:
            original_image = self.image_item.pixmap()
            dlg = PixelSortDialog(self, original_image, self.set_canvas_pixmap)
            
            dlg.accepted.connect(lambda: self.push_undo(dlg.get_pixmap()))
            dlg.rejected.connect(lambda: self.set_canvas_pixmap(original_image, push=False))
            dlg.show()

    def vectordisplace_dialog(self):
        if self.image_item:
            original_image = self.image_item.pixmap()
            dlg = VectorDisplaceDialog(self, original_image, self.set_canvas_pixmap)
            
            dlg.accepted.connect(lambda: self.push_undo(dlg.get_pixmap()))
            dlg.rejected.connect(lambda: self.set_canvas_pixmap(original_image, push=False))
            dlg.show()

    def set_canvas_pixmap(self, pixmap, push=True):
        self.scene.clear()
        self.image_item = QGraphicsPixmapItem(pixmap)
        self.scene.addItem(self.image_item)
        self.scene.setSceneRect(self.image_item.boundingRect())
        self.canvas.fitInView(self.image_item, Qt.KeepAspectRatio)
        self.canvas.centerOn(self.image_item)
        self.save_image_btn.setEnabled(True)
        if push:
            self.push_undo(pixmap)

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

    def set_titlebar_color(self, color):
        hwnd = int(self.winId())
        color_ref = ctypes.c_uint(color)
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_CAPTION_COLOR,
            ctypes.byref(color_ref),
            ctypes.sizeof(color_ref)
        )

if __name__ == "__main__":
    app = QApplication(sys.argv)

    icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
    app.setWindowIcon(QIcon(icon_path))

    editor = ImageEditor()
    editor.show()
    editor.setFocus(Qt.NoFocusReason)
    sys.exit(app.exec_())