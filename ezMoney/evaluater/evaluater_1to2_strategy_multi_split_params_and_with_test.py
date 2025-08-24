import sys
sys.path.append(r"D:\workspace\TradeX\ezMoney")

import numpy as np
import random
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from deap import base, creator, tools, algorithms
from monitor.monitor_for_backtest import StockMonitor
from tqdm import tqdm
import pickle
import os
import multiprocessing
from functools import partial
import datetime
import logging
import json
import time
import traceback
# from evaluater.evaluater_generate_datas import build_evaluater_1to2_data_list_from_file

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定义参数范围和类型
PARAM_RANGES = {
    'per_step_tick_gap': (1, 25, int),
    'cold_start_steps': (0, 30, int),
    'max_abserve_tick_steps': (5, 500, int),
    'max_abserce_avg_price_down_steps': (1, 15, int),
    'stop_profit_open_hc_pct': (-0.15, 0.0, float),
    'dynamic_hc_stop_profit_thres': (0.01, 8, float),
    'last_close_price_hc_pct': (-0.04, 0.01, float),
    'last_day_sell_thres': (0.001, 1.0, float),
    'last_day_sell_huiche': (0.001, 0.02, float),
    'fd_mount': (10000000, 150000000, int),
    'fd_vol_pct': (0, 0.75, float),
    'fd_ju_ticks': (1, 50, int),
    'max_zb_times': (1, 30, int),
    'stagnation_kline_ticks': (3, 50, int),
    'decline_kline_ticks': (3, 50, int),
    'yang_yin_threshold': (0.002, 0.03, float),
    'stagnation_n': (1, 30, int),
    'stagnation_volume_ratio_threshold': (1.1, 100, float),
    'stagnation_ratio_threshold': (15, 1500, int),
    'decline_volume_ratio_threshold': (1.1, 100, float),
    'max_rebounds': (1, 15, int),
    'decline_ratio_threshold': (15, 1500, int),
    'flxd_ticks': (0, 500, int),
    'flzz_ticks': (100, 2000, int),
    'kline_sell_only_zy': (0, 1, bool),
    'window_size': (3, 15, int),
    'use_simiple_kline_strategy_flxd': (0, 1, bool),
    'use_simiple_kline_strategy_flzz': (0, 1, bool),
    'flzz_use_smooth_price': (0, 1, bool),
    'flzz_zf_thresh': (-0.07, 0.1, float),
}

# 参数分组 - 核心参数优先优化
PARAM_GROUPS = {
    'phase1_tick_monitoring': [
        'per_step_tick_gap',
        'cold_start_steps',
        'max_abserve_tick_steps',
        'max_abserce_avg_price_down_steps',
        'stop_profit_open_hc_pct',
        'dynamic_hc_stop_profit_thres',
        'last_close_price_hc_pct',
        'last_day_sell_thres',
        'last_day_sell_huiche',
        'window_size',
    ],
    'phase2_stop_loss_profit': [
        'stagnation_kline_ticks',
        'decline_kline_ticks',
        'stagnation_ratio_threshold',
        'decline_ratio_threshold',
        'stagnation_volume_ratio_threshold',
        'decline_volume_ratio_threshold',
        'stagnation_n',
        'max_rebounds',
        'flxd_ticks',
        'flzz_ticks',
        'flzz_zf_thresh',
        'yang_yin_threshold',
        'kline_sell_only_zy',
        'use_simiple_kline_strategy_flxd',
        'use_simiple_kline_strategy_flzz',
        'flzz_use_smooth_price',
    ],
    'phase3_volume_analysis': [
        'fd_mount',
        'fd_vol_pct',
        'fd_ju_ticks',
        'max_zb_times',
    ],
    # 'phase4_trend_following': [
        
        
    # ],
    # 'phase5_miscellaneous': [
        
    # ]
}

# 默认参数值（用于未优化的参数）
DEFAULT_PARAMS = {
    "per_step_tick_gap": 13,
    "cold_start_steps": 3,
    "max_abserve_tick_steps": 194,
    "max_abserce_avg_price_down_steps": 6,
    "stop_profit_open_hc_pct": -0.051398809835553116,
    "dynamic_hc_stop_profit_thres": 0.10003196463273602,
    "last_close_price_hc_pct": -0.02296567115927568,
    "last_day_sell_thres": 0.011504005089447681,
    "last_day_sell_huiche": 0.001,
    "fd_mount": 90481903,
    "fd_vol_pct": 0.5014903668296646,
    "fd_ju_ticks": 3,
    "max_zb_times": 14,
    "stagnation_kline_ticks": 33,
    "decline_kline_ticks": 11,
    "yang_yin_threshold": 0.009002281217788533,
    "stagnation_n": 7,
    "stagnation_volume_ratio_threshold": 47,
    "stagnation_ratio_threshold": 398,
    "decline_volume_ratio_threshold": 13,
    "max_rebounds": 1,
    "decline_ratio_threshold": 33,
    "flxd_ticks": 265,
    "kline_sell_only_zy": False,
    "window_size": 5,
    "use_simiple_kline_strategy_flxd": True,
    "use_simiple_kline_strategy_flzz": False,
    "stop_profit_pct": 0.0,
    "static_hc_stop_profit_pct": 1.0,
    'flzz_use_smooth_price': False,
    'flzz_zf_thresh': -0.05,
    'flzz_ticks': 2000,
}

# 无风险年化收益率 (0%)
RISK_FREE_RATE = 0
DAILY_RISK_FREE_RATE = RISK_FREE_RATE / 252

# 创建输出目录
os.makedirs("optimization_results", exist_ok=True)
os.makedirs("capital_curves", exist_ok=True)

class SharedData:
    def __init__(self, stock_lists):
        self.stock_lists = stock_lists
    
    def __getstate__(self):
        return self.__dict__
    
    def __setstate__(self, state):
        self.__dict__.update(state)

def init_worker(shared_data):
    global global_shared_data
    global_shared_data = shared_data

def create_individual(optimizable_params):
    """创建个体（一组参数）"""
    individual = []
    for param in optimizable_params:
        min_val, max_val, param_type = PARAM_RANGES[param]
        
        if param_type == int:
            individual.append(random.randint(min_val, max_val))
        elif param_type == bool:
            individual.append(random.randint(0, 1))
        else:
            individual.append(random.uniform(min_val, max_val))
    
    return individual

def create_diverse_individual(optimizable_params):
    individual = []
    for param in optimizable_params:
        min_val, max_val, param_type = PARAM_RANGES[param]
        if param_type == int:
            individual.append(random.randint(min_val, max_val))
        elif param_type == bool:
            individual.append(random.randint(0, 1))
        else:
            if random.random() < 0.5:
                value = random.uniform(min_val, max_val)
            else:
                mean = (min_val + max_val) / 2
                std = (max_val - min_val) / 6
                value = random.gauss(mean, std)
                value = max(min_val, min(max_val, value))
            individual.append(value)
    return individual

