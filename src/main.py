"""
Основной файл для моделирования СМО вариант №6
"""

import sys
import os

# Добавляем путь к src для импортов
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from src.utils.config_loader import load_config
from src.visualization.plots import ResultsVisualizer
from src.models.system import SMOSystem

def main():
    """Главная функция запуска моделирования"""
    
    try:
        # Загружаем конфигурацию
        config = load_config('config/system_config.json')
        variant_config = config['variant_6']
        
        print("=== МОДЕЛИРОВАНИЕ СМО ВАРИАНТ №6 ===")
        print("Конфигурация системы:")
        print(f"- Источники: {variant_config['sources']['count']} ({variant_config['sources']['distribution']})")
        print(f"- Прибор: {variant_config['device']['distribution']}")
        print(f"- Буфер: {variant_config['buffer']['size']} мест")
        print(f"- Дисциплины: {variant_config['buffer']['disciplines']}")
        
        # Создаем систему
        smo_system = SMOSystem(variant_config)
        
        # Спрашиваем режим работы
        print("\nВыберите режим работы:")
        print("1 - Автоматический режим")
        print("2 - Пошаговый режим")
        
        choice = input("Ваш выбор (1/2): ").strip()
        
        if choice == "2":
            # Пошаговый режим
            print("\nВыберите события для остановки:")
            print("a - все события")
            print("b - только ключевые (запись, отказ, обслуживание)")
            print("c - настроить вручную")
            
            mode_choice = input("Ваш выбор (a/b/c): ").strip().lower()
            
            if mode_choice == "a":
                smo_system.enable_step_mode()  # все события
            elif mode_choice == "b":
                smo_system.enable_step_mode(['arrival', 'buffer_write', 'buffer_reject', 'device_start', 'device_finish'])
            elif mode_choice == "c":
                print("Доступные события: arrival, buffer_write, buffer_reject, device_start, device_finish, buffer_select, packet_change")
                events = input("Введите события через запятую: ").strip().split(',')
                events = [e.strip() for e in events if e.strip()]
                smo_system.enable_step_mode(events)
            else:
                smo_system.enable_step_mode()  # по умолчанию все события
        
        # Запускаем моделирование
        print("\nЗапуск моделирования...")
        results = smo_system.run_simulation(step_mode=(choice == "2"))
        
        # Выводим результаты
        print("\n=== РЕЗУЛЬТАТЫ МОДЕЛИРОВАНИЯ ===")
        
        # Итоговая статистика
        for i, result in enumerate(results):
            print(f"\n--- Реализация {i+1} (TAU={result['tau']}) ---")
            system_stats = result['system_stats']
            print(f"Общее количество заявок: {system_stats['total_requests']}")
            print(f"Обработано: {system_stats['total_processed']}")
            print(f"Отказов: {system_stats['total_rejected']}")
            print(f"Вероятность отказа: {system_stats['total_reject_prob']:.4f}")
            
            # Статистика по источникам
            for j, source_stats in enumerate(result['sources_stats']):
                print(f"Источник {j+1}: обработано {source_stats['processed']}, среднее время ожидания: {source_stats['avg_wait_time']:.4f}")
        
        # Визуализация результатов (графики)
        visualizer = ResultsVisualizer()
        visualizer.plot_comprehensive_analysis(results, 
                                            events_data=smo_system.step_controller.get_event_history() if choice == "2" else None)
        
        # Сохраняем результаты
        smo_system.save_results('data/output/results_v6.json')
        
    except FileNotFoundError as e:
        print(f"Ошибка: {e}")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")

if __name__ == "__main__":
    main()