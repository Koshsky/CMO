"""
Модуль генерации случайных величин по заданным распределениям
"""

import math
import random

def uniform_distribution(min_val: float, max_val: float) -> float:
    """Равномерное распределение (ИЗ2)"""
    return min_val + (max_val - min_val) * random.random()

def exponential_distribution(lambd: float) -> float:
    """Экспоненциальное распределение (ПЗ1)"""
    return -math.log(1.0 - random.random()) / lambd

def erlang_distribution(order: int, lambd: float) -> float:
    """Распределение Эрланга"""
    product = 1.0
    for _ in range(order):
        product *= random.random()
    return -math.log(product) / lambd