def decode_individual(individual, optimizable_params, base_params=None):
    """将遗传算法中的个体解码为参数字典"""
    if base_params is None:
        params = DEFAULT_PARAMS.copy()
    else:
        params = base_params.copy()
    
    for i, param in enumerate(optimizable_params):
        min_val, max_val, param_type = PARAM_RANGES[param]
        value = individual[i]
        
        if value < min_val or value > max_val:
            value = np.clip(value, min_val, max_val)
        
        if param_type == int:
            value = int(round(value))
        elif param_type == bool:
            value = value > 0.5
        else:
            value = float(value)
        
        params[param] = value
    
    return params

def evaluate_strategy_on_single_list(individual, stock_sublist, initial_capital=200000, 
                                    fitness_weights=(0.2, 0.5, 0.3), optimizable_params=None, base_params=None):
    """评估策略在单个股票子列表上的表现"""
    try:
        if optimizable_params is None:
            optimizable_params = list(PARAM_RANGES.keys())
            
        params = decode_individual(individual, optimizable_params, base_params)
        capital = initial_capital
        capital_curve = [capital]
        daily_returns = []
        
        stock_count = 0
        profitable_trades = 0
        total_profit = 0
        
        for stock_data in stock_sublist:
            stock_count += 1
            stock_code = stock_data['stock_code']
            stock_name = stock_data['stock_name']
            stock_infos = stock_data['stock_infos']
            mkt_datas = stock_data['mkt_datas']
            
            if 'params' in stock_infos:
                stock_infos['params'].update(params)
            else:
                stock_infos['params'] = params

            monitor = StockMonitor(
                stock_code=stock_code,
                stock_name=stock_name,
                stock_infos=stock_infos,
                mkt_datas=mkt_datas,
                params=stock_infos['params']
            )
            
            sold, sell_price = monitor.get_result()
            
            trade_price = stock_infos['trade_price']
            close_price = stock_infos['close_price']
            limit_up = stock_infos['limit_up']
            limit_down = stock_infos['limit_down']
            n_next_open = stock_infos['n_next_open']
            n_next_close = stock_infos['n_next_close']

            if sold:
                actual_sell_price = sell_price
            else:
                actual_sell_price = close_price
                if limit_up == 1 or limit_down == 1:
                    actual_sell_price = n_next_open
            
            if actual_sell_price <= 0:
                actual_sell_price = close_price
            
            if trade_price > 0:
                shares = (capital / trade_price // 100) * 100
                cost = shares * trade_price
                revenue = shares * actual_sell_price
                profit = revenue - cost
                profit_pct = (actual_sell_price - trade_price) / trade_price
                
                if profit > 0:
                    profitable_trades += 1
                total_profit += profit
                
                capital += profit
            
            capital_curve.append(capital)
            
            if len(capital_curve) >= 2 and capital_curve[-2] > 0:
                daily_return = (capital_curve[-1] - capital_curve[-2]) / capital_curve[-2]
                daily_returns.append(daily_return)
        
        # 计算总体表现指标
        if initial_capital > 0:
            total_return = (capital - initial_capital) / initial_capital
        else:
            total_return = 0
        
        if len(capital_curve) > 1:
            capital_array = np.array(capital_curve)
            peak = np.maximum.accumulate(capital_array)
            drawdowns = (peak - capital_array) / peak
            max_drawdown = np.max(drawdowns)
        else:
            max_drawdown = 0
        
        returns_array = np.array(daily_returns)
        if len(returns_array) > 1:
            excess_returns = returns_array - DAILY_RISK_FREE_RATE
            sharpe_ratio = np.mean(excess_returns) / (np.std(excess_returns) + 1e-8) * np.sqrt(252)
        else:
            sharpe_ratio = 0

        w_return, w_drawdown, w_sharpe = fitness_weights
        
        # 增加对回撤的惩罚
        drawdown_penalty = 1.0
        if max_drawdown > 0.3:
            drawdown_penalty = np.exp(-10 * (max_drawdown - 0.3))
        
        return_component = max(1e-8, total_return)
        drawdown_component = max(1e-8, 1 - max_drawdown)
        sharpe_component = max(1e-8, sharpe_ratio)
        
        fitness = ((return_component) ** w_return) * (drawdown_component ** w_drawdown) * (sharpe_component ** w_sharpe)
        
        # 应用回撤惩罚
        fitness *= drawdown_penalty
        
        return fitness, total_return, max_drawdown, sharpe_ratio, capital_curve
        
    except Exception as e:
        stock_code = stock_data['stock_code'] if 'stock_code' in stock_data else 'Unknown'
        logger.error(f"Error evaluating strategy for stock {stock_code}: {str(e)}")
        logger.error(traceback.format_exc())
        return 1e-8, -0.9, 0.9, 0, [initial_capital]

def evaluate_strategy_global_phase(individual, initial_capital=200000, fitness_weights=(0.4, 0.3, 0.3), 
                                  optimizable_params=None, base_params=None):
    """使用共享数据评估策略（分阶段版本）"""
    try:
        global global_shared_data
        stock_lists = global_shared_data.stock_lists
        
        all_fitnesses = []
        all_returns = []
        all_drawdowns = []
        all_sharpes = []
        
        for i, stock_sublist in enumerate(stock_lists):
            fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
                individual, stock_sublist, initial_capital, fitness_weights, optimizable_params, base_params
            )
            all_fitnesses.append(fitness)
            all_returns.append(total_return)
            all_drawdowns.append(max_drawdown)
            all_sharpes.append(sharpe_ratio)
        
        avg_fitness = np.mean(all_fitnesses)
        return (avg_fitness,)
        
    except Exception as e:
        logger.error(f"Error in evaluate_strategy_global: {str(e)}")
        logger.error(traceback.format_exc())
        return (0.0,)

def mutGaussianAdaptive(individual, mu, sigma, indpb, optimizable_params):
    """自适应高斯变异"""
    size = len(individual)
    for i in range(size):
        if random.random() < indpb:
            param_name = optimizable_params[i]
            min_val, max_val, param_type = PARAM_RANGES[param_name]
            range_size = max_val - min_val
            
            if param_type == int:
                adjusted_sigma = max(1, sigma * range_size / 5)
                individual[i] += int(round(random.gauss(mu, adjusted_sigma)))
            elif param_type == bool:
                individual[i] = 1 - individual[i]
            else:
                adjusted_sigma = sigma * range_size
                individual[i] += random.gauss(mu, adjusted_sigma)
            
            individual[i] = max(min_val, min(individual[i], max_val))
    return (individual,)

