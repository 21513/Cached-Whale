def cmd_theme(background_color, text_color, border):
    return f"""
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
        border: {border};
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
        border: {border};
    }}

    QMenu::item:selected {{
        background-color: {text_color};
        color: {background_color};
    }}

    CanvasView {{
        border: 2px solid {text_color};
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
        border: {border};
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

def hacker_theme(background_color, text_color, border):
    return f"""
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
        border: {border};
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
        border: {border};
    }}

    QMenu::item:selected {{
        background-color: {text_color};
        color: {background_color};
    }}

    CanvasView {{
        border: {border};
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
        border: {border};
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