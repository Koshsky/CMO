"""
Улучшенный модуль для визуализации результатов моделирования
"""

import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Any
import matplotlib.gridspec as gridspec

class ResultsVisualizer:
    """Улучшенный класс для визуализации результатов СМО"""
    
    def __init__(self):
        plt.style.use('seaborn-v0_8')
        self.figsize = (16, 10)
        self.colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']
    
    def print_results_table(self, results: Dict[str, Any]):
        """
        Вывод улучшенной сводной таблицы результатов
        """
        print("\n" + "="*90)
        print("СВОДНАЯ ТАБЛИЦА РЕЗУЛЬТАТОВ МОДЕЛИРОВАНИЯ")
        print("="*90)
        
        if 'sources_stats' in results:
            print("\nХАРАКТЕРИСТИКИ ИСТОЧНИКОВ:")
            print("-" * 80)
            print(f"{'Источник':<10} {'Всего':<8} {'Обработано':<10} {'Отказов':<8} {'P_отк':<10} {'M[T_ож]':<12} {'M[T_пр]':<12} {'Загрузка':<10}")
            print("-" * 80)
            
            for i, stats in enumerate(results['sources_stats']):
                utilization = stats.get('utilization', 0)
                print(f"{f'И{i+1}':<10} {stats['total']:<8} {stats.get('processed', 0):<10} "
                      f"{stats['rejected']:<8} {stats['reject_prob']:<10.4f} "
                      f"{stats['avg_wait_time']:<12.4f} {stats['avg_system_time']:<12.4f} "
                      f"{utilization:<10.3f}")
        
        if 'system_stats' in results:
            print(f"\nОБЩАЯ СТАТИСТИКА СИСТЕМЫ:")
            print("-" * 50)
            sys_stats = results['system_stats']
            print(f"Общее время моделирования: {sys_stats.get('total_time', 0):.2f}")
            print(f"Общее кол-во заявок: {sys_stats.get('total_requests', 0)}")
            print(f"Коэффициент использования системы: {sys_stats.get('system_utilization', 0):.3f}")
            print(f"Средняя длина очереди: {sys_stats.get('avg_queue_length', 0):.3f}")

    def plot_comprehensive_analysis(self, results_by_tau: List[Dict], events_data: List[Dict] = None):
        """
        Комплексный анализ результатов моделирования
        """
        if not results_by_tau:
            print("Нет данных для анализа")
            return
        
        # Создаем комплексную панель графиков
        fig = plt.figure(figsize=(18, 12))
        gs = gridspec.GridSpec(3, 3, figure=fig)
        
        # 1. Основные зависимости от TAU
        self._plot_main_dependencies(fig, gs[0, 0], results_by_tau)
        
        # 2. Распределение времени ожидания
        self._plot_wait_time_analysis(fig, gs[0, 1], results_by_tau)
        
        # 3. Эффективность системы
        self._plot_system_efficiency(fig, gs[0, 2], results_by_tau)
        
        # 4. Сравнение источников
        self._plot_sources_comparison(fig, gs[1, :], results_by_tau)
        
        # 5. Временные диаграммы (если есть данные событий)
        if events_data:
            self._plot_enhanced_timeline(fig, gs[2, :], events_data)
        else:
            # Или анализ загрузки буфера
            self._plot_buffer_analysis(fig, gs[2, :], results_by_tau)
        
        plt.tight_layout()
        plt.show()

    def _plot_main_dependencies(self, fig, pos, results_by_tau):
        """Основные зависимости характеристик от времени обслуживания"""
        ax = fig.add_subplot(pos)
        
        tau_values = [r['tau'] for r in results_by_tau]
        
        # P_отк для обоих источников
        for i in range(2):
            p_reject = [r['sources_stats'][i]['reject_prob'] for r in results_by_tau]
            ax.plot(tau_values, p_reject, 'o-', linewidth=2.5, 
                   label=f'P_отк И{i+1}', color=self.colors[i], markersize=6)
        
        ax.set_xlabel('Время обслуживания (TAU)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Вероятность отказа', fontsize=11, fontweight='bold')
        ax.set_title('Зависимость вероятности отказа\nот времени обслуживания', 
                    fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=0)

    def _plot_wait_time_analysis(self, fig, pos, results_by_tau):
        """Анализ времени ожидания"""
        ax = fig.add_subplot(pos)
        
        tau_values = [r['tau'] for r in results_by_tau]
        
        # M[T_ож] для обоих источников
        for i in range(2):
            wait_times = [r['sources_stats'][i]['avg_wait_time'] for r in results_by_tau]
            ax.plot(tau_values, wait_times, 's-', linewidth=2.5,
                   label=f'M[T_ож] И{i+1}', color=self.colors[i+2], markersize=6)
        
        ax.set_xlabel('Время обслуживания (TAU)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Среднее время ожидания', fontsize=11, fontweight='bold')
        ax.set_title('Зависимость времени ожидания\nот времени обслуживания', 
                    fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(bottom=0)

    def _plot_system_efficiency(self, fig, pos, results_by_tau):
        """Анализ эффективности системы"""
        ax = fig.add_subplot(pos)
        
        tau_values = [r['tau'] for r in results_by_tau]
        
        # Коэффициент использования системы
        utilizations = [r.get('system_stats', {}).get('system_utilization', 0.5) for r in results_by_tau]
        
        ax.plot(tau_values, utilizations, '^-', linewidth=2.5, color='#2E8B57',
               label='Коэф. использования', markersize=8)
        
        # Оптимальная зона (80-90% использования)
        ax.axhspan(0.7, 0.9, alpha=0.2, color='green', label='Оптимальная зона')
        
        ax.set_xlabel('Время обслуживания (TAU)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Коэффициент использования', fontsize=11, fontweight='bold')
        ax.set_title('Эффективность использования\nсистемы', fontsize=12, fontweight='bold')
        ax.legend()
        ax.grid(True, alpha=0.3)
        ax.set_ylim(0, 1)

    def _plot_sources_comparison(self, fig, pos, results_by_tau):
        """Сравнительный анализ источников"""
        ax = fig.add_subplot(pos)
        
        tau_values = [r['tau'] for r in results_by_tau]
        
        metrics = ['reject_prob', 'avg_wait_time', 'avg_system_time']
        metric_names = ['Вероятность отказа', 'Время ожидания', 'Время в системе']
        bar_width = 0.25
        
        for metric_idx, (metric, name) in enumerate(zip(metrics, metric_names)):
            # Значения для обоих источников
            values_source1 = [r['sources_stats'][0][metric] for r in results_by_tau]
            values_source2 = [r['sources_stats'][1][metric] for r in results_by_tau]
            
            x_pos = np.arange(len(tau_values)) + metric_idx * bar_width
            
            ax.bar(x_pos - bar_width/2, values_source1, bar_width, 
                   label=f'И1 {name}' if metric_idx == 0 else "", 
                   color=self.colors[0], alpha=0.7)
            ax.bar(x_pos + bar_width/2, values_source2, bar_width,
                   label=f'И2 {name}' if metric_idx == 0 else "",
                   color=self.colors[1], alpha=0.7)
        
        ax.set_xlabel('Индекс реализации (по TAU)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Значения характеристик', fontsize=11, fontweight='bold')
        ax.set_title('Сравнительный анализ характеристик источников', 
                    fontsize=12, fontweight='bold')
        ax.set_xticks(np.arange(len(tau_values)) + bar_width)
        ax.set_xticklabels([f'TAU={t:.1f}' for t in tau_values], rotation=45)
        ax.legend()
        ax.grid(True, alpha=0.3)

    def _plot_enhanced_timeline(self, fig, pos, events_data: List[Dict]):
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
            'device_finish': ('Окончание обсл.', 'v')
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

    def _plot_buffer_analysis(self, fig, pos, results_by_tau):
        """Анализ работы буфера"""
        ax = fig.add_subplot(pos)
        
        tau_values = [r['tau'] for r in results_by_tau]
        
        # Средняя длина очереди и вероятность отказа
        avg_queue = [r.get('system_stats', {}).get('avg_queue_length', 0) for r in results_by_tau]
        total_reject_prob = [
            (r['sources_stats'][0]['reject_prob'] * r['sources_stats'][0]['total'] +
             r['sources_stats'][1]['reject_prob'] * r['sources_stats'][1]['total']) /
            (r['sources_stats'][0]['total'] + r['sources_stats'][1]['total'])
            for r in results_by_tau
        ]
        
        ax.plot(tau_values, avg_queue, 'o-', linewidth=2.5, 
               label='Средняя длина очереди', color='#FF6B6B')
        ax_twin = ax.twinx()
        ax_twin.plot(tau_values, total_reject_prob, 's-', linewidth=2.5,
                    label='Общая P_отк', color='#4ECDC4')
        
        ax.set_xlabel('Время обслуживания (TAU)', fontsize=11, fontweight='bold')
        ax.set_ylabel('Средняя длина очереди', fontsize=11, fontweight='bold', color='#FF6B6B')
        ax_twin.set_ylabel('Общая вероятность отказа', fontsize=11, fontweight='bold', color='#4ECDC4')
        ax.set_title('Анализ работы буферной памяти', fontsize=12, fontweight='bold')
        
        # Объединяем легенды
        lines1, labels1 = ax.get_legend_handles_labels()
        lines2, labels2 = ax_twin.get_legend_handles_labels()
        ax.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        ax.grid(True, alpha=0.3)

    def plot_real_time_statistics(self, real_time_data: List[Dict]):
        """
        График статистики в реальном времени (для пошагового режима)
        """
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('СТАТИСТИКА В РЕАЛЬНОМ ВРЕМЕНИ', fontsize=16, fontweight='bold')
        
        times = [d['time'] for d in real_time_data]
        
        # 1. Количество заявок в системе
        total_requests = [d.get('statistics', {}).get('total_1', 0) + 
                         d.get('statistics', {}).get('total_2', 0) for d in real_time_data]
        axes[0,0].plot(times, total_requests, linewidth=2, color=self.colors[0])
        axes[0,0].set_title('Общее количество заявок')
        axes[0,0].set_ylabel('Количество')
        axes[0,0].grid(True, alpha=0.3)
        
        # 2. Заполненность буфера
        buffer_sizes = [d.get('buffer_size', 0) for d in real_time_data]
        axes[0,1].step(times, buffer_sizes, where='post', linewidth=2, color=self.colors[1])
        axes[0,1].set_title('Заполненность буфера')
        axes[0,1].set_ylabel('Заявок в буфере')
        axes[0,1].grid(True, alpha=0.3)
        
        # 3. Состояние прибора
        device_states = [1 if d.get('device_busy', False) else 0 for d in real_time_data]
        axes[1,0].step(times, device_states, where='post', linewidth=2, color=self.colors[2])
        axes[1,0].set_title('Состояние прибора')
        axes[1,0].set_ylabel('1 - занят, 0 - свободен')
        axes[1,0].set_yticks([0, 1])
        axes[1,0].grid(True, alpha=0.3)
        
        # 4. Накопленные отказы
        rejected_1 = [d.get('statistics', {}).get('rejected_1', 0) for d in real_time_data]
        rejected_2 = [d.get('statistics', {}).get('rejected_2', 0) for d in real_time_data]
        axes[1,1].plot(times, rejected_1, label='Отказы И1', linewidth=2)
        axes[1,1].plot(times, rejected_2, label='Отказы И2', linewidth=2)
        axes[1,1].set_title('Накопленные отказы')
        axes[1,1].set_ylabel('Количество отказов')
        axes[1,1].legend()
        axes[1,1].grid(True, alpha=0.3)
        
        for ax in axes.flat:
            ax.set_xlabel('Время')
        
        plt.tight_layout()
        plt.show()