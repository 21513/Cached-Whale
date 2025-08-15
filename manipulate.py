import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QFileDialog, QVBoxLayout
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

        self.image_label = QLabel("No image loaded")
        self.image_label.setScaledContents(True)
        self.image_label.setAlignment(Qt.AlignCenter)

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.button)
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
                # Fit image to label while preserving aspect ratio
                aspect_ratio = base_width / base_height
                if label_size.width() / aspect_ratio <= label_size.height():
                    scaled_width = min(scaled_width, label_size.width())
                    scaled_height = int(scaled_width / aspect_ratio)
                else:
                    scaled_height = min(scaled_height, label_size.height())
                    scaled_width = int(scaled_height * aspect_ratio)

            scaled_pixmap = self.original_pixmap.scaled(
                scaled_width, scaled_height, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        else:
            self.image_label.setText("No image loaded")

    def wheelEvent(self, event):
        if self.original_pixmap:
            if event.angleDelta().y() > 0:
                self.zoom_factor *= 1.25
            else:
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
