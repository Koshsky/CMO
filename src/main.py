import math
import random
import yaml
import os
from typing import Dict, List, Any

class SimulationSystem:
    def __init__(self, config_path: str = "config.yaml"):
        # Загрузка конфигурации
        self.config = self.load_config(config_path)
        
        # Параметры системы из конфига
        self.LAM1 = self.config['system']['LAM1']
        self.LAM2 = self.config['system']['LAM2']
        self.TAU1 = self.config['system']['TAU1']
        self.TAU2 = self.config['system']['TAU2']
        self.DTAU = self.config['system']['DTAU']
        self.KMIN = self.config['system']['KMIN']
        
        # Диапазоны генерации заявок
        self.TAY1 = self.config['sources']['TAY1']
        self.TAY2 = self.config['sources']['TAY2']
        
        # Инициализация состояния системы
        self.initialize_system()
        
    def initialize_system(self):
        """Инициализация состояния системы"""
        self.KOL = 0
        self.KOTK = 0
        self.KOBR = 0
        self.TOSV = [float('inf'), float('inf')]
        self.TOG = [0.0, 0.0]
        self.INDBUF = 0
        
        # Буфер (4 места) - храним номер источника (0 - свободно, 1 - И1, 2 - И2)
        self.buffer = [0] * 4
        
        # Календарь событий
        self.TPOST = [0.0, 0.0]
        self.current_time = 0.0
        
        # Статистика
        self.source_stats = [
            {'generated': 0, 'rejected': 0, 'processed': 0},
            {'generated': 0, 'rejected': 0, 'processed': 0}
        ]
        
        # Указатели
        self.device_pointer = 0
        self.TAUOB = self.TAU1
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Загрузка конфигурации из YAML файла"""
        if not os.path.exists(config_path):
            # Создаем конфиг по умолчанию
            default_config = {
                'system': {
                    'LAM1': 1.0,
                    'LAM2': 1.0,
                    'TAU1': 1.0,
                    'TAU2': 2.0,
                    'DTAU': 0.2,
                    'KMIN': 3000
                },
                'sources': {
                    'TAY1': 0.1,
                    'TAY2': 0.5
                },
                'step_by_step': {
                    'enabled': True,
                    'max_steps': 50
                }
            }
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(default_config, f, default_flow_style=False, allow_unicode=True)
            return default_config
        
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def uniform_random(self, a: float, b: float) -> float:
        """Равномерное распределение для генерации заявок"""
        return a + (b - a) * random.random()
    
    def exponential_random(self, mu: float) -> float:
        """Экспоненциальное распределение для времени обслуживания"""
        return -1.0 / mu * math.log(random.random() + 1e-10)
    
    def generate_first_requests(self):
        """Генерация первых заявок от каждого источника"""
        self.TPOST[0] = self.uniform_random(self.TAY1, self.TAY2)
        self.TPOST[1] = self.uniform_random(self.TAY1, self.TAY2)
    
    def find_next_event(self):
        """Поиск ближайшего события"""
        events = [
            (self.TPOST[0], 1, "Поступление от И1"),
            (self.TPOST[1], 2, "Поступление от И2"),
            (self.TOSV[0], 3, "Освобождение П1"),
            (self.TOSV[1], 4, "Освобождение П2")
        ]
        
        active_events = [(time, event_type, desc) for time, event_type, desc in events 
                        if time != float('inf')]
        
        if not active_events:
            return None, None, None
            
        return min(active_events, key=lambda x: x[0])
    
    def add_to_buffer(self, source_num: int) -> bool:
        """Добавление заявки в буфер в порядке поступления"""
        if self.INDBUF < 4:
            self.buffer[self.INDBUF] = source_num
            self.INDBUF += 1
            return True
        return False
    
    def remove_lowest_priority_from_buffer(self) -> int:
        """Удаление заявки с наименьшим приоритетом (наибольший номер источника)"""
        if self.INDBUF == 0:
            return 0
            
        max_source = max(self.buffer[:self.INDBUF])
        max_idx = self.buffer.index(max_source)
        
        removed_source = self.buffer[max_idx]
        
        for i in range(max_idx, self.INDBUF - 1):
            self.buffer[i] = self.buffer[i + 1]
        
        self.buffer[self.INDBUF - 1] = 0
        self.INDBUF -= 1
        
        return removed_source
    
    def get_highest_priority_from_buffer(self) -> int:
        """Получение заявки с наивысшим приоритетом из буфера"""
        if self.INDBUF == 0:
            return 0
        return min(self.buffer[:self.INDBUF])
    
    def remove_from_buffer(self, source_num: int):
        """Удаление конкретной заявки из буфера"""
        if self.INDBUF == 0:
            return
            
        for i in range(self.INDBUF):
            if self.buffer[i] == source_num:
                for j in range(i, self.INDBUF - 1):
                    self.buffer[j] = self.buffer[j + 1]
                self.buffer[self.INDBUF - 1] = 0
                self.INDBUF -= 1
                return
    
    def select_device(self) -> int:
        """Выбор прибора по кольцу"""
        device = self.device_pointer
        self.device_pointer = (self.device_pointer + 1) % 2
        return device
    
    def process_arrival(self, source_num: int, verbose: bool = True):
        """Обработка поступления заявки"""
        source_idx = source_num - 1
        
        if verbose:
            print(f"📨 Поступление заявки от источника {source_num}")
        
        self.KOL += 1
        self.source_stats[source_idx]['generated'] += 1
        
        free_device = None
        for i in range(2):
            if self.TOSV[i] == float('inf'):
                free_device = i
                break
        
        if free_device is not None:
            service_time = self.exponential_random(1.0/self.TAUOB)
            self.TOSV[free_device] = self.current_time + service_time
            self.source_stats[source_idx]['processed'] += 1
            self.KOBR += 1
            if verbose:
                print(f"  ⚡ Заявка сразу на прибор {free_device + 1}, время обслуживания: {service_time:.3f}")
        else:
            if not self.add_to_buffer(source_num):
                removed_source = self.remove_lowest_priority_from_buffer()
                if removed_source > 0:
                    self.source_stats[removed_source - 1]['rejected'] += 1
                    self.KOTK += 1
                    if verbose:
                        print(f"  ❌ Отказ заявке от источника {removed_source}")
                
                self.add_to_buffer(source_num)
                if verbose:
                    print(f"  📥 Новая заявка добавлена в буфер вместо удаленной")
            else:
                if verbose:
                    print(f"  📥 Заявка добавлена в буфер")
        
        next_arrival = self.uniform_random(self.TAY1, self.TAY2)
        self.TPOST[source_idx] = self.current_time + next_arrival
    
    def process_departure(self, device_num: int, verbose: bool = True):
        """Обработка освобождения прибора"""
        if verbose:
            print(f"🔓 Освобождение прибора {device_num + 1}")
        
        if self.INDBUF > 0:
            source_num = self.get_highest_priority_from_buffer()
            if source_num > 0:
                self.remove_from_buffer(source_num)
                
                service_time = self.exponential_random(1.0/self.TAUOB)
                self.TOSV[device_num] = self.current_time + service_time
                self.source_stats[source_num - 1]['processed'] += 1
                self.KOBR += 1
                
                if verbose:
                    print(f"  ⚡ Заявка от И{source_num} взята на обслуживание, время: {service_time:.3f}")
        else:
            self.TOSV[device_num] = float('inf')
            if verbose:
                print("  💤 Прибор свободен - буфер пуст")
    
    def format_buffer_display(self) -> List[str]:
        """Форматирование буфера для отображения"""
        display = []
        for i in range(4):
            if i < self.INDBUF:
                source = self.buffer[i]
                display.append(f"[И{source}]")
            else:
                display.append("[  ]")
        return display
    
    def print_state(self):
        """Вывод текущего состояния системы"""
        print(f"\n{'='*60}")
        print(f"🕒 Время: {self.current_time:.3f}")
        
        print("📅 Календарь событий:")
        print("+-----------+-----------+")
        print("|   Событие |   Время   |")
        print("+-----------+-----------+")
        events = [
            ("И1", self.TPOST[0]),
            ("И2", self.TPOST[1]), 
            ("П1", self.TOSV[0]),
            ("П2", self.TOSV[1])
        ]
        
        for event_name, event_time in events:
            time_str = f"{event_time:.3f}" if event_time != float('inf') else "---"
            print(f"|   {event_name:<6} |   {time_str:<7} |")
        print("+-----------+-----------+")
        
        print("\n📦 Буфер:")
        buffer_display = self.format_buffer_display()
        print("  " + " ".join(buffer_display))
        
        print(f"\n📊 Статистика:")
        print(f"  Всего заявок: {self.KOL}")
        print(f"  Обработано: {self.KOBR}")
        print(f"  Отказов: {self.KOTK}")
        print(f"  В буфере: {self.INDBUF}/4")

        print(f"\n{'-'*60}")
    
    def print_final_stats(self):
        """Вывод финальной статистики"""
        print("\n" + "="*70)
        print("🎯 ФИНАЛЬНАЯ СТАТИСТИКА")
        print("="*70)
        
        print(f"📈 Общие показатели:")
        print(f"   Всего заявок: {self.KOL}")
        print(f"   Обработано: {self.KOBR}")
        print(f"   Отказов: {self.KOTK}")
        print(f"   Время моделирования: {self.current_time:.3f}")
        
        print(f"\n📊 Статистика по источникам:")
        for i in range(2):
            stats = self.source_stats[i]
            rejection_rate = (stats['rejected'] / stats['generated'] * 100) if stats['generated'] > 0 else 0
            print(f"   Источник {i+1}:")
            print(f"     Сгенерировано: {stats['generated']}")
            print(f"     Обработано: {stats['processed']}")
            print(f"     Отказов: {stats['rejected']}")
            print(f"     Процент отказов: {rejection_rate:.2f}%")
        
        print(f"\n⚙️  Параметры системы:")
        print(f"   TAUOB: {self.TAUOB}")
        print(f"   KMIN: {self.KMIN}")
        print("="*70)
    
    def run_step_by_step(self):
        """Запуск пошагового режима"""
        print("🚀 НАЧАЛО МОДЕЛИРОВАНИЯ (Пошаговый режим)")
        print("📋 Параметры системы:")
        print(f"   TAUOB = {self.TAUOB}")
        print(f"   KMIN = {self.KMIN}")
        print(f"   Диапазон генерации: [{self.TAY1}, {self.TAY2}]")
        
        self.generate_first_requests()
        self.print_state()
        
        step = 0
        max_steps = self.config['step_by_step'].get('max_steps', 50)
        
        while self.KOL < self.KMIN and step < max_steps:
            step += 1
            input(f"\n⏳ Шаг {step}. Нажмите Enter для продолжения...")
            
            next_event = self.find_next_event()
            if next_event[0] is None:
                print("❌ Нет активных событий!")
                break
                
            event_time, event_type, event_desc = next_event
            self.current_time = event_time
            
            print(f"\n🎯 Событие: {event_desc}")
            
            if event_type in [1, 2]:
                self.process_arrival(event_type, verbose=True)
            else:
                self.process_departure(event_type - 3, verbose=True)
            
            self.print_state()
        
        return step
    
    def run_automatic(self):
        """Запуск автоматического прогона до KMIN"""
        print(f"\n🔄 ЗАПУСК АВТОМАТИЧЕСКОГО ПРОГОНА ДО KMIN={self.KMIN}")
        print("   (вывод событий отключен для скорости)")
        
        progress_interval = max(1, self.KMIN // 20)  # Показывать прогресс каждые 5%
        
        while self.KOL < self.KMIN:
            next_event = self.find_next_event()
            if next_event[0] is None:
                print("❌ Нет активных событий!")
                break
                
            event_time, event_type, event_desc = next_event
            self.current_time = event_time
            
            # Показываем прогресс
            if self.KOL % progress_interval == 0:
                print(f"   Прогресс: {self.KOL}/{self.KMIN} заявок ({self.KOL/self.KMIN*100:.1f}%)")
            
            # Обработка события без вывода деталей
            if event_type in [1, 2]:
                self.process_arrival(event_type, verbose=False)
            else:
                self.process_departure(event_type - 3, verbose=False)
        
        print(f"✅ Автоматический прогон завершен!")
    
    def run_simulation(self):
        """Основной метод запуска симуляции"""
        # Пошаговый режим
        steps_completed = self.run_step_by_step()
        
        # Проверяем, нужно ли продолжать автоматически
        if self.KOL < self.KMIN:
            print(f"\n📊 После {steps_completed} шагов:")
            print(f"   Обработано заявок: {self.KOL}/{self.KMIN}")
            
            if steps_completed >= self.config['step_by_step'].get('max_steps', 50):
                response = input("\nПродолжить автоматически до KMIN? (y/n): ").strip().lower()
                if response == 'y':
                    self.run_automatic()
                else:
                    print("Завершение по запросу пользователя.")
            else:
                print("Завершение пошагового режима.")
        
        # Вывод финальной статистики
        self.print_final_stats()

# Создаем конфигурационный файл
def create_config():
    config_content = """# Конфигурация системы массового обслуживания
system:
  LAM1: 1.0      # Интенсивность источника 1
  LAM2: 1.0      # Интенсивность источника 2  
  TAU1: 1.0      # Начальное значение TAU
  TAU2: 2.0      # Конечное значение TAU
  DTAU: 0.2      # Шаг изменения TAU
  KMIN: 3000     # Минимальное количество заявок для завершения

sources:
  TAY1: 0.1      # Минимальное время между заявками
  TAY2: 0.5      # Максимальное время между заявками

step_by_step:
  enabled: true  # Включить пошаговый режим
  max_steps: 50  # Максимальное количество шагов для демонстрации
"""
    with open("config.yaml", "w", encoding="utf-8") as f:
        f.write(config_content)

if __name__ == "__main__":
    # Создаем конфиг если его нет
    if not os.path.exists("config.yaml"):
        create_config()
        print("📁 Создан файл config.yaml с настройками по умолчанию")
    
    # Запускаем систему
    system = SimulationSystem("config.yaml")
    system.run_simulation()