def mutUniformInt(individual, indpb, optimizable_params):
    """均匀整数变异"""
    size = len(individual)
    for i in range(size):
        if random.random() < indpb:
            param_name = optimizable_params[i]
            min_val, max_val, param_type = PARAM_RANGES[param_name]
            
            if param_type == int:
                individual[i] = random.randint(min_val, max_val)
            elif param_type == bool:
                individual[i] = 1 - individual[i]
            else:
                individual[i] = random.uniform(min_val, max_val)
    
    return (individual,)

def cxBlendAdaptive(ind1, ind2, alpha, optimizable_params):
    """自适应混合交叉"""
    size = min(len(ind1), len(ind2))
    for i in range(size):
        param_name = optimizable_params[i]
        _, _, param_type = PARAM_RANGES[param_name]
        
        if param_type == bool:
            if random.random() < 0.5:
                ind1[i], ind2[i] = ind2[i], ind1[i]
        else:
            gamma = (1. + 2. * alpha) * random.random() - alpha
            ind1[i] = (1. - gamma) * ind1[i] + gamma * ind2[i]
            ind2[i] = gamma * ind1[i] + (1. - gamma) * ind2[i]
    
    return ind1, ind2

def diversity(population, optimizable_params):
    """计算种群多样性"""
    if len(population) <= 1:
        return 0
    
    valid_individuals = [ind for ind in population if isinstance(ind, list)]
    
    if len(valid_individuals) <= 1:
        return 0
    
    normalized_pop = []
    for ind in valid_individuals:
        normalized_ind = []
        for i, param in enumerate(optimizable_params):
            min_val, max_val, _ = PARAM_RANGES[param]
            value = ind[i]
            if value < min_val or value > max_val:
                value = np.clip(value, min_val, max_val)
            normalized_val = (value - min_val) / (max_val - min_val)
            normalized_ind.append(normalized_val)
        normalized_pop.append(normalized_ind)
    
    total_distance = 0
    count = 0
    for i in range(len(normalized_pop)):
        for j in range(i+1, len(normalized_pop)):
            dist = np.linalg.norm(np.array(normalized_pop[i]) - np.array(normalized_pop[j]))
            total_distance += dist
            count += 1
    
    return total_distance / count if count > 0 else 0

def create_adaptive_mutate(diversity_threshold=0.1, optimizable_params=None):
    """创建自适应变异函数"""
    def adaptive_mutate(individual):
        if random.random() < 0.5:
            return mutGaussianAdaptive(individual, mu=0, sigma=0.05, indpb=0.3, optimizable_params=optimizable_params)
        else:
            return mutUniformInt(individual, indpb=0.3, optimizable_params=optimizable_params)
    return adaptive_mutate

def check_bounds_decorator(func, optimizable_params):
    """装饰器函数，确保遗传操作后的个体参数在合理范围内"""
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        if isinstance(result, tuple):
            for ind in result:
                for i, param in enumerate(optimizable_params):
                    min_val, max_val, _ = PARAM_RANGES[param]
                    if ind[i] < min_val or ind[i] > max_val:
                        ind[i] = np.clip(ind[i], min_val, max_val)
            return result
        else:
            for i, param in enumerate(optimizable_params):
                min_val, max_val, _ = PARAM_RANGES[param]
                if result[i] < min_val or result[i] > max_val:
                    result[i] = np.clip(result[i], min_val, max_val)
            return result
    
    return wrapper

def adaptive_cx_mutate(population, toolbox, cxpb, mutpb, diversity_score, optimizable_params):
    """根据种群多样性自适应调整交叉和变异概率"""
    if diversity_score < 0.1:
        mutpb = min(0.8, mutpb * 1.5)
        cxpb = max(0.2, cxpb * 0.8)
    elif diversity_score > 0.5:
        cxpb = min(0.9, cxpb * 1.2)
        mutpb = max(0.1, mutpb * 0.8)
    
    offspring = []
    for i in range(0, len(population), 2):
        if i+1 < len(population):
            child1, child2 = toolbox.clone(population[i]), toolbox.clone(population[i+1])
            if random.random() < cxpb:
                toolbox.mate(child1, child2)
                del child1.fitness.values
                del child2.fitness.values
            offspring.append(child1)
            offspring.append(child2)
    
    for mutant in offspring:
        if random.random() < mutpb:
            toolbox.mutate(mutant)
            del mutant.fitness.values
    
    return offspring

def plot_capital_curves(gen, train_capital_curve, test_capital_curve, phase_name):
    """绘制训练和测试资本曲线"""
    plt.figure(figsize=(12, 6))
    
    # 绘制训练资本曲线
    plt.subplot(1, 2, 1)
    plt.plot(train_capital_curve, 'b-', linewidth=2)
    plt.xlabel("Trade")
    plt.ylabel("Capital")
    plt.title(f"Train Capital Curve (Gen {gen})")
    plt.grid(True)
    
    # 绘制测试资本曲线
    plt.subplot(1, 2, 2)
    plt.plot(test_capital_curve, 'r-', linewidth=2)
    plt.xlabel("Trade")
    plt.ylabel("Capital")
    plt.title(f"Test Capital Curve (Gen {gen})")
    plt.grid(True)
    
    plt.tight_layout()
    
    # 创建目录
    os.makedirs(f"capital_curves/{phase_name}", exist_ok=True)
    
    # 保存图像
    plt.savefig(f"capital_curves/{phase_name}/gen_{gen:04d}.png", dpi=150, bbox_inches='tight')
    plt.close()
    
    logger.info(f"Saved capital curves for generation {gen}")

def plot_optimization_history(history, phase_name):
    """绘制优化历史指标"""
    plt.figure(figsize=(14, 10))
    
    # 1. 适应度变化
    plt.subplot(2, 2, 1)
    plt.plot(history['gen'], history['best_fitness'], 'b-o', label='Best Fitness')
    if 'test_fitness' in history:
        plt.plot(history['gen'], history['test_fitness'], 'r-o', label='Test Fitness')
    plt.xlabel("Generation")
    plt.ylabel("Fitness")
    plt.title("Fitness Evolution")
    plt.legend()
    plt.grid(True)
    
    # 2. 总收益变化
    plt.subplot(2, 2, 2)
    plt.plot(history['gen'], [r * 100 for r in history['best_return']], 'g-o', label='Train Return')
    if 'test_return' in history:
        plt.plot(history['gen'], [r * 100 for r in history['test_return']], 'r-o', label='Test Return')
    plt.xlabel("Generation")
    plt.ylabel("Total Return (%)")
    plt.title("Total Return Evolution")
    plt.legend()
    plt.grid(True)
    
    # 3. 最大回撤变化
    plt.subplot(2, 2, 3)
    plt.plot(history['gen'], [d * 100 for d in history['best_drawdown']], 'r-o', label='Train Drawdown')
    if 'test_drawdown' in history:
        plt.plot(history['gen'], [d * 100 for d in history['test_drawdown']], 'g-o', label='Test Drawdown')
    plt.xlabel("Generation")
    plt.ylabel("Max Drawdown (%)")
    plt.title("Max Drawdown Evolution")
    plt.legend()
    plt.grid(True)
    
    # 4. 夏普比率变化
    plt.subplot(2, 2, 4)
    plt.plot(history['gen'], history['best_sharpe'], 'm-o', label='Train Sharpe')
    if 'test_sharpe' in history:
        plt.plot(history['gen'], history['test_sharpe'], 'c-o', label='Test Sharpe')
    plt.xlabel("Generation")
    plt.ylabel("Sharpe Ratio")
    plt.title("Sharpe Ratio Evolution")
    plt.legend()
    plt.grid(True)
    
    plt.tight_layout()
    
    # 创建目录
    os.makedirs(f"optimization_results/{phase_name}", exist_ok=True)
    
    plt.savefig(f"optimization_results/{phase_name}/optimization_metrics_evolution.png", dpi=200, bbox_inches='tight')
    plt.close()

