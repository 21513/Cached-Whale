# Dark mode variables
background_color = "#010101"
text_color = "#ffffff"

dborder = "1px solid #ffffff"

# Hacker mode variables
hbackground_color = "#010101"
htext_color = "#00ff00"
hhover_color = "#202020"

hborder = "1px solid #00ff00"

DARK_MODE = f"""
QWidget {{
    background-color: {background_color};
    color: {text_color};
    font-family: 'Minecraft';
    font-size: 16px;
    padding: 4px;
}}

QPushButton {{
    padding: 4px;
    text-align: left;
}}

QPushButton:hover {{
    border: 1px solid {text_color};
    background-color: {text_color};
    color: {background_color};
}}

QPushButton:focus {{
    background-color: {text_color};
    color: {background_color};
    outline: none;
    border: {dborder};
}}

QLabel {{
    padding: 4px;
}}

QMenuBar {{
    background-color: {background_color};
    color: {text_color};
}}

QMenuBar::item {{
    spacing: 4px;
    padding: 4px 8px;
    background: transparent;
}}

QMenuBar::item:selected {{
    background-color: {text_color};
    color: {background_color};
}}

QMenu::separator {{
    height: 2px;
    background-color: {text_color};
    margin: 4px 8px;
}}

QMenu {{
    padding: 2px;
    border: {dborder};
}}

QMenu::item:selected {{
    background-color: {text_color};
    color: {background_color};
}}

CanvasView {{
    border: {dborder};
    border-radius: 4px;
}}

QComboBox {{
    background-color: #222;
    color: #eee;
    border: 1px solid #555;
    padding: 4px;
}}

QComboBox:focus {{
    background-color: {background_color};
    color: {text_color};
    border: {dborder};
}}

QComboBox:on {{
    background-color: {background_color};
}}

QComboBox QAbstractItemView {{
    background-color: {background_color};
    color: {text_color};
    selection-background-color: {background_color};
    selection-color: {text_color};
}}

QFrame[class="divider"] {{
    background-color: {text_color};
}}
"""

HACKER_MODE = f"""
QWidget {{
    background-color: {hbackground_color};
    color: {htext_color};
    font-family: 'Minecraft';
    font-size: 16px;
    padding: 4px;
}}

QPushButton {{
    padding: 4px;
    text-align: left;
}}

QPushButton:hover {{
    border: 1px solid {htext_color};
}}

QLabel {{
    padding: 4px;
}}

QMenuBar {{
    background-color: {hbackground_color};
    color: {htext_color};
}}

QMenuBar::item {{
    spacing: 4px;
    padding: 4px 8px;
    background: transparent;
}}

QMenuBar::item:selected {{
    background-color: {hhover_color};
}}

QMenu::separator {{
    height: 2px;
    background-color: {htext_color};
    margin: 4px 8px;
}}

QMenu {{
    padding: 2px;
    border: {hborder};
}}

QMenu::item:selected {{
    background-color: {hhover_color};
}}

CanvasView {{
    border: {hborder};
    border-radius: 4px;
}}
"""
