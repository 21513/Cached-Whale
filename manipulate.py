import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QFileDialog, QVBoxLayout, QHBoxLayout
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

class ImageEditor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Simple Image Viewer")
        self.resize(600, 400)

        # UI Elements
        self.button = QPushButton("Import Image")
        self.button.clicked.connect(self.load_image)

        self.zoom_in_button = QPushButton("Zoom In")
        self.zoom_in_button.clicked.connect(self.zoom_in)
        self.zoom_out_button = QPushButton("Zoom Out")
        self.zoom_out_button.clicked.connect(self.zoom_out)

        self.image_label = QLabel("No image loaded")
        self.image_label.setScaledContents(True)
        self.image_label.setAlignment(Qt.AlignCenter)

        # Layout
        button_layout = QHBoxLayout()
        button_layout.addWidget(self.button)
        button_layout.addWidget(self.zoom_in_button)
        button_layout.addWidget(self.zoom_out_button)

        layout = QVBoxLayout()
        layout.addLayout(button_layout)
        layout.addWidget(self.image_label)
        self.setLayout(layout)

        # Image and zoom state
        self.original_pixmap = None
        self.zoom_factor = 1.0

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            pixmap = QPixmap(file_path)
            self.original_pixmap = pixmap
            self.zoom_factor = 1.0
            self.update_image_display()

    def update_image_display(self):
        if self.original_pixmap:
            # Calculate scaled size based on zoom and window size
            label_size = self.image_label.size()
            base_width = self.original_pixmap.width()
            base_height = self.original_pixmap.height()
            scaled_width = int(base_width * self.zoom_factor)
            scaled_height = int(base_height * self.zoom_factor)

            # Ensure the image does not exceed the label size unless zoomed in
            if self.zoom_factor <= 1.0:
                scaled_width = min(scaled_width, label_size.width())
                scaled_height = min(scaled_height, label_size.height())

            scaled_pixmap = self.original_pixmap.scaled(
                scaled_width, scaled_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        else:
            self.image_label.setText("No image loaded")

    def zoom_in(self):
        if self.original_pixmap:
            self.zoom_factor *= 1.25
            self.update_image_display()

    def zoom_out(self):
        if self.original_pixmap:
            self.zoom_factor /= 1.25
            if self.zoom_factor < 0.1:
                self.zoom_factor = 0.1
            self.update_image_display()

    def resizeEvent(self, event):
        # Rescale image when window is resized
        self.update_image_display()
        super().resizeEvent(event)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = ImageEditor()
    editor.show()
    sys.exit(app.exec_())
