"""
Модуль для управления пошаговым режимом моделирования
"""

from typing import Dict, Any, List, Callable
import time

class StepModeController:
    """Контроллер пошагового режима моделирования"""
    
    def __init__(self):
        self.is_step_mode = False
        self.breakpoints = set()
        self.current_step = 0
        self.event_history = []
        
        # Типы событий для остановки
        self.event_types = {
            'arrival': 'Поступление заявки',
            'buffer_write': 'Запись в буфер',
            'buffer_reject': 'Отказ заявке', 
            'device_start': 'Начало обслуживания',
            'device_finish': 'Окончание обслуживания',
            'buffer_select': 'Выбор заявки из буфера',
            'packet_change': 'Смена пакета обслуживания'
        }
    
    def enable_step_mode(self, breakpoint_events: List[str] = None):
        """Включение пошагового режима"""
        self.is_step_mode = True
        if breakpoint_events:
            self.breakpoints = set(breakpoint_events)
        else:
            # Все события по умолчанию
            self.breakpoints = set(self.event_types.keys())
        print("Пошаговый режим активирован")
    
    def disable_step_mode(self):
        """Выключение пошагового режима"""
        self.is_step_mode = False
        print("Пошаговый режим деактивирован")
    
    def check_breakpoint(self, event_type: str, event_data: Dict[str, Any]) -> bool:
        """
        Проверка точки остановки
        
        Args:
            event_type: тип события
            event_data: данные события
            
        Returns:
            True если нужно остановиться
        """
        if not self.is_step_mode:
            return False
            
        should_break = event_type in self.breakpoints
        
        if should_break:
            self.current_step += 1
            self.event_history.append({
                'step': self.current_step,
                'type': event_type,
                'data': event_data,
                'time': event_data.get('time', 0)
            })
            
        return should_break
    
    def wait_for_step(self, event_type: str, event_data: Dict[str, Any]):
        """
        Ожидание команды пользователя для продолжения
        
        Args:
            event_type: тип события
            event_data: данные события
        """
        if not self.check_breakpoint(event_type, event_data):
            return
            
        self._display_event_info(event_type, event_data)
        self._show_control_prompt()
    
    def _display_event_info(self, event_type: str, event_data: Dict[str, Any]):
        """Отображение информации о событии"""
        event_name = self.event_types.get(event_type, event_type)
        
        print(f"\n{'='*60}")
        print(f"ШАГ {self.current_step}: {event_name}")
        print(f"{'='*60}")
        
        # Общая информация
        print(f"Время: {event_data.get('time', 0):.3f}")
        
        # Специфичная информация для разных типов событий
        if event_type == 'arrival':
            source = event_data.get('source', 0)
            print(f"Источник: И{source + 1}")
            print(f"Время след. заявки: {event_data.get('next_arrival_time', 0):.3f}")
            
        elif event_type == 'buffer_write':
            source = event_data.get('source', 0)
            buffer_pos = event_data.get('buffer_position', 0)
            print(f"Источник: И{source + 1}")
            print(f"Позиция в буфере: {buffer_pos}")
            print(f"Заявок в буфере: {event_data.get('buffer_size', 0)}")
            
        elif event_type == 'buffer_reject':
            source = event_data.get('source', 0)
            rejected_source = event_data.get('rejected_source', 0)
            print(f"Новая заявка от: И{source + 1}")
            print(f"Отказ заявке от: И{rejected_source + 1}")
            print(f"Причина: {event_data.get('reason', 'переполнение буфера')}")
            print(f"Общее количество отказов: {event_data.get('total_rejects', 0)}")
            
        elif event_type == 'device_start':
            source = event_data.get('source', 0)
            service_time = event_data.get('service_time', 0)
            print(f"Прибор обслуживает заявку от: И{source + 1}")
            print(f"Время обслуживания: {service_time:.3f}")
            print(f"Окончание в: {event_data.get('finish_time', 0):.3f}")
            
        elif event_type == 'device_finish':
            print(f"Прибор освободился")
            print(f"Причина: {event_data.get('reason', 'обслуживание завершено')}")
            
        elif event_type == 'buffer_select':
            source = event_data.get('selected_source', 0)
            buffer_pos = event_data.get('buffer_position', 0)
            print(f"Выбрана заявка от: И{source + 1}")
            print(f"Из позиции буфера: {buffer_pos}")
            print(f"Текущий пакет: {event_data.get('current_packet', 'нет')}")
            
        elif event_type == 'packet_change':
            old_packet = event_data.get('old_packet', -1)
            new_packet = event_data.get('new_packet', -1)
            print(f"Смена пакета: {old_packet} -> {new_packet}")
            print(f"Причина: {event_data.get('reason', 'пакет опустошен')}")
        
        # Состояние системы
        self._display_system_state(event_data)
    
    def _display_system_state(self, event_data: Dict[str, Any]):
        """Отображение текущего состояния системы"""
        print(f"\n--- ТЕКУЩЕЕ СОСТОЯНИЕ СИСТЕМЫ ---")
        
        # Приборы - состояние обработчиков
        devices_state = event_data.get('devices_state', [])
        print(f"Приборы: {', '.join(devices_state)}")
        
        # Буфер
        buffer_state = event_data.get('buffer_state', [])
        buffer_size = event_data.get('buffer_size', 0)
        buffer_capacity = event_data.get('buffer_capacity', 4)
        
        print(f"Буфер [{buffer_size}/{buffer_capacity}]: {' '.join(buffer_state)}")
        
        # Следующие заявки от источников
        next_arrivals = event_data.get('next_arrivals', [])
        if next_arrivals:
            print(f"След. заявки: {', '.join(next_arrivals)}")
        
        # ОБРАБОТАНО ПО ОБРАБОТЧИКАМ (приборам) - это главное изменение!
        devices_processed = event_data.get('devices_processed', [])
        if devices_processed:
            print(f"Обработано: {', '.join(devices_processed)}")
        
        # Общее количество отказов
        total_rejected = event_data.get('total_rejected', 0)
        print(f"Отказано: {total_rejected}")
    
    def _show_control_prompt(self):
        """Показ управляющего промпта"""
        while True:
            print(f"\n{'─'*40}")
            print("УПРАВЛЕНИЕ:")
            print("  [Enter] - следующий шаг")
            print("  [c]     - продолжить до конца")
            print("  [q]     - выйти")
            print(f"{'─'*40}")
            
            command = input("Команда: ").strip().lower()
            
            if command == '' or command == 'n':
                break  # следующий шаг
            elif command == 'c':
                self.disable_step_mode()
                break
            elif command == 'q':
                print("Выход из моделирования...")
                exit(0)
            else:
                print("Неизвестная команда")
    
    def get_event_history(self) -> List[Dict]:
        """Получить историю событий"""
        return self.event_history