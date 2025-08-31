# Dark mode variables
dbackground_color = "#010101"
dtext_color = "#ffffff"
dhover_color = "#202020"

dborder = "1px solid #ffffff"

# Hacker mode variables
hbackground_color = "#010101"
htext_color = "#00ff00"
hhover_color = "#202020"

hborder = "1px solid #00ff00"

DARK_MODE = f"""
QWidget {{
    background-color: {dbackground_color};
    color: {dtext_color};
    font-family: 'Minecraft';
    font-size: 16px;
    padding: 4px;
}}

QPushButton {{
    padding: 4px;
    text-align: left;
}}

QPushButton:hover {{
    border: 1px solid {dtext_color};
}}

QLabel {{
    padding: 4px;
}}

QMenuBar {{
    background-color: {dbackground_color};
    color: {dtext_color};
}}

QMenuBar::item {{
    spacing: 4px;
    padding: 4px 8px;
    background: transparent;
}}

QMenuBar::item:selected {{
    background-color: {dhover_color};
}}

QMenu::separator {{
    height: 2px;
    background-color: {dtext_color};
    margin: 4px 8px;
}}

QMenu {{
    padding: 2px;
    border: {dborder};
}}

QMenu::item:selected {{
    background-color: {dhover_color};
}}

CanvasView {{
    border: {dborder};
    border-radius: 4px;
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