def setup_genetic_algorithm_phase(stock_lists, test_stock_lists, optimizable_params, base_params=None, 
                                 population_size=50, num_generations=100, 
                                 n_processes=None, fitness_weights=(0.2, 0.5, 0.3),
                                 save_interval=5, early_stopping_patience=25, diversity_threshold=0.05,
                                 phase_name="unknown"):
    """设置并运行遗传算法（分阶段版本）"""
    # 创建共享数据对象
    shared_data = SharedData(stock_lists)
    
    # 创建适应度类
    if not hasattr(creator, "FitnessMax"):
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    if not hasattr(creator, "Individual"):
        creator.create("Individual", list, fitness=creator.FitnessMax)
    
    # 初始化工具箱
    toolbox = base.Toolbox()
    toolbox.register("individual", tools.initIterate, creator.Individual, 
                    lambda: create_individual(optimizable_params))
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    
    # 注册遗传操作
    toolbox.register("mate", cxBlendAdaptive, alpha=0.5, optimizable_params=optimizable_params)
    toolbox.register("select", tools.selTournament, tournsize=3)

    adaptive_mutate_func = create_adaptive_mutate(diversity_threshold=0.1, optimizable_params=optimizable_params)
    toolbox.register("mutate", adaptive_mutate_func)
    
    # 添加边界检查装饰器
    toolbox.decorate("mate", lambda func: check_bounds_decorator(func, optimizable_params))
    toolbox.decorate("mutate", lambda func: check_bounds_decorator(func, optimizable_params))
    
    # 使用部分函数固定参数
    evaluate_with_params = partial(evaluate_strategy_global_phase, 
                                  initial_capital=200000, 
                                  fitness_weights=fitness_weights,
                                  optimizable_params=optimizable_params,
                                  base_params=base_params)
    toolbox.register("evaluate", evaluate_with_params)
    
    # 创建种群
    population = toolbox.population(n=population_size)
    
    # 设置并行处理
    if n_processes is None:
        n_processes = min(multiprocessing.cpu_count(), 20)
    logger.info(f"Using {n_processes} processes for parallel evaluation")
    
    # 初始化历史记录
    history = {
        'gen': [],
        'best_fitness': [],
        'best_return': [],
        'best_drawdown': [],
        'best_sharpe': [],
        'test_fitness': [],
        'test_return': [],
        'test_drawdown': [],
        'test_sharpe': [],
        'avg_fitness': [],
        'min_fitness': [],
        'max_fitness': [],
        'diversity': [],
        'cx_prob': [],
        'mut_prob': []
    }
    
    # 初始化交叉和变异概率
    cx_prob = 0.7
    mut_prob = 0.3
    
    # 早停机制变量
    best_fitness_history = []
    no_improvement_count = 0
    low_diversity_count = 0
    
    # 创建进程池并初始化
    with multiprocessing.Pool(processes=n_processes, initializer=init_worker, initargs=(shared_data,)) as pool:
        toolbox.register("map", pool.map)
        
        # 初始化统计和记录
        stats = tools.Statistics(lambda ind: ind.fitness.values[0])
        stats.register("avg", np.mean)
        stats.register("min", np.min)
        stats.register("max", np.max)
        stats.register("std", np.std)
        
        logbook = tools.Logbook()
        logbook.header = ["gen", "nevals"] + (stats.fields if stats else [])
        
        # 评估初始种群
        fitnesses = list(toolbox.map(toolbox.evaluate, population))
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = fit
        
        # 记录初始状态
        record = stats.compile(population)
        logbook.record(gen=0, nevals=len(population), **record)
        
        # 添加精英保留策略
        hof = tools.HallOfFame(1)
        hof.update(population)
        
        # 获取初始最佳个体
        best_individual = hof[0]
        best_fitness = best_individual.fitness.values[0]
        best_fitness_history.append(best_fitness)
        
        # 评估初始最佳个体的详细表现（训练集）
        all_fitnesses = []
        all_returns = []
        all_drawdowns = []
        all_sharpes = []
        
        for stock_sublist in stock_lists:
            fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
                best_individual, stock_sublist, 200000, fitness_weights, optimizable_params, base_params
            )
            all_fitnesses.append(fitness)
            all_returns.append(total_return)
            all_drawdowns.append(max_drawdown)
            all_sharpes.append(sharpe_ratio)
        
        avg_return = np.mean(all_returns)
        avg_drawdown = np.mean(all_drawdowns)
        avg_sharpe = np.mean(all_sharpes)
        
        # 评估初始最佳个体的详细表现（测试集）
        test_fitnesses = []
        test_returns = []
        test_drawdowns = []
        test_sharpes = []
        
        for test_sublist in test_stock_lists:
            fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
                best_individual, test_sublist, 200000, fitness_weights, optimizable_params, base_params
            )
            test_fitnesses.append(fitness)
            test_returns.append(total_return)
            test_drawdowns.append(max_drawdown)
            test_sharpes.append(sharpe_ratio)
        
        test_avg_fitness = np.mean(test_fitnesses)
        test_avg_return = np.mean(test_returns)
        test_avg_drawdown = np.mean(test_drawdowns)
        test_avg_sharpe = np.mean(test_sharpes)
        
        # 计算初始多样性
        diversity_score = diversity(population, optimizable_params)
        
        # 记录初始历史
        history['gen'].append(0)
        history['best_fitness'].append(best_fitness)
        history['best_return'].append(avg_return)
        history['best_drawdown'].append(avg_drawdown)
        history['best_sharpe'].append(avg_sharpe)
        history['test_fitness'].append(test_avg_fitness)
        history['test_return'].append(test_avg_return)
        history['test_drawdown'].append(test_avg_drawdown)
        history['test_sharpe'].append(test_avg_sharpe)
        history['avg_fitness'].append(record['avg'])
        history['min_fitness'].append(record['min'])
        history['max_fitness'].append(record['max'])
        history['diversity'].append(diversity_score)
        history['cx_prob'].append(cx_prob)
        history['mut_prob'].append(mut_prob)
        
        # 打印初始代信息
        logger.info(f"\n{'='*80}")
        logger.info(f"Initial Generation Summary:")
        logger.info(f"{'='*80}")
        logger.info(f"Best Fitness: {best_fitness:.6f}")
        logger.info(f"Average Return: {avg_return:.2%}")
        logger.info(f"Average Drawdown: {avg_drawdown:.2%}")
        logger.info(f"Average Sharpe Ratio: {avg_sharpe:.4f}")
        logger.info(f"Test Fitness: {test_avg_fitness:.6f}")
        logger.info(f"Test Return: {test_avg_return:.2%}")
        logger.info(f"Test Drawdown: {test_avg_drawdown:.2%}")
        logger.info(f"Test Sharpe Ratio: {test_avg_sharpe:.4f}")
        logger.info(f"Population Average Fitness: {record['avg']:.6f}")
        logger.info(f"Population Min Fitness: {record['min']:.6f}")
        logger.info(f"Population Max Fitness: {record['max']:.6f}")
        logger.info(f"Population Diversity: {diversity_score:.6f}")
        logger.info(f"Crossover Probability: {cx_prob:.2f}")
        logger.info(f"Mutation Probability: {mut_prob:.2f}")
        logger.info(f"{'='*80}\n")

        # 开始进化
        for gen in range(1, num_generations + 1):
            # 选择下一代
            offspring = toolbox.select(population, len(population))
            
            # 克隆选中的个体
            offspring = list(map(toolbox.clone, offspring))
            
            # 应用自适应交叉和变异
            diversity_score = diversity(population, optimizable_params)
            offspring = adaptive_cx_mutate(offspring, toolbox, cx_prob, mut_prob, diversity_score, optimizable_params)
            
            # 评估新个体
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = fit
            
            # 精英保留策略
            elite_size = max(1, int(0.1 * population_size))
            elites = tools.selBest(population, elite_size)
            
            # 更新种群
            population[:] = offspring
            
            # 用精英替换最差的个体
            worst_individuals = tools.selWorst(population, elite_size)
            for i, elite in enumerate(elites):
                idx = population.index(worst_individuals[i])
                population[idx] = toolbox.clone(elite)
            
            # 更新名人堂
            hof.update(population)
            
            # 记录统计信息
            record = stats.compile(population)
            logbook.record(gen=gen, nevals=len(invalid_ind), **record)
            
            # 获取当前最佳个体
            best_individual = hof[0]
            best_fitness = best_individual.fitness.values[0]
            best_fitness_history.append(best_fitness)
            
            # 评估最佳个体的详细表现（训练集）
            all_fitnesses = []
            all_returns = []
            all_drawdowns = []
            all_sharpes = []
            train_capital_curve = []
            
            for stock_sublist in stock_lists:
                fitness, total_return, max_drawdown, sharpe_ratio, capital_curve = evaluate_strategy_on_single_list(
                    best_individual, stock_sublist, 200000, fitness_weights, optimizable_params, base_params
                )
                all_fitnesses.append(fitness)
                all_returns.append(total_return)
                all_drawdowns.append(max_drawdown)
                all_sharpes.append(sharpe_ratio)
                train_capital_curve = capital_curve  # 取最后一个子列表的资本曲线
            
            avg_return = np.mean(all_returns)
            avg_drawdown = np.mean(all_drawdowns)
            avg_sharpe = np.mean(all_sharpes)
            
            # 评估最佳个体的详细表现（测试集）
            test_fitnesses = []
            test_returns = []
            test_drawdowns = []
            test_sharpes = []
            test_capital_curve = []
            
            for test_sublist in test_stock_lists:
                fitness, total_return, max_drawdown, sharpe_ratio, capital_curve = evaluate_strategy_on_single_list(
                    best_individual, test_sublist, 200000, fitness_weights, optimizable_params, base_params
                )
                test_fitnesses.append(fitness)
                test_returns.append(total_return)
                test_drawdowns.append(max_drawdown)
                test_sharpes.append(sharpe_ratio)
                test_capital_curve = capital_curve  # 取最后一个子列表的资本曲线
            
            test_avg_fitness = np.mean(test_fitnesses)
            test_avg_return = np.mean(test_returns)
            test_avg_drawdown = np.mean(test_drawdowns)
            test_avg_sharpe = np.mean(test_sharpes)
            
            # 更新交叉和变异概率
            diversity_score = diversity(population, optimizable_params)
            if diversity_score < 0.1:
                mut_prob = min(0.8, mut_prob * 1.5)
                cx_prob = max(0.2, cx_prob * 0.8)
            elif diversity_score > 0.5:
                cx_prob = min(0.9, cx_prob * 1.2)
                mut_prob = max(0.1, mut_prob * 0.8)
            
            # 记录历史
            history['gen'].append(gen)
            history['best_fitness'].append(best_fitness)
            history['best_return'].append(avg_return)
            history['best_drawdown'].append(avg_drawdown)
            history['best_sharpe'].append(avg_sharpe)
            history['test_fitness'].append(test_avg_fitness)
            history['test_return'].append(test_avg_return)
            history['test_drawdown'].append(test_avg_drawdown)
            history['test_sharpe'].append(test_avg_sharpe)
            history['avg_fitness'].append(record['avg'])
            history['min_fitness'].append(record['min'])
            history['max_fitness'].append(record['max'])
            history['diversity'].append(diversity_score)
            history['cx_prob'].append(cx_prob)
            history['mut_prob'].append(mut_prob)
            
            # 每隔10代绘制资本曲线
            if gen % 10 == 0:
                plot_capital_curves(gen, train_capital_curve, test_capital_curve, phase_name)
            
            # 检查早停条件
            if len(best_fitness_history) > 1:
                if abs(best_fitness - max(best_fitness_history[:-1])) < 1e-8:
                    no_improvement_count += 1
                else:
                    no_improvement_count = 0
            
            if diversity_score < diversity_threshold:
                low_diversity_count += 1
            else:
                low_diversity_count = 0
            
            # 打印当前代信息
            logger.info(f"\n{'='*80}")
            logger.info(f"Generation {gen} Summary:")
            logger.info(f"{'='*80}")
            logger.info(f"Best Fitness: {best_fitness:.6f}")
            logger.info(f"Average Return: {avg_return:.2%}")
            logger.info(f"Average Drawdown: {avg_drawdown:.2%}")
            logger.info(f"Average Sharpe Ratio: {avg_sharpe:.4f}")
            logger.info(f"Test Fitness: {test_avg_fitness:.6f}")
            logger.info(f"Test Return: {test_avg_return:.2%}")
            logger.info(f"Test Drawdown: {test_avg_drawdown:.2%}")
            logger.info(f"Test Sharpe Ratio: {test_avg_sharpe:.4f}")
            logger.info(f"Population Average Fitness: {record['avg']:.6f}")
            logger.info(f"Population Min Fitness: {record['min']:.6f}")
            logger.info(f"Population Max Fitness: {record['max']:.6f}")
            logger.info(f"Population Diversity: {diversity_score:.6f}")
            logger.info(f"Crossover Probability: {cx_prob:.2f}")
            logger.info(f"Mutation Probability: {mut_prob:.2f}")
            logger.info(f"No Improvement Count: {no_improvement_count}/{early_stopping_patience}")
            logger.info(f"Low Diversity Count: {low_diversity_count}/{early_stopping_patience}")
            logger.info(f"Number of Evaluated Individuals: {len(invalid_ind)}")

            if gen % 5 == 0:
                logger.info(f"\nBest Individual Parameters (Generation {gen}):")
                for i, param in enumerate(optimizable_params):
                    min_val, max_val, param_type = PARAM_RANGES[param]
                    value = best_individual[i]
                    if value < min_val or value > max_val:
                        value = np.clip(value, min_val, max_val)
                    logger.info(f"  {param}: {value:.6f} ({param_type.__name__})")

            logger.info(f"{'='*80}\n")

            # 定期保存结果
            if gen % save_interval == 0 or gen == num_generations:
                best_params = decode_individual(best_individual, optimizable_params, base_params)
                save_optimization_state_phase(gen, best_individual, best_params, best_fitness, 
                                            avg_return, avg_drawdown, avg_sharpe, stock_lists, 
                                            fitness_weights, optimizable_params, base_params)
            
            # 检查早停条件
            if no_improvement_count >= early_stopping_patience:
                logger.info(f"Early stopping triggered due to no improvement for {early_stopping_patience} generations")
                break
                
            if low_diversity_count >= early_stopping_patience:
                logger.info(f"Early stopping triggered due to low diversity for {early_stopping_patience} generations")
                break
        
        # 获取最终最佳个体
        best_individual = hof[0]
        best_fitness = best_individual.fitness.values[0]
        best_params = decode_individual(best_individual, optimizable_params, base_params)
        
        # 评估最终最佳个体的表现（训练集）
        all_fitnesses = []
        all_returns = []
        all_drawdowns = []
        all_sharpes = []
        
        for stock_sublist in stock_lists:
            fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
                best_individual, stock_sublist, 200000, fitness_weights, optimizable_params, base_params
            )
            all_fitnesses.append(fitness)
            all_returns.append(total_return)
            all_drawdowns.append(max_drawdown)
            all_sharpes.append(sharpe_ratio)
        
        avg_return = np.mean(all_returns)
        avg_drawdown = np.mean(all_drawdowns)
        avg_sharpe = np.mean(all_sharpes)
        
        # 评估最终最佳个体的表现（测试集）
        test_fitnesses = []
        test_returns = []
        test_drawdowns = []
        test_sharpes = []
        
        for test_sublist in test_stock_lists:
            fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
                best_individual, test_sublist, 200000, fitness_weights, optimizable_params, base_params
            )
            test_fitnesses.append(fitness)
            test_returns.append(total_return)
            test_drawdowns.append(max_drawdown)
            test_sharpes.append(sharpe_ratio)
        
        test_avg_fitness = np.mean(test_fitnesses)
        test_avg_return = np.mean(test_returns)
        test_avg_drawdown = np.mean(test_drawdowns)
        test_avg_sharpe = np.mean(test_sharpes)
        
        # 绘制最终的优化历史
        plot_optimization_history(history, phase_name)
        
        return best_individual, best_params, best_fitness, avg_return, avg_drawdown, avg_sharpe, test_avg_fitness, test_avg_return, test_avg_drawdown, test_avg_sharpe, logbook, history

