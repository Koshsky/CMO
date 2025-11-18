"""
Полная реализация системы массового обслуживания для варианта №6
"""

import json
from typing import Dict, Any, List, Tuple
from src.utils.step_mode import StepModeController
from src.utils.distributions import uniform_distribution, exponential_distribution

class SMOSystem:
    """Полная реализация СМО для варианта №6"""
    
    def __init__(self, config):
        self.config = config
        self.step_controller = StepModeController()
        self.initialize_system()
    
    def initialize_system(self):
        """Инициализация системы согласно блок-схеме"""
        # Общие параметры
        self.buffer_capacity = self.config['buffer']['size']
        self.min_requests = self.config['simulation']['min_requests']
        
        # Параметры источников (ИЗ2 - равномерный закон)
        self.source_params = [
            self.config['sources']['params']['source_0'],
            self.config['sources']['params']['source_1']
        ]
        
        # Параметры прибора (ПЗ1 - экспоненциальный закон)
        self.service_lambda = self.config['device']['lambda']
        self.tau_range = self.config['device']['tau_range']
        
        # Дисциплины
        self.disciplines = self.config['buffer']['disciplines']
        
        # Текущие значения для реализации
        self.current_tau = self.tau_range['min']
        self.current_time = 0.0
        self.realization_results = []
        
        print("Система инициализирована для варианта №6")

    def initialize_realization(self):
        """Инициализация переменных для одной реализации"""
        # Временные параметры
        self.current_time = 0.0
        self.TPOST = [0.0, 0.0]  # Время следующей заявки от источников
        self.TOSV = 0.0          # Время освобождения прибора
        self.device_busy = False
        
        # Буфер (БМС)
        self.INDBUF = 0
        self.BUFT = [0.0] * self.buffer_capacity
        self.BUFN = [0] * self.buffer_capacity
        self.buffer_pointer = 0  # Для дисциплины по кольцу
        
        # Счетчики (БМС) - ОБЩИЕ для системы
        self.KOL = [0, 0]    # Общее количество заявок по источникам
        self.KOTK = 0        # ОБЩИЙ счетчик отказов для системы
        self.KOBR = [0, 0]   # Количество обработанных по источникам
        self.TOG = [0.0, 0.0] # Суммарное время ожидания по источникам
        
        # Вспомогательные переменные
        self.NMIN = 0
        self.NOMBUF = 0
        self.NOMOB = 0
        self.TOB = 0.0
        
        # Дисциплина Д2Б5 (пакетная)
        self.current_packet = -1
        self.packet_empty = True
        
        # Дисциплина Д2П2 (выбор прибора по кольцу)
        self.device_pointer = 0
        
        # Генерация первых заявок
        self.TPOST[0] = self.generate_interval(0)
        self.TPOST[1] = self.generate_interval(1)

    def generate_interval(self, source_num: int) -> float:
        """Генерация интервала между заявками по закону ИЗ2 (равномерный)"""
        params = self.source_params[source_num]
        return uniform_distribution(params['min_interval'], params['max_interval'])

    def generate_service_time(self) -> float:
        """Генерация времени обслуживания по закону ПЗ1 (экспоненциальный)"""
        return exponential_distribution(self.service_lambda)

    def boos_block(self) -> int:
        """БООС - выбор ближайшего события"""
        # Определяем ближайшее событие
        next_arrival = min(self.TPOST[0], self.TPOST[1])
        
        if not self.device_busy:
            # Прибор свободен - следующее событие всегда поступление заявки
            if self.TPOST[0] < self.TPOST[1]:
                self.NMIN = 0
                return 1
            else:
                self.NMIN = 1
                return 2
        else:
            # Прибор занят - сравниваем поступление заявок и освобождение прибора
            if next_arrival < self.TOSV:
                if self.TPOST[0] < self.TPOST[1]:
                    self.NMIN = 0
                    return 1
                else:
                    self.NMIN = 1
                    return 2
            else:
                return 3

    def process_event(self, event_type: int):
        """Обработка события согласно блок-схеме"""
        event_data = self._get_system_state()
        
        if event_type == 1 or event_type == 2:
            # Событие от источника
            source = 0 if event_type == 1 else 1
            self.NMIN = source
            
            event_data.update({
                'event_type': 'arrival',
                'source': source,
                'arrival_time': self.TPOST[source]
            })
            self.step_controller.wait_for_step('arrival', event_data)
            
            self.bas_block(source)
            
        elif event_type == 3:
            # Событие освобождения прибора
            event_data.update({
                'event_type': 'device_free',
                'device_free_time': self.TOSV
            })
            self.step_controller.wait_for_step('device_finish', event_data)
            
            self.bas3_block()

    def bas_block(self, source: int):
        """БАС1/БАС2 - анализ состояния при поступлении заявки"""
        if not self.device_busy:
            # Прибор свободен - БМС32 (обслуживание без буфера)
            self.bms32_block(source)
        elif self.INDBUF < self.buffer_capacity:
            # Прибор занят, но есть место в буфере - БМС12/БМС22
            self.bms12_block(source)
        else:
            # Прибор занят и буфер полон - БМС11/БМС21 (отказ с выбиванием)
            self.bms11_block(source)

    def bas3_block(self):
        """БАС3 - анализ состояния при освобождении прибора"""
        self.device_busy = False
        self.device_current_source = -1
        
        if self.INDBUF > 0:
            # В буфере есть заявки - БМС31
            self.bms31_block()
        else:
            # Буфер пуст - прибор остается свободным
            self.TOSV = float('inf')
            
            event_data = self._get_system_state()
            event_data.update({
                'event_type': 'device_finish',
                'device_free_time': self.current_time,
                'reason': 'Буфер пуст, прибор свободен'
            })
            self.step_controller.wait_for_step('device_finish', event_data)

    def bms11_block(self, source: int):
        """БМС11/БМС21 - отказ с выбиванием (Д10О2)"""
        # Находим заявку для выбивания (источник с наименьшим приоритетом)
        victim_index = self.find_victim_for_rejection()
        victim_source = self.BUFN[victim_index]
        
        # Увеличиваем ОБЩИЙ счетчик отказов
        self.KOTK += 1
        
        # Заменяем выбитую заявку на новую
        self.BUFT[victim_index] = self.TPOST[source]
        self.BUFN[victim_index] = source
        
        # Генерация следующей заявки и обновление счетчиков
        self.generate_next_request(source)
        
        event_data = self._get_system_state()
        event_data.update({
            'event_type': 'buffer_reject',
            'source': source,
            'rejected_source': victim_source,
            'buffer_position': victim_index,
            'total_rejects': self.KOTK,  # Добавляем общее количество отказов
            'reason': f'Выбивание заявки И{victim_source + 1}'
        })
        self.step_controller.wait_for_step('buffer_reject', event_data)

    def bms12_block(self, source: int):
        """БМС12/БМС22 - запись в буфер (Д10З2) при занятом приборе"""
        # Запись в буфер в порядке поступления (Д10З2)
        if self.disciplines['write'] == 'D10Z2':
            # Ищем первую свободную позицию
            write_position = -1
            for i in range(self.buffer_capacity):
                if self.BUFN[i] == 0 and self.BUFT[i] == 0:  # Слот пуст
                    write_position = i
                    break
            
            if write_position >= 0:
                self.BUFT[write_position] = self.TPOST[source]
                self.BUFN[write_position] = source
                self.INDBUF += 1
        
        # Генерация следующей заявки и обновление счетчиков
        self.KOL[source] += 1
        self.TPOST[source] = self.current_time + self.generate_interval(source)
        
        event_data = self._get_system_state()
        event_data.update({
            'event_type': 'buffer_write',
            'source': source,
            'buffer_position': write_position,
            'buffer_size': self.INDBUF,
            'reason': 'Прибор занят, заявка поставлена в буфер'
        })
        self.step_controller.wait_for_step('buffer_write', event_data)

    def bms31_block(self):
        """БМС31 - выборка из буфера на обслуживание (Д2Б5 + Д2П2)"""
        # Выбор заявки по дисциплине Д2Б5 (пакетная)
        selected_index = self.select_request_from_buffer()
        
        if selected_index >= 0:
            self.NOMOB = self.BUFN[selected_index]
            self.TOB = self.BUFT[selected_index]
            
            # Расчет времени ожидания
            wait_time = self.current_time - self.TOB
            self.TOG[self.NOMOB] += wait_time
            
            # Обслуживание заявки
            service_time = self.generate_service_time()
            self.TOSV = self.current_time + service_time
            self.device_busy = True
            self.device_current_source = self.NOMOB
            
            # Удаление заявки из буфера
            self.remove_from_buffer(selected_index)
            
            # Обновление счетчиков
            self.KOBR[self.NOMOB] += 1
            
            event_data = self._get_system_state()
            event_data.update({
                'event_type': 'buffer_select',
                'selected_source': self.NOMOB,
                'buffer_position': selected_index,
                'wait_time': wait_time,
                'service_time': service_time,
                'current_packet': self.current_packet
            })
            self.step_controller.wait_for_step('buffer_select', event_data)
            
            event_data.update({
                'event_type': 'device_start', 
                'source': self.NOMOB,
                'finish_time': self.TOSV,
                'from_buffer': True
            })
            self.step_controller.wait_for_step('device_start', event_data)

    def bms32_block(self, source: int):
        """БМС32 - обслуживание без буфера (при свободном приборе)"""
        # Обслуживание заявки, пришедшей напрямую на свободный прибор
        self.NOMOB = source
        self.TOB = self.TPOST[source]
        
        service_time = self.generate_service_time()
        self.TOSV = self.current_time + service_time
        self.device_busy = True
        self.device_current_source = source
        
        # Обновление счетчиков
        self.KOBR[source] += 1
        self.KOL[source] += 1
        
        # Генерация следующей заявки
        self.TPOST[source] = self.current_time + self.generate_interval(source)
        
        event_data = self._get_system_state()
        event_data.update({
            'event_type': 'device_start',
            'source': source,
            'service_time': service_time,
            'finish_time': self.TOSV,
            'direct_service': True  # Прямое обслуживание без буфера
        })
        self.step_controller.wait_for_step('device_start', event_data)

    def find_victim_for_rejection(self) -> int:
        """Найти заявку для выбивания по дисциплине Д10О2"""
        # Приоритет по номеру источника (источник 0 имеет высший приоритет)
        candidates = []
        
        for i in range(self.buffer_capacity):
            if self.BUFN[i] != 0 or self.BUFT[i] != 0:  # Слот занят
                source = self.BUFN[i]
                priority = 1 if source == 0 else 2  # Меньше число - выше приоритет
                candidates.append((priority, self.BUFT[i], i, source))
        
        # Сортируем по приоритету (возрастание), затем по времени (старые first)
        candidates.sort(key=lambda x: (x[0], x[1]))
        
        return candidates[0][2] if candidates else 0

    def select_request_from_buffer(self) -> int:
        """Выбор заявки из буфера по дисциплине Д2Б5 (пакетная)"""
        # Если текущий пакет не установлен или пуст, выбираем новый
        if self.current_packet == -1 or self.packet_empty:
            self.select_new_packet()
        
        # Ищем заявку текущего пакета в буфере
        for i in range(self.buffer_capacity):
            if self.BUFN[i] == self.current_packet and self.BUFT[i] > 0:
                self.packet_empty = False
                return i
        
        # Если заявок текущего пакета нет, выбираем новый пакет
        self.select_new_packet()
        for i in range(self.buffer_capacity):
            if self.BUFN[i] == self.current_packet and self.BUFT[i] > 0:
                return i
        
        return -1  # Не должно происходить

    def select_new_packet(self):
        """Выбор нового пакета для обслуживания"""
        old_packet = self.current_packet
        
        # Ищем источники, имеющие заявки в буфере
        available_sources = set()
        for i in range(self.buffer_capacity):
            if self.BUFN[i] != 0 or self.BUFT[i] != 0:
                available_sources.add(self.BUFN[i])
        
        if available_sources:
            # Выбираем источник с наивысшим приоритетом (источник 0)
            if 0 in available_sources:
                self.current_packet = 0
            else:
                self.current_packet = 1
            self.packet_empty = False
        else:
            self.current_packet = -1
            self.packet_empty = True
        
        if old_packet != self.current_packet and old_packet != -1:
            event_data = self._get_system_state()
            event_data.update({
                'event_type': 'packet_change',
                'old_packet': old_packet,
                'new_packet': self.current_packet,
                'reason': 'Смена пакета обслуживания'
            })
            self.step_controller.wait_for_step('packet_change', event_data)

    def select_device(self):
        """Выбор прибора по дисциплине Д2П2 (по кольцу)"""
        # В данной реализации один прибор, поэтому просто увеличиваем указатель
        self.device_pointer = (self.device_pointer + 1) % 1  # 1 прибор

    def remove_from_buffer(self, index: int):
        """Удаление заявки из буфера со сдвигом"""
        if index < 0 or index >= self.buffer_capacity:
            return
            
        # Сдвигаем элементы буфера
        for i in range(index, self.buffer_capacity - 1):
            self.BUFT[i] = self.BUFT[i + 1]
            self.BUFN[i] = self.BUFN[i + 1]
        
        # Очищаем последний элемент
        self.BUFT[self.buffer_capacity - 1] = 0.0
        self.BUFN[self.buffer_capacity - 1] = 0
        self.INDBUF = max(0, self.INDBUF - 1)

    def generate_next_request(self, source: int):
        """Генерация следующей заявки от источника"""
        self.TPOST[source] = self.current_time + self.generate_interval(source)
        self.KOL[source] += 1

    def _get_system_state(self) -> Dict[str, Any]:
        """Получить текущее состояние системы"""
        buffer_state = []
        for i in range(self.buffer_capacity):
            if self.BUFN[i] != 0 or self.BUFT[i] != 0:
                buffer_state.append(self.BUFN[i])
            else:
                buffer_state.append(None)
        
        return {
            'time': self.current_time,
            'buffer_state': buffer_state,
            'buffer_size': self.INDBUF,
            'buffer_capacity': self.buffer_capacity,
            'buffer_pointer': self.buffer_pointer,
            'device_busy': self.device_busy,
            'device_source': self.NOMOB if self.device_busy else -1,
            'device_finish_time': self.TOSV,
            'next_arrival_1': self.TPOST[0],
            'next_arrival_2': self.TPOST[1],
            'current_packet': self.current_packet,
            'statistics': {
                'total_1': self.KOL[0],
                'total_2': self.KOL[1],
                'processed_1': self.KOBR[0],
                'processed_2': self.KOBR[1],
                'total_rejected': self.KOTK,  # Теперь общее количество отказов
            },
            'tau': self.current_tau
        }

    def run_realization(self) -> Dict[str, Any]:
        """Запуск одной реализации моделирования"""
        self.initialize_realization()
        
        iteration = 0
        max_iterations = 100000  # Защита от бесконечного цикла
        
        while (self.KOL[0] < self.min_requests or self.KOL[1] < self.min_requests) and iteration < max_iterations:
            iteration += 1
            
            # БООС - определение следующего события
            event_type = self.boos_block()
            
            if event_type == 0:
                break  # Нет событий
                
            # Обновляем текущее время
            if event_type == 1:
                self.current_time = self.TPOST[0]
            elif event_type == 2:
                self.current_time = self.TPOST[1]
            elif event_type == 3:
                self.current_time = self.TOSV
            
            # Обработка события
            self.process_event(event_type)
        
        # Расчет результатов реализации
        return self.calculate_results()

    def calculate_results(self) -> Dict[str, Any]:
        """Расчет результатов реализации"""
        total_requests = self.KOL[0] + self.KOL[1]
        total_processed = self.KOBR[0] + self.KOBR[1]
        
        # Общая вероятность отказа для системы
        total_reject_prob = self.KOTK / total_requests if total_requests > 0 else 0
        
        results = {
            'tau': self.current_tau,
            'system_stats': {
                'total_requests': total_requests,
                'total_processed': total_processed,
                'total_rejected': self.KOTK,
                'total_reject_prob': total_reject_prob
            },
            'sources_stats': [],
            'device_stats': [],
            'realization_data': self._get_system_state()
        }
        
        # Статистика по источникам (только обработанные заявки)
        for i in range(2):
            avg_wait_time = self.TOG[i] / self.KOBR[i] if self.KOBR[i] > 0 else 0
            avg_service_time = self.current_tau  # Для упрощения
            
            results['sources_stats'].append({
                'total': self.KOL[i],
                'processed': self.KOBR[i],
                'avg_wait_time': avg_wait_time,
                'avg_system_time': avg_wait_time + avg_service_time
            })
        
        # Статистика по приборам
        utilization = self.current_time > 0  # Упрощенный расчет
        results['device_stats'].append({
            'utilization': utilization,
            'total_working_time': self.current_time
        })
        
        return results

    def run_simulation(self, step_mode: bool = False) -> List[Dict[str, Any]]:
        """Запуск полного моделирования для всех TAU"""
        if step_mode:
            self.enable_step_mode()
        
        print("Запуск полного моделирования СМО вариант №6")
        
        self.realization_results = []
        current_tau = self.tau_range['min']
        
        while current_tau <= self.tau_range['max']:
            self.current_tau = current_tau
            print(f"Моделирование для TAU = {current_tau:.1f}")
            
            result = self.run_realization()
            self.realization_results.append(result)
            
            current_tau += self.tau_range['step']
        
        return self.realization_results

    def enable_step_mode(self, breakpoint_events: List[str] = None):
        """Включение пошагового режима"""
        self.step_controller.enable_step_mode(breakpoint_events)

    def save_results(self, filename: str):
        """Сохранение результатов в файл"""
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.realization_results, f, indent=2, ensure_ascii=False)
        
        print(f"Результаты сохранены в {filename}")