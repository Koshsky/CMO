"""
Полная реализация системы массового обслуживания для варианта №6
"""

import json
from typing import Dict, Any, List, Optional
from src.utils.step_mode import StepModeController
from src.utils.distributions import uniform_distribution, exponential_distribution

class Source:
    """Класс источника заявок"""
    def __init__(self, source_id: int, params: Dict[str, float]):
        self.id = source_id
        self.params = params
        self.generated_count = 0
        self.processed_count = 0
        self.rejected_count = 0
        self.total_wait_time = 0.0
        self.next_arrival_time = 0.0

    def generate_interval(self) -> float:
        """Генерация интервала между заявками по закону ИЗ2 (равномерный)"""
        return uniform_distribution(self.params['min_interval'], self.params['max_interval'])

    def __str__(self):
        return f"И{self.id+1}"

class Device:
    """Класс прибора (обработчика)"""
    def __init__(self, device_id: int, service_lambda: float):
        self.id = device_id
        self.service_lambda = service_lambda
        self.is_busy = False
        self.current_source = None
        self.processed_count = 0
        self.finish_time = float('inf')

    def generate_service_time(self) -> float:
        """Генерация времени обслуживания по закону ПЗ1 (экспоненциальный)"""
        return exponential_distribution(self.service_lambda)

    def __str__(self):
        if self.is_busy:
            return f"П{self.id+1}[И{self.current_source.id+1}]"
        else:
            return f"П{self.id+1}[...]"

