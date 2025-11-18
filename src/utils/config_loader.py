"""
Модуль для загрузки конфигурации системы
"""

import json
from typing import Dict, Any

def load_config(config_path: str) -> Dict[str, Any]:
    """
    Загрузка конфигурации из JSON файла
    
    Args:
        config_path: Путь к файлу конфигурации
        
    Returns:
        Словарь с конфигурацией
        
    Raises:
        FileNotFoundError: если файл не найден
        json.JSONDecodeError: если ошибка формата JSON
    """
    with open(config_path, 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print(f"Конфигурация загружена из {config_path}")
    return config