def save_optimization_state_phase(gen, individual, params, fitness, total_return, 
                                 max_drawdown, sharpe_ratio, stock_lists, fitness_weights,
                                 optimizable_params, base_params):
    """保存优化状态（分阶段版本）"""
    state = {
        'generation': gen,
        'fitness': fitness,
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'params': params,
        'timestamp': datetime.datetime.now().isoformat(),
        'individual': individual,
        'optimizable_params': optimizable_params,
        'base_params': base_params
    }
    
    phase_name = "_".join(optimizable_params[:2]) if optimizable_params else "unknown"
    os.makedirs(f"optimization_results/{phase_name}", exist_ok=True)
    
    with open(f"optimization_results/{phase_name}/gen_{gen:04d}.json", "w") as f:
        json.dump(state, f, indent=2, default=lambda o: o.tolist() if hasattr(o, 'tolist') else o)
    
    with open(f"optimization_results/{phase_name}/gen_{gen:04d}.pkl", "wb") as f:
        pickle.dump(state, f)
    
    logger.info(f"Saved state for generation {gen}: Fitness={fitness:.4f}, Return={total_return:.2%}")

def optimize_in_phases(stock_lists, test_stock_lists, population_size=30, num_generations=50, 
                      fitness_weights=(0.2, 0.5, 0.3), save_interval=5,
                      early_stopping_patience=15, diversity_threshold=0.05):
    """分阶段优化参数"""
    logger.info("Starting phased genetic algorithm optimization...")
    
    # 初始化基础参数
    base_params = DEFAULT_PARAMS.copy()
    all_optimized_params = {}
    
    # 按阶段优化
    for phase_name, optimizable_params in PARAM_GROUPS.items():
        logger.info(f"\n{'='*80}")
        logger.info(f"Starting {phase_name} phase")
        logger.info(f"Optimizing parameters: {optimizable_params}")
        logger.info(f"{'='*80}")
        
        # 运行当前阶段的优化
        (best_individual, best_params, best_fitness, 
         best_return, best_drawdown, sharpe_ratio, 
         test_fitness, test_return, test_drawdown, test_sharpe,
         logbook, history) = setup_genetic_algorithm_phase(
            stock_lists,
            test_stock_lists,
            optimizable_params=optimizable_params,
            base_params=base_params,
            population_size=population_size,
            num_generations=num_generations,
            fitness_weights=fitness_weights,
            save_interval=save_interval,
            early_stopping_patience=early_stopping_patience,
            diversity_threshold=diversity_threshold,
            phase_name=phase_name
        )
        
        # 更新基础参数（将当前阶段优化的参数加入）
        base_params.update(best_params)
        all_optimized_params.update(best_params)
        
        # 记录当前阶段结果
        logger.info(f"\n{phase_name} completed!")
        logger.info(f"Best fitness: {best_fitness:.4f}")
        logger.info(f"Total return: {best_return:.2%}")
        logger.info(f"Max drawdown: {best_drawdown:.2%}")
        logger.info(f"Sharpe ratio: {sharpe_ratio:.4f}")
        logger.info(f"Test fitness: {test_fitness:.4f}")
        logger.info(f"Test return: {test_return:.2%}")
        logger.info(f"Test drawdown: {test_drawdown:.2%}")
        logger.info(f"Test Sharpe: {test_sharpe:.4f}")
        
        # 保存当前阶段的最佳参数
        phase_dir = f"optimization_results/{phase_name}"
        os.makedirs(phase_dir, exist_ok=True)
        
        with open(f"{phase_dir}/best_params.pkl", "wb") as f:
            pickle.dump({
                'params': best_params,
                'fitness': best_fitness,
                'return': best_return,
                'drawdown': best_drawdown,
                'sharpe': sharpe_ratio,
                'test_fitness': test_fitness,
                'test_return': test_return,
                'test_drawdown': test_drawdown,
                'test_sharpe': test_sharpe,
                'individual': best_individual
            }, f)
        
        with open(f"{phase_dir}/best_params.json", "w") as f:
            json.dump({
                'params': best_params,
                'fitness': best_fitness,
                'return': best_return,
                'drawdown': best_drawdown,
                'sharpe': sharpe_ratio,
                'test_fitness': test_fitness,
                'test_return': test_return,
                'test_drawdown': test_drawdown,
                'test_sharpe': test_sharpe,
                'individual': best_individual.tolist() if hasattr(best_individual, 'tolist') else list(best_individual)
            }, f, indent=2)
    
    # 最终评估所有优化参数
    logger.info(f"\n{'='*80}")
    logger.info("Final evaluation with all optimized parameters")
    logger.info(f"{'='*80}")
    
    # 创建最终个体进行评估
    final_individual = []
    for param in list(PARAM_RANGES.keys()):
        if param in all_optimized_params:
            final_individual.append(all_optimized_params[param])
        else:
            # 使用默认值
            min_val, max_val, param_type = PARAM_RANGES[param]
            if param_type == int:
                final_individual.append(random.randint(min_val, max_val))
            elif param_type == bool:
                final_individual.append(random.randint(0, 1))
            else:
                final_individual.append(random.uniform(min_val, max_val))
    
    # 评估最终参数组合（训练集）
    all_fitnesses = []
    all_returns = []
    all_drawdowns = []
    all_sharpes = []
    
    for stock_sublist in stock_lists:
        fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
            final_individual, stock_sublist, 200000, fitness_weights
        )
        all_fitnesses.append(fitness)
        all_returns.append(total_return)
        all_drawdowns.append(max_drawdown)
        all_sharpes.append(sharpe_ratio)
    
    final_fitness = np.mean(all_fitnesses)
    final_return = np.mean(all_returns)
    final_drawdown = np.mean(all_drawdowns)
    final_sharpe = np.mean(all_sharpes)
    
    # 评估最终参数组合（测试集）
    test_fitnesses = []
    test_returns = []
    test_drawdowns = []
    test_sharpes = []
    
    for test_sublist in test_stock_lists:
        fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
            final_individual, test_sublist, 200000, fitness_weights
        )
        test_fitnesses.append(fitness)
        test_returns.append(total_return)
        test_drawdowns.append(max_drawdown)
        test_sharpes.append(sharpe_ratio)
    
    test_fitness = np.mean(test_fitnesses)
    test_return = np.mean(test_returns)
    test_drawdown = np.mean(test_drawdowns)
    test_sharpe = np.mean(test_sharpes)
    
    logger.info(f"Final results with all optimized parameters:")
    logger.info(f"Fitness: {final_fitness:.4f}")
    logger.info(f"Total return: {final_return:.2%}")
    logger.info(f"Max drawdown: {final_drawdown:.2%}")
    logger.info(f"Sharpe ratio: {final_sharpe:.4f}")
    logger.info(f"Test fitness: {test_fitness:.4f}")
    logger.info(f"Test return: {test_return:.2%}")
    logger.info(f"Test drawdown: {test_drawdown:.2%}")
    logger.info(f"Test Sharpe: {test_sharpe:.4f}")
    
    # 保存最终参数
    with open("optimization_results/final_params.pkl", "wb") as f:
        pickle.dump({
            'params': all_optimized_params,
            'fitness': final_fitness,
            'return': final_return,
            'drawdown': final_drawdown,
            'sharpe': final_sharpe,
            'test_fitness': test_fitness,
            'test_return': test_return,
            'test_drawdown': test_drawdown,
            'test_sharpe': test_sharpe,
        }, f)
    
    with open("optimization_results/final_params.json", "w") as f:
        json.dump({
            'params': all_optimized_params,
            'fitness': final_fitness,
            'return': final_return,
            'drawdown': final_drawdown,
            'sharpe': final_sharpe,
            'test_fitness': test_fitness,
            'test_return': test_return,
            'test_drawdown': test_drawdown,
            'test_sharpe': test_sharpe,
        }, f, indent=2)
    
    return all_optimized_params, final_fitness, final_return, final_drawdown, final_sharpe, test_fitness, test_return, test_drawdown, test_sharpe