class SMOSystem:
    """Полная реализация СМО для варианта №6"""
    
    def __init__(self, config):
        self.config = config
        self.step_controller = StepModeController()
        self.initialize_system()
    
    def initialize_system(self):
        """Инициализация системы согласно блок-схеме"""
        self.buffer_capacity = self.config['buffer']['size']
        self.min_requests = self.config['simulation']['min_requests']
        
        # Инициализация источников
        self.sources = []
        sources_config = self.config['sources']
        for i in range(sources_config['count']):
            source_params = sources_config['params'][f'source_{i}']
            self.sources.append(Source(i, source_params))
        
        # Инициализация приборов - с проверкой наличия count
        self.devices = []
        device_config = self.config['device']
        
        # Определяем количество приборов (по умолчанию 2 для варианта №6)
        devices_count = device_config.get('count', 2)
        
        for i in range(devices_count):
            self.devices.append(Device(i, device_config['lambda']))
        
        # Дисциплины
        self.disciplines = self.config['buffer']['disciplines']
        
        # Параметры моделирования
        self.tau_range = self.config['device']['tau_range']
        self.current_tau = self.tau_range['min']
        self.current_time = 0.0
        self.realization_results = []
        
        print(f"Система инициализирована: {len(self.sources)} источников, {len(self.devices)} приборов")

    def initialize_realization(self):
        """Инициализация переменных для одной реализации"""
        self.current_time = 0.0
        
        # Сброс состояний источников
        for source in self.sources:
            source.generated_count = 0
            source.processed_count = 0
            source.rejected_count = 0
            source.total_wait_time = 0.0
            source.next_arrival_time = source.generate_interval()
        
        # Сброс состояний приборов
        for device in self.devices:
            device.is_busy = False
            device.current_source = None
            device.processed_count = 0
            device.finish_time = float('inf')
            
        # Буфер
        self.INDBUF = 0
        self.BUFT = [0.0] * self.buffer_capacity
        self.BUFN = [-1] * self.buffer_capacity  # -1 означает пустой слот
        
        # Вспомогательные переменные
        self.KOTK = 0  # Общий счетчик отказов
        self.TOG = [0.0] * len(self.sources)  # Суммарное время ожидания по источникам
        
        # Дисциплина Д2Б5 (пакетная)
        self.current_packet = -1
        self.packet_empty = True
        
        # Дисциплина Д2П2 (выбор прибора по кольцу)
        self.device_pointer = 0

    def boos_block(self) -> int:
        """БООС - определение типа следующего события"""
        # Ближайшее поступление заявки
        next_arrival = min(source.next_arrival_time for source in self.sources)
        arrival_source_id = next(i for i, source in enumerate(self.sources) 
                               if source.next_arrival_time == next_arrival)
        
        # Ближайшее освобождение прибора
        device_finish_times = [device.finish_time for device in self.devices]
        next_device_free = min(device_finish_times) if device_finish_times else float('inf')
        
        if next_arrival <= next_device_free:
            return arrival_source_id + 1  # 1..N - события от источников
        else:
            return len(self.sources) + 1  # N+1 - освобождение прибора

    def process_event(self, event_type: int):
        """Обработка события согласно блок-схеме"""
        event_data = self._get_system_state()
        
        if 1 <= event_type <= len(self.sources):
            # Событие от источника
            source_id = event_type - 1
            source = self.sources[source_id]
            
            event_data.update({
                'event_type': 'arrival',
                'source': source_id,
                'source_name': f'И{source_id+1}',
                'arrival_time': source.next_arrival_time
            })
            self.step_controller.wait_for_step('arrival', event_data)
            
            self.bas_block(source)
            
        elif event_type == len(self.sources) + 1:
            # Событие освобождения прибора
            device = self.find_device_to_free()
            
            event_data.update({
                'event_type': 'device_free',
                'device': device.id,
                'device_name': f'П{device.id+1}',
                'device_free_time': device.finish_time
            })
            self.step_controller.wait_for_step('device_finish', event_data)
            
            self.bas3_block(device)

    def bas_block(self, source: Source):
        """БАС1/БАС2 - анализ состояния при поступлении заявки"""
        free_device = self.find_free_device()
        
        if free_device is not None:
            # Есть свободный прибор - обслуживаем сразу
            self.bms32_block(source, free_device)
        elif self.INDBUF < self.buffer_capacity:
            # Все приборы заняты, но есть место в буфере
            self.bms12_block(source)
        else:
            # Все приборы заняты и буфер полон - отказ с выбиванием
            self.bms11_block(source)

    def find_free_device(self) -> Optional[Device]:
        """Поиск свободного прибора"""
        for device in self.devices:
            if not device.is_busy:
                return device
        return None

    def find_device_to_free(self) -> Device:
        """Определение прибора, который освободился"""
        # Находим прибор с минимальным временем освобождения
        min_finish_time = float('inf')
        result_device = self.devices[0]  # По умолчанию берем первый
        
        for device in self.devices:
            if device.finish_time < min_finish_time:
                min_finish_time = device.finish_time
                result_device = device
        return result_device

    def bas3_block(self, device: Device):
        """БАС3 - анализ состояния при освобождении прибора"""
        device.is_busy = False
        device.current_source = None
        
        if self.INDBUF > 0:
            # В буфере есть заявки - выбираем следующую
            self.bms31_block(device)
        else:
            # Буфер пуст - прибор остается свободным
            device.finish_time = float('inf')

    def bms11_block(self, source: Source):
        """БМС11/БМС21 - отказ с выбиванием по дисциплине Д10О2"""
        victim_index = self.find_victim_for_rejection()
        victim_source_id = self.BUFN[victim_index]
        
        self.KOTK += 1
        source.rejected_count += 1
        
        # Заменяем выбитую заявку на новую
        self.BUFT[victim_index] = source.next_arrival_time
        self.BUFN[victim_index] = source.id
        
        # Генерация следующей заявки и обновление счетчиков
        source.generated_count += 1
        source.next_arrival_time = self.current_time + source.generate_interval()
        
        event_data = self._get_system_state()
        event_data.update({
            'event_type': 'buffer_reject',
            'source': source.id,
            'source_name': f'И{source.id+1}',
            'rejected_source': victim_source_id,
            'rejected_source_name': f'И{victim_source_id+1}',
            'buffer_position': victim_index,
            'total_rejects': self.KOTK,
            'reason': f'Выбивание заявки И{victim_source_id+1}'
        })
        self.step_controller.wait_for_step('buffer_reject', event_data)

    def bms12_block(self, source: Source):
        """БМС12/БМС22 - запись в буфер по дисциплине Д10З2"""
        write_position = -1
        for i in range(self.buffer_capacity):
            if self.BUFN[i] == -1:  # Пустой слот
                write_position = i
                break
        
        if write_position >= 0:
            self.BUFT[write_position] = source.next_arrival_time
            self.BUFN[write_position] = source.id
            self.INDBUF += 1
        
        # Обновление источника
        source.generated_count += 1
        source.next_arrival_time = self.current_time + source.generate_interval()
        
        event_data = self._get_system_state()
        event_data.update({
            'event_type': 'buffer_write',
            'source': source.id,
            'source_name': f'И{source.id+1}',
            'buffer_position': write_position,
            'buffer_size': self.INDBUF,
            'reason': 'Все приборы заняты, заявка поставлена в буфер'
        })
        self.step_controller.wait_for_step('buffer_write', event_data)

    def bms31_block(self, device: Device):
        """БМС31 - выборка из буфера на обслуживание по дисциплине Д2Б5"""
        selected_index = self.select_request_from_buffer()
        
        if selected_index >= 0:
            source_id = self.BUFN[selected_index]
            source = self.sources[source_id]
            arrival_time = self.BUFT[selected_index]
            
            # Расчет времени ожидания
            wait_time = self.current_time - arrival_time
            source.total_wait_time += wait_time
            self.TOG[source_id] += wait_time
            
            # Обслуживание заявки
            service_time = device.generate_service_time()
            device.finish_time = self.current_time + service_time
            device.is_busy = True
            device.current_source = source
            
            # Удаление из буфера и обновление счетчиков
            self.remove_from_buffer(selected_index)
            device.processed_count += 1
            source.processed_count += 1
            
            event_data = self._get_system_state()
            event_data.update({
                'event_type': 'buffer_select',
                'selected_source': source_id,
                'selected_source_name': f'И{source_id+1}',
                'device': device.id,
                'device_name': f'П{device.id+1}',
                'buffer_position': selected_index,
                'wait_time': wait_time,
                'service_time': service_time,
                'current_packet': self.current_packet
            })
            self.step_controller.wait_for_step('buffer_select', event_data)
            
            event_data.update({
                'event_type': 'device_start', 
                'source': source_id,
                'source_name': f'И{source_id+1}',
                'device': device.id,
                'device_name': f'П{device.id+1}',
                'finish_time': device.finish_time,
                'from_buffer': True
            })
            self.step_controller.wait_for_step('device_start', event_data)

    def bms32_block(self, source: Source, device: Device):
        """БМС32 - обслуживание без буфера при свободном приборе"""
        # Обслуживание заявки напрямую
        service_time = device.generate_service_time()
        device.finish_time = self.current_time + service_time
        device.is_busy = True
        device.current_source = source
        
        # Обновление счетчиков
        device.processed_count += 1
        source.processed_count += 1
        source.generated_count += 1
        
        # Генерация следующей заявки
        source.next_arrival_time = self.current_time + source.generate_interval()
        
        event_data = self._get_system_state()
        event_data.update({
            'event_type': 'device_start',
            'source': source.id,
            'source_name': f'И{source.id+1}',
            'device': device.id,
            'device_name': f'П{device.id+1}',
            'service_time': service_time,
            'finish_time': device.finish_time,
            'direct_service': True
        })
        self.step_controller.wait_for_step('device_start', event_data)

    def find_victim_for_rejection(self) -> int:
        """Поиск заявки для выбивания по приоритету источника (Д10О2)"""
        candidates = []
        
        for i in range(self.buffer_capacity):
            if self.BUFN[i] != -1:  # Занятый слот
                source_id = self.BUFN[i]
                priority = source_id + 1  # Источник 0 имеет высший приоритет (1), источник 1 - низший (2)
                candidates.append((priority, self.BUFT[i], i, source_id))
        
        # Сортируем по приоритету (возрастание) и времени поступления (старые first)
        candidates.sort(key=lambda x: (x[0], x[1]))
        return candidates[0][2] if candidates else 0

    def select_request_from_buffer(self) -> int:
        """Выбор заявки из буфера по пакетной дисциплине Д2Б5"""
        if self.current_packet == -1 or self.packet_empty:
            self.select_new_packet()
        
        # Ищем заявку текущего пакета
        for i in range(self.buffer_capacity):
            if self.BUFN[i] == self.current_packet:
                self.packet_empty = False
                return i
        
        # Если заявок текущего пакета нет, выбираем новый пакет
        self.select_new_packet()
        for i in range(self.buffer_capacity):
            if self.BUFN[i] == self.current_packet:
                return i
        
        return -1  # Буфер пуст

    def select_new_packet(self):
        """Выбор нового пакета для обслуживания"""
        old_packet = self.current_packet
        
        # Ищем источники, имеющие заявки в буфере
        available_sources = set()
        for i in range(self.buffer_capacity):
            if self.BUFN[i] != -1:
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

    def remove_from_buffer(self, index: int):
        """Удаление заявки из буфера"""
        if 0 <= index < self.buffer_capacity:
            self.BUFT[index] = 0.0
            self.BUFN[index] = -1
            self.INDBUF = max(0, self.INDBUF - 1)

    def _get_system_state(self) -> Dict[str, Any]:
        """Получение текущего состояния системы"""
        buffer_state = []
        for i in range(self.buffer_capacity):
            if self.BUFN[i] != -1:
                buffer_state.append(f"{i+1}:И{self.BUFN[i]+1}")
            else:
                buffer_state.append(f"{i+1}:__")
        
        # Состояние приборов (обработчиков)
        devices_state = []
        for device in self.devices:
            if device.is_busy and device.current_source is not None:
                devices_state.append(f"П{device.id+1}[И{device.current_source.id+1}]")
            else:
                devices_state.append(f"П{device.id+1}[...]")
        
        # Следующие заявки от источников
        next_arrivals = []
        for i, source in enumerate(self.sources):
            next_arrivals.append(f"И{i+1}={source.next_arrival_time:.3f}")
        
        # СТАТИСТИКА ПО ОБРАБОТЧИКАМ - сколько заявок обработал каждый прибор
        devices_processed = []
        for i, device in enumerate(self.devices):
            devices_processed.append(f"П{i+1}[{device.processed_count}]")
        
        return {
            'time': self.current_time,
            'buffer_state': buffer_state,
            'buffer_size': self.INDBUF,
            'buffer_capacity': self.buffer_capacity,
            'devices_state': devices_state,
            'next_arrivals': next_arrivals,
            'devices_processed': devices_processed,  # Статистика по обработчикам
            'total_rejected': self.KOTK,
            'current_packet': self.current_packet,
            'tau': self.current_tau
        }

    def run_realization(self) -> Dict[str, Any]:
        """Запуск одной реализации моделирования"""
        self.initialize_realization()
        
        iteration = 0
        max_iterations = 100000
        
        # Продолжаем пока все источники не сгенерируют минимальное количество заявок
        while (all(source.generated_count >= self.min_requests for source in self.sources) is False 
               and iteration < max_iterations):
            iteration += 1
            
            event_type = self.boos_block()
            
            if event_type == 0:
                break
                
            # Обновление текущего времени
            if 1 <= event_type <= len(self.sources):
                source_id = event_type - 1
                self.current_time = self.sources[source_id].next_arrival_time
            else:
                device = self.find_device_to_free()
                self.current_time = device.finish_time
            
            self.process_event(event_type)
        
        return self.calculate_results()

    def calculate_results(self) -> Dict[str, Any]:
        """Расчет результатов реализации"""
        total_requests = sum(source.generated_count for source in self.sources)
        total_processed = sum(source.processed_count for source in self.sources)
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
            'devices_stats': [],
            'realization_data': self._get_system_state()
        }
        
        # Статистика по источникам
        for source in self.sources:
            avg_wait_time = source.total_wait_time / source.processed_count if source.processed_count > 0 else 0
            
            results['sources_stats'].append({
                'source_id': source.id,
                'source_name': f'И{source.id+1}',
                'total': source.generated_count,
                'processed': source.processed_count,
                'rejected': source.rejected_count,
                'avg_wait_time': avg_wait_time
            })
        
        # Статистика по приборам
        for device in self.devices:
            results['devices_stats'].append({
                'device_id': device.id,
                'device_name': f'П{device.id+1}',
                'processed': device.processed_count,
                'utilization': device.processed_count > 0
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