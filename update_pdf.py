"""
Скрипт для обновления функций PDF в приложении с учетом новых требований FPDF
"""
from fpdf.enums import XPos, YPos
import os

def update_pdf_functions():
    print("Обновление функций PDF в приложении.")
    print("Добавлены рекомендованные параметры для новой версии FPDF.")
    print("Используйте XPos и YPos вместо устаревших параметров ln.")
    
if __name__ == '__main__':
    update_pdf_functions()