def time_series_cv_split(data, n_splits=5):
    """时间序列交叉验证分割"""
    splits = []
    total_size = len(data)
    test_size = total_size // n_splits
    
    for i in range(n_splits):
        train_end = total_size - test_size * (n_splits - i)
        test_start = train_end
        test_end = test_start + test_size
        
        train_data = data[:train_end]
        test_data = data[test_start:test_end]
        splits.append((train_data, test_data))
    
    return splits

def out_of_sample_test(optimized_params, test_stock_lists):
    """样本外测试"""
    logger.info("Running out-of-sample test...")
    
    # 创建个体
    test_individual = []
    for param in list(PARAM_RANGES.keys()):
        if param in optimized_params:
            test_individual.append(optimized_params[param])
        else:
            min_val, max_val, param_type = PARAM_RANGES[param]
            if param_type == int:
                test_individual.append(random.randint(min_val, max_val))
            elif param_type == bool:
                test_individual.append(random.randint(0, 1))
            else:
                test_individual.append(random.uniform(min_val, max_val))
    
    all_fitnesses = []
    all_returns = []
    all_drawdowns = []
    all_sharpes = []
    
    for stock_sublist in test_stock_lists:
        fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
            test_individual, stock_sublist, 200000, fitness_weights=(0.3, 0.42, 0.28)
        )
        all_fitnesses.append(fitness)
        all_returns.append(total_return)
        all_drawdowns.append(max_drawdown)
        all_sharpes.append(sharpe_ratio)
    
    test_fitness = np.mean(all_fitnesses)
    test_return = np.mean(all_returns)
    test_drawdown = np.mean(all_drawdowns)
    test_sharpe = np.mean(all_sharpes)
    
    logger.info(f"Out-of-sample results:")
    logger.info(f"Fitness: {test_fitness:.4f}")
    logger.info(f"Return: {test_return:.2%}")
    logger.info(f"Drawdown: {test_drawdown:.2%}")
    logger.info(f"Sharpe: {test_sharpe:.4f}")
    
    return test_fitness, test_return, test_drawdown, test_sharpe

