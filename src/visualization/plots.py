"""
Улучшенный модуль для визуализации результатов моделирования
Адаптирован для работы с переменным количеством источников и приборов
"""

import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Any, Optional
import matplotlib.gridspec as gridspec

class ResultsVisualizer:
    """Улучшенный класс для визуализации результатов СМО"""
    
    def __init__(self):
        plt.style.use('seaborn-v0_8')
        self.figsize = (16, 12)
        self.colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#4ECDC4', '#FF6B6B', '#45B7D1', '#96CEB4']
    
    def print_results_table(self, results: Dict[str, Any]):
        """
        Вывод улучшенной сводной таблицы результатов
        Адаптировано для переменного количества источников и приборов
        """
        print("\n" + "="*100)
        print("СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ МОДЕЛИРОВАНИЯ")
        print("="*100)
        
        if 'sources_stats' in results:
            print(f"\nХАРАКТЕРИСТИКИ ИСТОЧНИКОВ ({len(results['sources_stats'])} источников):")
            print("-" * 100)
            print(f"{'Источник':<12} {'Всего':<8} {'Обработано':<10} {'Отказов':<8} {'M[T_ож]':<12} {'Вер.отказа':<10}")
            print("-" * 100)
            
            for stats in results['sources_stats']:
                source_name = stats.get('source_name', f"И{stats['source_id']+1}")
                reject_prob = stats['rejected'] / stats['total'] if stats['total'] > 0 else 0
                print(f"{source_name:<12} {stats['total']:<8} {stats['processed']:<10} "
                      f"{stats['rejected']:<8} {stats['avg_wait_time']:<12.4f} {reject_prob:<10.4f}")
        
        if 'devices_stats' in results:
            print(f"\nХАРАКТЕРИСТИКИ ПРИБОРОВ ({len(results['devices_stats'])} приборов):")
            print("-" * 60)
            print(f"{'Прибор':<10} {'Обработано':<10} {'Загрузка':<10}")
            print("-" * 60)
            
            for stats in results['devices_stats']:
                device_name = stats.get('device_name', f"П{stats['device_id']+1}")
                utilization = "Да" if stats['utilization'] else "Нет"
                print(f"{device_name:<10} {stats['processed']:<10} {utilization:<10}")
        
        if 'system_stats' in results:
            print(f"\nОБЩАЯ СТАТИСТИКА СИСТЕМЫ:")
            print("-" * 60)
            sys_stats = results['system_stats']
            print(f"Общее кол-во заявок: {sys_stats.get('total_requests', 0)}")
            print(f"Общее кол-во обработанных: {sys_stats.get('total_processed', 0)}")
            print(f"Общее кол-во отказов: {sys_stats.get('total_rejected', 0)}")
            print(f"Общая вероятность отказа: {sys_stats.get('total_reject_prob', 0):.4f}")

    def plot_comprehensive_analysis(self, results_by_tau: List[Dict], events_data: List[Dict] = None):
        """
        Комплексный анализ результатов моделирования
        Адаптировано для переменного количества источников
        """
        if not results_by_tau:
            print("Нет данных для анализа")
            return
        
        # Определяем количество источников из первого результата
        first_result = results_by_tau[0]
        num_sources = len(first_result['sources_stats']) if 'sources_stats' in first_result else 0
        num_devices = len(first_result['devices_stats']) if 'devices_stats' in first_result else 0
        
        print(f"Анализ данных: {len(results_by_tau)} реализаций, {num_sources} источников, {num_devices} приборов")
        
        # Создаем комплексную панель графиков
        fig = plt.figure(figsize=(18, 14))
        
        # Динамическое создание grid в зависимости от количества данных
        if num_sources <= 2:
            gs = gridspec.GridSpec(3, 2, figure=fig)
        else:
            gs = gridspec.GridSpec(3, 3, figure=fig)
        
        # 1. Основные зависимости от TAU
        self._plot_main_dependencies(fig, gs[0, 0], results_by_tau, num_sources)
        
        # 2. Распределение времени ожидания
        self._plot_wait_time_analysis(fig, gs[0, 1], results_by_tau, num_sources)
        
        # 3. Вероятности отказа по источникам
        if num_sources > 0:
            if num_sources <= 2:
                self._plot_reject_probability(fig, gs[1, 0], results_by_tau, num_sources)
                # 4. Сравнение производительности приборов
                self._plot_devices_performance(fig, gs[1, 1], results_by_tau, num_devices)
                # 5. Временные диаграммы или анализ буфера
                if events_data:
                    self._plot_enhanced_timeline(fig, gs[2, :], events_data, num_sources)
                else:
                    self._plot_buffer_analysis(fig, gs[2, :], results_by_tau)
            else:
                self._plot_reject_probability(fig, gs[1, 0], results_by_tau, num_sources)
                self._plot_devices_performance(fig, gs[1, 1], results_by_tau, num_devices)
                if events_data:
                    self._plot_enhanced_timeline(fig, gs[2, 0], events_data, num_sources)
                self._plot_buffer_analysis(fig, gs[2, 1], results_by_tau)
        
        plt.tight_layout()
        plt.show()

    def _plot_main_dependencies(self, fig, pos, results_by_tau: List[Dict], num_sources: int):
        """Основные зависимости характеристик от времени обслуживания"""
        ax = fig.add_subplot(pos)
        
        tau_values = [r['tau'] for r in results_by_tau]
        
        # Общая вероятность отказа системы
        total_reject_prob = [r['system_stats']['total_reject_prob'] for r in results_by_tau]
        ax.plot(tau_values, total_reject_prob, 'o-', linewidth=2.5, 
                label='Общая P_отк', color=self.colors[0], markersize=6)
        
        # Среднее время ожидания для первых нескольких источников (чтобы не перегружать график)
        max_sources_to_plot = min(4, num_sources)
        for i in range(max_sources_to_plot):
            wait_times = [r['sources_stats'][i].get('avg_wait_time', 0) for r in results_by_tau]
            ax.plot(tau_values, wait_times, 's-', linewidth=2,
                   label=f'M[T_ож] И{i+1}', color=self.colors[i+1], markersize=5, alpha=0.8)
        
        ax.set_xlabel('Время обслуживания (TAU)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Вероятность отказа / Время ожидания', fontsize=11, fontweight='bold')
        ax.set_title('Основные зависимости от времени обслуживания', 
                    fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=0)

    def _plot_wait_time_analysis(self, fig, pos, results_by_tau: List[Dict], num_sources: int):
        """Анализ времени ожидания для всех источников"""
        ax = fig.add_subplot(pos)
        
        tau_values = [r['tau'] for r in results_by_tau]
        
        # M[T_ож] для всех источников
        for i in range(num_sources):
            wait_times = [r['sources_stats'][i].get('avg_wait_time', 0) for r in results_by_tau]
            ax.plot(tau_values, wait_times, 's-', linewidth=2.5,
                   label=f'M[T_ож] И{i+1}', color=self.colors[i % len(self.colors)], markersize=6)
        
        ax.set_xlabel('Время обслуживания (TAU)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Среднее время ожидания', fontsize=11, fontweight='bold')
        ax.set_title('Время ожидания по источникам', 
                    fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=0)

    def _plot_reject_probability(self, fig, pos, results_by_tau: List[Dict], num_sources: int):
        """Анализ вероятностей отказа по источникам"""
        ax = fig.add_subplot(pos)
        
        tau_values = [r['tau'] for r in results_by_tau]
        
        # Вероятность отказа для всех источников
        for i in range(num_sources):
            reject_probs = []
            for r in results_by_tau:
                stats = r['sources_stats'][i]
                reject_prob = stats['rejected'] / stats['total'] if stats['total'] > 0 else 0
                reject_probs.append(reject_prob)
            
            ax.plot(tau_values, reject_probs, '^-', linewidth=2,
                   label=f'P_отк И{i+1}', color=self.colors[i % len(self.colors)], markersize=6, alpha=0.8)
        
        # Общая вероятность отказа
        total_reject_prob = [r['system_stats']['total_reject_prob'] for r in results_by_tau]
        ax.plot(tau_values, total_reject_prob, 'o-', linewidth=2.5,
               label='Общая P_отк', color='red', markersize=8)
        
        ax.set_xlabel('Время обслуживания (TAU)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Вероятность отказа', fontsize=11, fontweight='bold')
        ax.set_title('Вероятности отказа по источникам', 
                    fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 1)

    def _plot_devices_performance(self, fig, pos, results_by_tau: List[Dict], num_devices: int):
        """Анализ производительности приборов"""
        ax = fig.add_subplot(pos)
        
        tau_values = [r['tau'] for r in results_by_tau]
        
        # Количество обработанных заявок для каждого прибора
        for i in range(num_devices):
            processed_counts = [r['devices_stats'][i]['processed'] for r in results_by_tau]
            ax.plot(tau_values, processed_counts, 'o-', linewidth=2,
                   label=f'Обработано П{i+1}', color=self.colors[i % len(self.colors)], markersize=6)
        
        ax.set_xlabel('Время обслуживания (TAU)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Количество обработанных заявок', fontsize=11, fontweight='bold')
        ax.set_title('Производительность приборов', 
                    fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=0)

    def _plot_enhanced_timeline(self, fig, pos, events_data: List[Dict], num_sources: int):
        """Улучшенные временные диаграммы"""
        ax = fig.add_subplot(pos)
        
        if not events_data:
            ax.text(0.5, 0.5, 'Нет данных событий', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=14)
            return
        
        # Ограничиваем количество событий для читаемости
        max_events = min(200, len(events_data))
        display_data = events_data[:max_events]
        
        times = [e['time'] for e in display_data]
        
        # Разные типы событий разными маркерами
        event_types = {
            'arrival': ('Поступление', 'o'),
            'buffer_write': ('Запись в буфер', 's'),
            'buffer_reject': ('Отказ', 'x'),
            'device_start': ('Начало обсл.', '^'),
            'device_finish': ('Окончание обсл.', 'v'),
            'buffer_select': ('Выбор из буфера', 'D'),
            'packet_change': ('Смена пакета', '*')
        }
        
        for event_type, (label, marker) in event_types.items():
            event_times = [e['time'] for e in display_data if e.get('event_type') == event_type]
            if event_times:
                y_pos = list(event_types.keys()).index(event_type) + 1
                ax.scatter(event_times, [y_pos] * len(event_times), marker=marker, 
                          label=label, s=50, alpha=0.7)
        
        ax.set_xlabel('Время', fontsize=11, fontweight='bold')
        ax.set_ylabel('Тип события', fontsize=11, fontweight='bold')
        ax.set_title('Временная диаграмма работы системы', fontsize=12, fontweight='bold')
        ax.set_yticks(range(1, len(event_types) + 1))
        ax.set_yticklabels([event_types[et][0] for et in event_types.keys()])
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
        ax.grid(True, alpha=0.3)

    def _plot_buffer_analysis(self, fig, pos, results_by_tau: List[Dict]):
        """Анализ работы буфера"""
        ax = fig.add_subplot(pos)
        
        tau_values = [r['tau'] for r in results_by_tau]
        
        # Общая вероятность отказа
        total_reject_prob = [r['system_stats']['total_reject_prob'] for r in results_by_tau]
        
        ax.plot(tau_values, total_reject_prob, 's-', linewidth=2.5,
                label='Общая P_отк', color='#4ECDC4')
        
        # Среднее количество заявок в буфере (если есть данные)
        if 'realization_data' in results_by_tau[0]:
            avg_buffer_usage = [r['realization_data'].get('avg_buffer_usage', 0) for r in results_by_tau]
            ax_twin = ax.twinx()
            ax_twin.plot(tau_values, avg_buffer_usage, 'o-', linewidth=2.5,
                        label='Ср. заполнение буфера', color='#FF6B6B')
            ax_twin.set_ylabel('Среднее заполнение буфера', fontsize=11, fontweight='bold', color='#FF6B6B')
        
        ax.set_xlabel('Время обслуживания (TAU)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Вероятность отказа', fontsize=11, fontweight='bold')
        ax.set_title('Зависимость вероятности отказа\nот времени обслуживания', 
                    fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)

    def plot_real_time_statistics(self, real_time_data: List[Dict]):
        """
        График статистики в реальном времени (для пошагового режима)
        Адаптировано для переменного количества источников и приборов
        """
        if not real_time_data:
            print("Нет данных для построения графика в реальном времени")
            return
            
        # Определяем количество источников и приборов из первого элемента данных
        first_data = real_time_data[0]
        num_sources = len(first_data.get('sources_stats', [])) if isinstance(first_data.get('sources_stats'), list) else 0
        num_devices = len(first_data.get('devices_state', [])) if isinstance(first_data.get('devices_state'), list) else 0
        
        # Создаем grid в зависимости от количества данных
        if num_sources <= 2 and num_devices <= 2:
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        else:
            fig, axes = plt.subplots(2, 3, figsize=(18, 10))
        
        fig.suptitle('СТАТИСТИКА В РЕАЛЬНОМ ВРЕМЕНИ', fontsize=16, fontweight='bold')
        
        times = [d['time'] for d in real_time_data]
        
        # 1. Общее количество заявок от всех источников
        total_requests = []
        for d in real_time_data:
            if 'sources_stats' in d and isinstance(d['sources_stats'], list):
                # Парсим строки вида "И1[15]" для получения числа
                total = 0
                for stat in d['sources_stats']:
                    if '[' in stat and ']' in stat:
                        try:
                            count = int(stat.split('[')[1].split(']')[0])
                            total += count
                        except (ValueError, IndexError):
                            pass
                total_requests.append(total)
            else:
                total_requests.append(0)
        
        axes[0,0].plot(times, total_requests, linewidth=2, color=self.colors[0])
        axes[0,0].set_title('Общее количество заявок')
        axes[0,0].set_ylabel('Количество')
        axes[0,0].grid(True, alpha=0.3)
        
        # 2. Заполненность буфера
        buffer_sizes = [d.get('buffer_size', 0) for d in real_time_data]
        axes[0,1].step(times, buffer_sizes, where='post', linewidth=2, color=self.colors[1])
        axes[0,1].set_title('Заполненность буфера')
        axes[0,1].set_ylabel('Заявок в буфере')
        axes[0,1].set_ylim(0, max(buffer_sizes) + 1 if buffer_sizes else 5)
        axes[0,1].grid(True, alpha=0.3)
        
        # 3. Количество занятых приборов
        busy_devices = []
        for d in real_time_data:
            if 'devices_state' in d and isinstance(d['devices_state'], list):
                busy_count = sum(1 for state in d['devices_state'] if '[...]' not in state)
                busy_devices.append(busy_count)
            else:
                busy_devices.append(0)
        
        axes[1,0].step(times, busy_devices, where='post', linewidth=2, color=self.colors[2])
        axes[1,0].set_title('Количество занятых приборов')
        axes[1,0].set_ylabel('Занятые приборы')
        axes[1,0].set_ylim(0, num_devices if num_devices > 0 else 2)
        axes[1,0].grid(True, alpha=0.3)
        
        # 4. Накопленные отказы
        total_rejected = [d.get('total_rejected', 0) for d in real_time_data]
        axes[1,1].plot(times, total_rejected, label='Всего отказов', linewidth=2, color=self.colors[3])
        axes[1,1].set_title('Накопленные отказы')
        axes[1,1].set_ylabel('Количество отказов')
        axes[1,1].legend()
        axes[1,1].grid(True, alpha=0.3)
        
        # 5. Дополнительный график - текущий пакет (если есть данные)
        if len(axes.flat) > 4 and any('current_packet' in d for d in real_time_data):
            current_packets = [d.get('current_packet', -1) for d in real_time_data]
            axes_extra = axes.flat[4]
            axes_extra.step(times, current_packets, where='post', linewidth=2, color=self.colors[4])
            axes_extra.set_title('Текущий пакет обслуживания')
            axes_extra.set_ylabel('Номер пакета')
            axes_extra.grid(True, alpha=0.3)
        
        for ax in axes.flat:
            if ax.has_data():
                ax.set_xlabel('Время')
        
        plt.tight_layout()
        plt.show()

    def plot_comparative_analysis(self, configs_comparison: List[Dict[str, Any]]):
        """
        Сравнительный анализ разных конфигураций системы
        """
        if not configs_comparison:
            print("Нет данных для сравнительного анализа")
            return
            
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('СРАВНИТЕЛЬНЫЙ АНАЛИЗ КОНФИГУРАЦИЙ', fontsize=16, fontweight='bold')
        
        config_names = [config['name'] for config in configs_comparison]
        
        # 1. Общая вероятность отказа
        total_reject_probs = [config['results']['system_stats']['total_reject_prob'] 
                             for config in configs_comparison]
        
        bars1 = axes[0,0].bar(config_names, total_reject_probs, color=self.colors[:len(config_names)])
        axes[0,0].set_title('Общая вероятность отказа')
        axes[0,0].set_ylabel('Вероятность отказа')
        axes[0,0].tick_params(axis='x', rotation=45)
        
        # Добавляем значения на столбцы
        for bar, value in zip(bars1, total_reject_probs):
            axes[0,0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                          f'{value:.4f}', ha='center', va='bottom')
        
        # 2. Среднее время ожидания
        avg_wait_times = []
        for config in configs_comparison:
            sources_wait_times = [source['avg_wait_time'] for source in config['results']['sources_stats']]
            avg_wait_times.append(np.mean(sources_wait_times))
        
        bars2 = axes[0,1].bar(config_names, avg_wait_times, color=self.colors[len(config_names):len(config_names)*2])
        axes[0,1].set_title('Среднее время ожидания')
        axes[0,1].set_ylabel('Время ожидания')
        axes[0,1].tick_params(axis='x', rotation=45)
        
        for bar, value in zip(bars2, avg_wait_times):
            axes[0,1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                          f'{value:.2f}', ha='center', va='bottom')
        
        # 3. Общая производительность системы
        total_processed = [config['results']['system_stats']['total_processed'] 
                          for config in configs_comparison]
        
        bars3 = axes[1,0].bar(config_names, total_processed, color=self.colors[len(config_names)*2:len(config_names)*3])
        axes[1,0].set_title('Общее количество обработанных заявок')
        axes[1,0].set_ylabel('Количество заявок')
        axes[1,0].tick_params(axis='x', rotation=45)
        
        for bar, value in zip(bars3, total_processed):
            axes[1,0].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                          f'{value}', ha='center', va='bottom')
        
        # 4. Эффективность использования приборов
        devices_efficiency = []
        for config in configs_comparison:
            devices_processed = [device['processed'] for device in config['results']['devices_stats']]
            efficiency = np.mean(devices_processed) / max(devices_processed) if max(devices_processed) > 0 else 0
            devices_efficiency.append(efficiency)
        
        bars4 = axes[1,1].bar(config_names, devices_efficiency, color=self.colors[len(config_names)*3:])
        axes[1,1].set_title('Эффективность использования приборов')
        axes[1,1].set_ylabel('Коэффициент эффективности')
        axes[1,1].tick_params(axis='x', rotation=45)
        axes[1,1].set_ylim(0, 1)
        
        for bar, value in zip(bars4, devices_efficiency):
            axes[1,1].text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.01, 
                          f'{value:.2f}', ha='center', va='bottom')
        
        plt.tight_layout()
        plt.show()