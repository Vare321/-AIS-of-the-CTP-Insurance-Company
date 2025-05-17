"""
Модуль для управления хранилищем файлов
"""
import os
import json
import uuid
from datetime import datetime

class FileStorage:
    """Класс для управления хранилищем файлов"""
    
    def __init__(self, storage_dir):
        """Инициализация хранилища файлов"""
        self.storage_dir = storage_dir
        self.registry_file = os.path.join(storage_dir, "file_registry.json")
        self.file_registry = {}
        
        # Создаем директорию, если она не существует
        if not os.path.exists(storage_dir):
            os.makedirs(storage_dir)
        
        # Загружаем реестр файлов, если он существует
        if os.path.exists(self.registry_file):
            try:
                with open(self.registry_file, 'r', encoding='utf-8') as f:
                    self.file_registry = json.load(f)
            except Exception:
                self.file_registry = {}
    
    def register_file(self, file_path):
        """Регистрирует файл в хранилище и возвращает его ID"""
        file_id = str(uuid.uuid4())
        filename = os.path.basename(file_path)
        
        # Сохраняем информацию о файле
        self.file_registry[file_id] = {
            'path': file_path,
            'filename': filename,
            'created_at': datetime.now().isoformat()
        }
        
        # Сохраняем реестр в файл
        self._save_registry()
        
        return file_id
    
    def get_file_info(self, file_id):
        """Возвращает информацию о файле по его ID"""
        return self.file_registry.get(file_id)
    
    def _save_registry(self):
        """Сохраняет реестр файлов в JSON"""
        with open(self.registry_file, 'w', encoding='utf-8') as f:
            json.dump(self.file_registry, f, ensure_ascii=False)