def calculate_overfitting_degree(train_performance, test_performance):
    """计算过拟合程度"""
    train_fitness, train_return, train_drawdown, train_sharpe = train_performance
    test_fitness, test_return, test_drawdown, test_sharpe = test_performance
    
    overfitting_ratio = {
        'fitness': train_fitness / max(test_fitness, 1e-8),
        'return': train_return / max(test_return, 1e-8),
        'sharpe': train_sharpe / max(test_sharpe, 1e-8)
    }
    
    return overfitting_ratio

def plot_final_optimization_results(logbook, best_params, best_return, best_drawdown, sharpe_ratio, 
                                  test_return=None, test_drawdown=None, test_sharpe=None):
    """绘制最终优化结果"""
    plt.figure(figsize=(14, 12))
    
    # 1. 绘制进化过程
    gen = logbook.select("gen")
    avg_fitness = logbook.select("avg")
    min_fitness = logbook.select("min")
    max_fitness = logbook.select("max")
    
    plt.subplot(3, 1, 1)
    plt.plot(gen, avg_fitness, 'b-', label="Average Fitness")
    plt.plot(gen, min_fitness, 'r-', label="Min Fitness")
    plt.plot(gen, max_fitness, 'g-', label="Max Fitness")
    plt.fill_between(gen, min_fitness, max_fitness, color='gray', alpha=0.1)
    plt.xlabel("Generation")
    plt.ylabel("Fitness")
    plt.title("Evolution of Fitness")
    plt.legend()
    plt.grid(True)
    
    # 2. 绘制最佳参数
    plt.subplot(3, 1, 2)
    param_names = list(best_params.keys())
    param_values = list(best_params.values())
    
    # 创建参数类型标签
    param_types = []
    for param in param_names:
        _, _, param_type = PARAM_RANGES.get(param, (0, 0, float))
        param_types.append(f"{param} ({param_type.__name__})")
    
    # 水平条形图
    y_pos = np.arange(len(param_types))
    plt.barh(y_pos, param_values, color='skyblue')
    plt.yticks(y_pos, param_types)
    plt.xlabel("Value")
    plt.title("Optimized Parameters")
    
    # 3. 添加参数值文本
    plt.subplot(3, 1, 3)
    plt.axis('off')
    
    # 创建结果文本
    result_text = f"Optimized Strategy Parameters:\n\n"
    for param, value in best_params.items():
        result_text += f"{param}: {value:.6f}\n"
    
    result_text += f"\nTraining Performance:\n"
    result_text += f"Total Return: {best_return:.2%}\n"
    result_text += f"Max Drawdown: {best_drawdown:.2%}\n"
    result_text += f"Sharpe Ratio: {sharpe_ratio:.4f}\n"
    
    if test_return is not None:
        result_text += f"\nTest Performance:\n"
        result_text += f"Total Return: {test_return:.2%}\n"
        result_text += f"Max Drawdown: {test_drawdown:.2%}\n"
        result_text += f"Sharpe Ratio: {test_sharpe:.4f}\n"
    
    plt.text(0.1, 0.5, result_text,
             fontsize=10, 
             bbox=dict(facecolor='lightyellow', alpha=0.5),
             verticalalignment='center')
    
    # 添加整体标题
    plt.suptitle(
        f"Optimized Stock Monitoring Strategy\n"
        f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        fontsize=16
    )
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig("optimization_results/final_optimization_results.png", dpi=300, bbox_inches='tight')
    plt.close()

