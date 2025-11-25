"""
Основной файл для моделирования СМО вариант №6
Обновлен для работы с новой архитектурой системы
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
        
        # Извлекаем конфигурацию для варианта №6
        variant_config = config.get('variant_6', config)  # Поддержка старого и нового формата
        
        print("=== МОДЕЛИРОВАНИЕ СМО ВАРИАНТ №6 ===")
        print("Конфигурация системы:")
        print(f"- Источники: {variant_config['sources']['count']} ({variant_config['sources']['distribution']})")
        
        # Показываем интервалы для источников
        if 'intervals' in variant_config['sources']:
            intervals = variant_config['sources']['intervals']
            print(f"  Интервалы: [{intervals['min']:.1f}, {intervals['max']:.1f}]")
        else:
            print("  Интервалы: индивидуальные для каждого источника")
        
        print(f"- Приборы: {variant_config['device'].get('count', 2)} ({variant_config['device']['distribution']})")
        print(f"- Буфер: {variant_config['buffer']['size']} мест")
        print(f"- Дисциплины: {variant_config['buffer']['disciplines']}")
        print(f"- Минимальное кол-во заявок: {variant_config['simulation']['min_requests']}")
        
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
        
        # Итоговая статистика по всем реализациям (разным TAU)
        for i, result in enumerate(results):
            print(f"\n--- Реализация {i+1} (TAU={result['tau']}) ---")
            system_stats = result['system_stats']
            print(f"Общее количество заявок: {system_stats['total_requests']}")
            print(f"Обработано: {system_stats['total_processed']}")
            print(f"Отказов: {system_stats['total_rejected']}")
            print(f"Вероятность отказа: {system_stats['total_reject_prob']:.4f}")
            
            # Статистика по источникам
            print("\nСтатистика по источникам:")
            for source_stats in result['sources_stats']:
                source_name = source_stats['source_name']
                reject_prob = source_stats['rejected'] / source_stats['total'] if source_stats['total'] > 0 else 0
                print(f"  {source_name}: сгенерировано {source_stats['total']}, "
                      f"обработано {source_stats['processed']}, "
                      f"отказов {source_stats['rejected']} "
                      f"(P_отк={reject_prob:.4f}), "
                      f"ср.время ожидания: {source_stats['avg_wait_time']:.4f}")
            
            # Статистика по приборам
            print("\nСтатистика по приборам:")
            for device_stats in result['devices_stats']:
                device_name = device_stats['device_name']
                print(f"  {device_name}: обработано {device_stats['processed']} заявок")
        
        # Визуализация результатов (графики)
        visualizer = ResultsVisualizer()
        
        # Выводим сводную таблицу для последней реализации
        if results:
            print("\n" + "="*80)
            print("СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ (последняя реализация)")
            print("="*80)
            visualizer.print_results_table(results[-1])
        
        # Комплексный анализ всех реализаций
        print("\nПостроение графиков анализа...")
        events_data = None
        if choice == "2":
            events_data = smo_system.step_controller.get_event_history()
        
        visualizer.plot_comprehensive_analysis(results, events_data=events_data)
        
        # Сохраняем результаты
        smo_system.save_results('data/output/results_v6.json')
        
        print("\nМоделирование завершено успешно!")
        
    except FileNotFoundError as e:
        print(f"Ошибка загрузки конфигурации: {e}")
        print("Убедитесь, что файл config/system_config.json существует и имеет правильный формат")
    except KeyError as e:
        print(f"Ошибка в структуре конфигурации: отсутствует ключ {e}")
        print("Проверьте правильность структуры JSON-конфигурации")
    except Exception as e:
        print(f"Неожиданная ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()