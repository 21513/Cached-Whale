import sys
from PyQt5.QtWidgets import QApplication, QWidget, QPushButton, QLabel, QFileDialog, QVBoxLayout
from PyQt5.QtGui import QPixmap

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

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.button)
        layout.addWidget(self.image_label)
        self.setLayout(layout)

    def load_image(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Open Image", "", "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)")
        if file_path:
            pixmap = QPixmap(file_path)
            self.image_label.setPixmap(pixmap)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    editor = ImageEditor()
    editor.show()
    sys.exit(app.exec_())