if __name__ == "__main__":
    from evaluater_generate_datas import build_evaluater_1to2_data_list_from_file
    
    # 加载数据
    stock_lists = build_evaluater_1to2_data_list_from_file(200)
    logger.info(f"Generated {len(stock_lists)} stock sublists, each with {len(stock_lists[0])} stocks")
    
    # 分割训练和测试数据
    train_data = stock_lists[0]  # 第一个子列表作为训练数据
    test_data = stock_lists[1]   # 第二个子列表作为测试数据
    
    # 运行分阶段优化
    (optimized_params, final_fitness, final_return, 
     final_drawdown, final_sharpe, test_fitness, 
     test_return, test_drawdown, test_sharpe) = optimize_in_phases(
        [train_data],  # 使用训练数据
        [test_data],   # 使用测试数据
        population_size=100,
        num_generations=100,
        fitness_weights=(0.3, 0.42, 0.28),
        save_interval=5,
        early_stopping_patience=15,
        diversity_threshold=0.05
    )
    
    # 样本外测试
    test_fitness, test_return, test_drawdown, test_sharpe = out_of_sample_test(
        optimized_params, [test_data]
    )
    
    # 计算过拟合程度
    overfitting_ratio = calculate_overfitting_degree(
        (final_fitness, final_return, final_drawdown, final_sharpe),
        (test_fitness, test_return, test_drawdown, test_sharpe)
    )
    
    logger.info(f"\nOverfitting analysis:")
    logger.info(f"Fitness overfitting ratio: {overfitting_ratio['fitness']:.2f}")
    logger.info(f"Return overfitting ratio: {overfitting_ratio['return']:.2f}")
    logger.info(f"Sharpe overfitting ratio: {overfitting_ratio['sharpe']:.2f}")
    
    # 保存过拟合分析
    with open("optimization_results/overfitting_analysis.json", "w") as f:
        json.dump({
            'train_performance': {
                'fitness': final_fitness,
                'return': final_return,
                'drawdown': final_drawdown,
                'sharpe': final_sharpe
            },
            'test_performance': {
                'fitness': test_fitness,
                'return': test_return,
                'drawdown': test_drawdown,
                'sharpe': test_sharpe
            },
            'overfitting_ratio': overfitting_ratio
        }, f, indent=2)
    
    # 绘制最终优化结果
    # 这里需要从最后一个阶段获取logbook，但为了简化，我们直接使用最终参数绘制
    # 在实际应用中，您可能需要保存每个阶段的logbook并在最后使用
    plot_final_optimization_results(
        tools.Logbook(),  # 空的logbook，实际应用中应该使用真实的logbook
        optimized_params, 
        final_return, 
        final_drawdown, 
        final_sharpe,
        test_return,
        test_drawdown,
        test_sharpe
    )