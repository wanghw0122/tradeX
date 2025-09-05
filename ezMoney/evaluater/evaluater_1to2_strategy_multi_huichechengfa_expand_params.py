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
    'cold_start_steps': (0, 50, int),
    'max_abserve_tick_steps': (1, 1000, int),
    'max_abserce_avg_price_down_steps': (1, 15, int),
    'stop_profit_open_hc_pct': (-0.15, 0.0, float),
    'dynamic_hc_stop_profit_thres': (0.01, 8, float),
    'last_close_price_hc_pct': (-0.04, 0.01, float),
    'last_day_sell_thres': (0.01, 1.0, float),
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
    'max_rebounds': (0, 15, int),
    'decline_ratio_threshold': (15, 1500, int),
    'flxd_ticks': (0, 500, int),
    'flzz_ticks': (100, 2000, int),
    'use_simiple_kline_strategy_flxd': (0, 1, bool),
    'use_simiple_kline_strategy_flzz': (0, 1, bool),
    'flzz_use_smooth_price': (0, 1, bool),
    'flzz_zf_thresh': (-0.07, 0.1, float),
    'kline_sell_flxd_zy': (0, 1, bool),
    'kline_sell_flxd_zs': (0, 1, bool),
    'kline_sell_flzz_zs': (0, 1, bool),
    'kline_sell_flzz_zy': (0, 1, bool),
    'last_open_price_hc_pct': (-0.08, 0.01, float),
    'open_price_max_hc': (-0.1, 0, float),

    'loss_per_step_tick_gap': (1, 25, int),
    'loss_cold_start_steps': (0, 30, int),
    'loss_max_abserve_tick_steps': (5, 500, int),
    'loss_max_abserce_avg_price_down_steps': (1, 15, int),
    'loss_dynamic_hc_stop_profit_thres': (0.01, 8, float),
    'loss_last_close_price_hc_pct': (-0.08, 0.01, float),
    'loss_last_open_price_hc_pct': (-0.08, 0.01, float),
    'loss_open_price_max_hc': (-0.1, 0, float),
    'loss_down_open_sell_wait_time': (0, 1, bool),
    'down_open_sell_wait_time': (0, 1, bool),

    'day_zy_line': (0, 1, float),
    'day_zs_line': (-1, 0, float),
    'sell_afternoon': (0, 1, bool),
    'sell_half_afternoon': (0, 1, bool),
    'sell_max_days': (1, 4, int),
}
# 需要优化的参数列表
OPTIMIZABLE_PARAMS = [
    'per_step_tick_gap',
    'cold_start_steps',
    'max_abserve_tick_steps',
    'max_abserce_avg_price_down_steps',
    'stop_profit_open_hc_pct',
    'dynamic_hc_stop_profit_thres',
    'last_close_price_hc_pct',
    'last_day_sell_thres',
    'last_day_sell_huiche',
    'fd_mount',
    'fd_vol_pct',
    'fd_ju_ticks',
    'max_zb_times',
    'stagnation_kline_ticks',
    'decline_kline_ticks',
    'yang_yin_threshold',
    'stagnation_n',
    'stagnation_volume_ratio_threshold',
    'stagnation_ratio_threshold',
    'decline_volume_ratio_threshold',
    'max_rebounds',
    'decline_ratio_threshold',
    'flxd_ticks',
    'flzz_ticks',
    'use_simiple_kline_strategy_flxd',
    'use_simiple_kline_strategy_flzz',
    'flzz_use_smooth_price',
    'flzz_zf_thresh',
    'kline_sell_flxd_zy',
    'kline_sell_flxd_zs',
    'kline_sell_flzz_zs',
    'kline_sell_flzz_zy',
    'last_open_price_hc_pct',
    'open_price_max_hc',
    'loss_per_step_tick_gap',
    'loss_cold_start_steps',
    'loss_max_abserve_tick_steps',
    'loss_max_abserce_avg_price_down_steps',
    'loss_dynamic_hc_stop_profit_thres',
    'loss_last_close_price_hc_pct',
    'loss_last_open_price_hc_pct',
    'loss_open_price_max_hc',
    'loss_down_open_sell_wait_time',
    'down_open_sell_wait_time',

    'day_zy_line',
    'day_zs_line',
    'sell_afternoon',
    'sell_half_afternoon',
    'sell_max_days',
]

# OPTIMIZABLE_PARAMS = list(PARAM_RANGES.keys())

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
        # 定义如何序列化对象
        return self.__dict__
    
    def __setstate__(self, state):
        # 定义如何反序列化对象
        self.__dict__.update(state)

def init_worker(shared_data):
    global global_shared_data
    global_shared_data = shared_data

def create_individual():
    """创建个体（一组参数）"""
    individual = []
    for param in OPTIMIZABLE_PARAMS:
        min_val, max_val, param_type = PARAM_RANGES[param]
        
        if param_type == int:
            individual.append(random.randint(min_val, max_val))
        elif param_type == bool:
            individual.append(random.randint(0, 1))
        else:
            individual.append(random.uniform(min_val, max_val))
    
    return individual


def create_diverse_individual():
    individual = []
    for param in OPTIMIZABLE_PARAMS:
        min_val, max_val, param_type = PARAM_RANGES[param]
        if param_type == int:
            individual.append(random.randint(min_val, max_val))
        elif param_type == bool:
            individual.append(random.randint(0, 1))
        else:
            # 使用多种分布生成初始值，增加多样性
            if random.random() < 0.5:
                # 均匀分布
                value = random.uniform(min_val, max_val)
            else:
                # 正态分布（集中在中间区域）
                mean = (min_val + max_val) / 2
                std = (max_val - min_val) / 6  # 99.7%的值在范围内
                value = random.gauss(mean, std)
                value = max(min_val, min(max_val, value))
            individual.append(value)
    return individual

def decode_individual(individual):
    """将遗传算法中的个体解码为参数字典 - 添加验证和类型转换"""
    params = {}
    for i, param in enumerate(OPTIMIZABLE_PARAMS):
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
        
        # 特殊处理：某些参数需要缩放
        # if param == 'max_abserve_tick_steps':
        #     value *= 10
        # elif param == 'stagnation_ratio_threshold':
        #     value *= 10
        # elif param == 'fd_mount':
        #     value *= 10000000
        # elif param == 'decline_ratio_threshold':
        #     value *= 10
        # elif param == 'flxd_ticks':
        #     value *= 100
        
        params[param] = value
    
    # 添加固定参数
    params['stop_profit_pct'] = 0.0
    params['static_hc_stop_profit_pct'] = 1.0
    params['loss_static_hc_stop_profit_pct'] = 1.0
    
    return params

def evaluate_strategy_on_single_list(individual, stock_sublist, initial_capital=200000, 
                                    fitness_weights=(0.33, 0.34, 0.33), max_drawdown_threshold=0.25):
    """评估策略在单个股票子列表上的表现 - 增加对回撤的惩罚"""
    try:
        params = decode_individual(individual)
        capital = initial_capital
        capital_curve = [capital]
        daily_returns = []
        
        stock_count = 0
        profitable_trades = 0
        total_profit = 0
        
        day_zy_line = params['day_zy_line']
        day_zs_line = params['day_zs_line']
        sell_afternoon = params['sell_afternoon']
        sell_half_afternoon = params['sell_half_afternoon']
        sell_max_days = params['sell_max_days']

        for stock_data in stock_sublist:
            stock_count += 1
            stock_code = stock_data['stock_code']
            trade_price = stock_data['trade_price']
            
            cur_res_datas = stock_data['cur_res_datas']
            if not cur_res_datas or len(cur_res_datas) != 4:
                raise ValueError(f"股票 {stock_code} 数据异常")
            i = 0
            actual_sell_price = 0
            actual_sell_prices = []

            for cur_res_data in cur_res_datas:
                i = i + 1
                stock_infos = {}
                stock_infos['trade_price'] = trade_price
                stock_infos['order_price'] = trade_price
                stock_infos['origin_trade_price'] = trade_price
                stock_infos['row_id'] = random.randint(0, 1000000)
                open = cur_res_data['open']
                close = cur_res_data['close']
                next_open = cur_res_data['next_open']
                next_close = cur_res_data['next_close']
                tick_datas = cur_res_data['tick_datas']
                pre_avg_volumes = cur_res_data['pre_volumes']
                pre_volume = cur_res_data['n_pre_volume']
                mkt_datas = cur_res_data['mkt_datas']
                open_profit = open / trade_price - 1
                close_profit = close / trade_price - 1
                monitor_type = 0
                if open_profit > day_zy_line:
                    monitor_type = 1
                elif open_profit < day_zs_line:
                    monitor_type = 2
                else:
                    monitor_type = 0
                if monitor_type == 0:
                    if sell_afternoon:
                        if i >= sell_max_days or i >= 4:
                            actual_sell_price = close
                            if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                actual_sell_price = next_open
                            if actual_sell_prices:
                                actual_sell_prices.append(actual_sell_price)
                                break
                            else:
                                actual_sell_prices.append(actual_sell_price)
                                actual_sell_prices.append(actual_sell_price)
                                break
                        if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                continue
                        if close_profit > day_zy_line or close_profit < day_zs_line:
                            actual_sell_price = close
                            if sell_half_afternoon:
                                if actual_sell_prices:
                                    actual_sell_prices.append(actual_sell_price)
                                    break
                                else:
                                    actual_sell_prices.append(actual_sell_price)
                                    continue
                            else:
                                if actual_sell_prices:
                                    actual_sell_prices.append(actual_sell_price)
                                    break
                                else:
                                    actual_sell_prices.append(actual_sell_price)
                                    actual_sell_prices.append(actual_sell_price)
                                    break
                        else:
                            if i >= sell_max_days or i >= 4:
                                actual_sell_price = close
                                if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                    actual_sell_price = next_open
                                if actual_sell_prices:
                                    actual_sell_prices.append(actual_sell_price)
                                    break
                                else:
                                    actual_sell_prices.append(actual_sell_price)
                                    actual_sell_prices.append(actual_sell_price)
                                    break
                            else:
                                continue
                    else:
                        if i >= sell_max_days or i >= 4:
                            actual_sell_price = close
                            if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                actual_sell_price = next_open
                            if actual_sell_prices:
                                actual_sell_prices.append(actual_sell_price)
                                break
                            else:
                                actual_sell_prices.append(actual_sell_price)
                                actual_sell_prices.append(actual_sell_price)
                                break
                        else:
                            continue
                else:
                    stock_infos['monitor_type'] = monitor_type
                    stock_infos['tick_datas'] = tick_datas
                    stock_infos['pre_avg_volumes'] = pre_avg_volumes
                    stock_infos['n_pre_volume'] = pre_volume
                    monitor = StockMonitor(
                        stock_code=stock_code,
                        stock_name='',
                        stock_infos=stock_infos,
                        mkt_datas=mkt_datas,
                        params=params
                    )
                    sold, sell_price = monitor.get_result()

                    if sold:
                        actual_sell_price = sell_price
                        if actual_sell_prices:
                            actual_sell_prices.append(actual_sell_price)
                            break
                        else:
                            actual_sell_prices.append(actual_sell_price)
                            actual_sell_prices.append(actual_sell_price)
                            break
                    else:
                        if i >= sell_max_days or i >= 4:
                            actual_sell_price = close
                            if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                actual_sell_price = next_open
                            if actual_sell_prices:
                                actual_sell_prices.append(actual_sell_price)
                                break
                            else:
                                actual_sell_prices.append(actual_sell_price)
                                actual_sell_prices.append(actual_sell_price)
                                break
                        if sell_afternoon:
                            if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                continue
                            if close_profit > day_zy_line or close_profit < day_zs_line:
                                actual_sell_price = close
                                if sell_half_afternoon:
                                    if actual_sell_prices:
                                        actual_sell_prices.append(actual_sell_price)
                                        break
                                    else:
                                        actual_sell_prices.append(actual_sell_price)
                                        continue
                                else:
                                    if actual_sell_prices:
                                        actual_sell_prices.append(actual_sell_price)
                                        break
                                    else:
                                        actual_sell_prices.append(actual_sell_price)
                                        actual_sell_prices.append(actual_sell_price)
                                        break
                            else:
                                if i >= sell_max_days or i >= 4:
                                    actual_sell_price = close
                                    if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                        actual_sell_price = next_open
                                    if actual_sell_prices:
                                        actual_sell_prices.append(actual_sell_price)
                                        break
                                    else:
                                        actual_sell_prices.append(actual_sell_price)
                                        actual_sell_prices.append(actual_sell_price)
                                        break
                                else:
                                    continue
                        else:
                            if i >= sell_max_days or i >= 4:
                                actual_sell_price = close
                                if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                    actual_sell_price = next_open
                                if actual_sell_prices:
                                    actual_sell_prices.append(actual_sell_price)
                                    break
                                else:
                                    actual_sell_prices.append(actual_sell_price)
                                    actual_sell_prices.append(actual_sell_price)
                                    break
                            else:
                                continue
                    
            if len(actual_sell_prices) != 2:
                raise ValueError(f"股票 {stock_code} 数据异常 售卖异常")
            
            actual_sell_price = (actual_sell_prices[0] + actual_sell_prices[1]) / 2

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
        
        # 增加对回撤的惩罚 - 使用传入的回撤阈值
        drawdown_penalty = 1.0
        if max_drawdown > max_drawdown_threshold:
            # 指数惩罚，回撤越大惩罚越重
            drawdown_penalty = np.exp(-5 * (max_drawdown - max_drawdown_threshold))

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

def evaluate_strategy(individual, stock_lists, initial_capital=200000, 
                      fitness_weights=(0.4, 0.3, 0.3), return_capital_curve=False, max_drawdown_threshold=0.25):
    """
    评估策略在多个股票列表上的平均表现
    
    参数:
        individual: 个体参数
        stock_lists: 二维股票数据列表，每个元素是一个股票子列表
        initial_capital: 初始资金
        fitness_weights: 适应度权重 (return, drawdown, sharpe)
        return_capital_curve: 是否返回资金曲线
        max_drawdown_threshold: 最大回撤阈值
        
    返回:
        如果 return_capital_curve=True: (avg_fitness, avg_return, avg_drawdown, avg_sharpe, capital_curves)
        否则: (avg_fitness, avg_return, avg_drawdown, avg_sharpe)
    """
    # 收集所有子列表的结果
    all_fitnesses = []
    all_returns = []
    all_drawdowns = []
    all_sharpes = []
    all_capital_curves = []
    
    # 对每个子列表进行评估
    for i, stock_sublist in enumerate(stock_lists):
        # logger.info(f"Evaluating sublist {i+1}/{len(stock_lists)} and {len(stock_sublist)} stocks")
        if return_capital_curve:
            fitness, total_return, max_drawdown, sharpe_ratio, capital_curve = evaluate_strategy_on_single_list(
                individual, stock_sublist, initial_capital, fitness_weights, max_drawdown_threshold
            )
            all_capital_curves.append(capital_curve)
        else:
            fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
                individual, stock_sublist, initial_capital, fitness_weights, max_drawdown_threshold
            )
        
        all_fitnesses.append(fitness)
        all_returns.append(total_return)
        all_drawdowns.append(max_drawdown)
        all_sharpes.append(sharpe_ratio)
    
    # 计算平均值
    avg_fitness = np.mean(all_fitnesses)
    avg_return = np.mean(all_returns)
    avg_drawdown = np.mean(all_drawdowns)
    avg_sharpe = np.mean(all_sharpes)
    
    # 记录评估结果
    logger.info(f"Evaluated individual with max_drawdown_threshold={max_drawdown_threshold}: "
                 f"avg_fitness={avg_fitness:.4f}, avg_return={avg_return:.2%}, "
                 f"avg_drawdown={avg_drawdown:.2%}, avg_sharpe={avg_sharpe:.2f}")
    
    if return_capital_curve:
        return avg_fitness, avg_return, avg_drawdown, avg_sharpe, all_capital_curves
    else:
        return avg_fitness, avg_return, avg_drawdown, avg_sharpe

def evaluate(individual, stock_lists, fitness_weights, max_drawdown_threshold=0.25):
    """适应度评估函数"""
    fitness, _, _, _ = evaluate_strategy(individual, stock_lists, fitness_weights=fitness_weights, 
                                       max_drawdown_threshold=max_drawdown_threshold)
    return (fitness,)

def evaluate_strategy_global(individual, initial_capital=200000, fitness_weights=(0.4, 0.3, 0.3), 
                           max_drawdown_threshold=0.25):
    """使用共享数据评估策略"""
    try:
        global global_shared_data
        stock_lists = global_shared_data.stock_lists
        
        # logger.info(f"Evaluating individual with {len(stock_lists)} sublists")
        
        all_fitnesses = []
        all_returns = []
        all_drawdowns = []
        all_sharpes = []
        
        for i, stock_sublist in enumerate(stock_lists):
            # logger.info(f"Evaluating sublist {i+1}/{len(stock_lists)}")
            fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
                individual, stock_sublist, initial_capital, fitness_weights, max_drawdown_threshold
            )
            all_fitnesses.append(fitness)
            all_returns.append(total_return)
            all_drawdowns.append(max_drawdown)
            all_sharpes.append(sharpe_ratio)
        
        avg_fitness = np.mean(all_fitnesses)
        # logger.info(f"Individual evaluation completed. Average fitness: {avg_fitness:.4f}")
        return (avg_fitness,)
        
    except Exception as e:
        logger.error(f"Error in evaluate_strategy_global: {str(e)}")
        logger.error(traceback.format_exc())
        return (0.0,)


def mutGaussianAdaptive(individual, mu, sigma, indpb):
    """
    自适应高斯变异
    根据参数范围调整变异幅度，使变异更智能
    """
    size = len(individual)
    for i in range(size):
        if random.random() < indpb:
            # 获取当前参数的取值范围
            param_name = OPTIMIZABLE_PARAMS[i]
            min_val, max_val, param_type = PARAM_RANGES[param_name]
            range_size = max_val - min_val
            
            # 根据参数类型调整变异幅度
            if param_type == int:
                # 整数参数：使用整数变异
                adjusted_sigma = max(1, sigma * range_size / 5)  # 确保至少变异1个单位
                individual[i] += int(round(random.gauss(mu, adjusted_sigma)))
            elif param_type == bool:
                # 布尔参数：直接翻转
                individual[i] = 1 - individual[i]
            else:
                # 浮点数参数：使用连续变异
                adjusted_sigma = sigma * range_size
                individual[i] += random.gauss(mu, adjusted_sigma)
            
            # 确保在范围内
            individual[i] = max(min_val, min(individual[i], max_val))
    return (individual,)

def mutUniformInt(individual, indpb):
    """
    均匀整数变异 - 对于整数参数更有效
    """
    size = len(individual)
    for i in range(size):
        if random.random() < indpb:
            param_name = OPTIMIZABLE_PARAMS[i]
            min_val, max_val, param_type = PARAM_RANGES[param_name]
            
            if param_type == int:
                # 对于整数参数，直接随机选择新值
                individual[i] = random.randint(min_val, max_val)
            elif param_type == bool:
                # 布尔参数：直接翻转
                individual[i] = 1 - individual[i]
            else:
                # 浮点数参数：使用均匀变异
                individual[i] = random.uniform(min_val, max_val)
    
    return (individual,)


def cxBlendAdaptive(ind1, ind2, alpha):
    """
    自适应混合交叉
    根据参数类型调整交叉方式
    """
    size = min(len(ind1), len(ind2))
    for i in range(size):
        param_name = OPTIMIZABLE_PARAMS[i]
        _, _, param_type = PARAM_RANGES[param_name]
        
        if param_type == bool:
            # 布尔参数：使用均匀交叉
            if random.random() < 0.5:
                ind1[i], ind2[i] = ind2[i], ind1[i]
        else:
            # 数值参数：使用混合交叉
            gamma = (1. + 2. * alpha) * random.random() - alpha
            ind1[i] = (1. - gamma) * ind1[i] + gamma * ind2[i]
            ind2[i] = gamma * ind1[i] + (1. - gamma) * ind2[i]
    
    return ind1, ind2


def diversity(population):
    """
    计算种群多样性（基于参数空间的欧几里得距离）
    """
    if len(population) <= 1:
        return 0
    
    # 只处理列表类型的个体
    valid_individuals = [ind for ind in population if isinstance(ind, list)]
    invalid_individuals = [ind for ind in population if not isinstance(ind, list)]
    
    # 记录无效个体的数量和类型
    # if invalid_individuals:
        # logger.warning(f"Found {len(invalid_individuals)} invalid individuals in population. Types: {[type(ind) for ind in invalid_individuals]}")
    
    if len(valid_individuals) <= 1:
        return 0
    
    # 归一化参数值
    normalized_pop = []
    for ind in valid_individuals:
        normalized_ind = []
        for i, param in enumerate(OPTIMIZABLE_PARAMS):
            min_val, max_val, _ = PARAM_RANGES[param]
            # 确保值在合理范围内
            value = ind[i]
            if value < min_val or value > max_val:
                value = np.clip(value, min_val, max_val)
            # 归一化到[0,1]范围
            normalized_val = (value - min_val) / (max_val - min_val)
            normalized_ind.append(normalized_val)
        normalized_pop.append(normalized_ind)
    
    # 计算所有个体间的平均距离
    total_distance = 0
    count = 0
    for i in range(len(normalized_pop)):
        for j in range(i+1, len(normalized_pop)):
            dist = np.linalg.norm(np.array(normalized_pop[i]) - np.array(normalized_pop[j]))
            total_distance += dist
            count += 1
    
    return total_distance / count if count > 0 else 0


def create_adaptive_mutate(diversity_threshold=0.1):
    """
    创建自适应变异函数的工厂函数，根据多样性选择变异策略
    """
    def adaptive_mutate(individual):
        # 获取当前多样性（可能需要通过全局变量或其他方式传递）
        # 这里假设有一个全局变量 current_diversity 存储当前多样性
        
        if random.random() < 0.5:
            return mutGaussianAdaptive(individual, mu=0, sigma=0.05, indpb=0.3)
        else:
            return mutUniformInt(individual, indpb=0.3)
    return adaptive_mutate

def check_bounds(individual):
    """检查并修正个体参数边界"""
    for i, param in enumerate(OPTIMIZABLE_PARAMS):
        min_val, max_val, _ = PARAM_RANGES[param]
        if individual[i] < min_val or individual[i] > max_val:
            individual[i] = np.clip(individual[i], min_val, max_val)
    return individual


def check_bounds_decorator(func):
    """装饰器函数，确保遗传操作后的个体参数在合理范围内"""
    def wrapper(*args, **kwargs):
        # 调用原始函数
        result = func(*args, **kwargs)
        
        # 处理返回结果（可能是一个或多个个体）
        if isinstance(result, tuple):
            # 对于返回多个个体的操作（如交叉）
            for ind in result:
                for i, param in enumerate(OPTIMIZABLE_PARAMS):
                    min_val, max_val, _ = PARAM_RANGES[param]
                    if ind[i] < min_val or ind[i] > max_val:
                        ind[i] = np.clip(ind[i], min_val, max_val)
            return result
        else:
            # 对于返回单个个体的操作（如变异）
            for i, param in enumerate(OPTIMIZABLE_PARAMS):
                min_val, max_val, _ = PARAM_RANGES[param]
                if result[i] < min_val or result[i] > max_val:
                    result[i] = np.clip(result[i], min_val, max_val)
            return result
    
    return wrapper



def adaptive_cx_mutate(population, toolbox, cxpb, mutpb, diversity_score):
    """根据种群多样性自适应调整交叉和变异概率"""
    # 多样性低时增加变异概率
    if diversity_score < 0.1:
        mutpb = min(0.8, mutpb * 1.5)
        cxpb = max(0.2, cxpb * 0.8)
    # 多样性高时增加交叉概率
    elif diversity_score > 0.5:
        cxpb = min(0.9, cxpb * 1.2)
        mutpb = max(0.1, mutpb * 0.8)
    
    # 应用交叉和变异
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
    
    # 应用变异
    for mutant in offspring:
        if random.random() < mutpb:
            toolbox.mutate(mutant)
            del mutant.fitness.values
    
    return offspring

def setup_genetic_algorithm(stock_lists, population_size=50, num_generations=100, 
                           n_processes=None, fitness_weights=(0.2, 0.5, 0.3),  # 调整权重，更注重回撤
                           save_interval=5, early_stopping_patience=25, diversity_threshold=0.05,
                           max_drawdown_threshold=0.25, strategy_name="default"):
    """设置并运行遗传算法（支持并行），添加早停机制"""
    # 创建共享数据对象
    shared_data = SharedData(stock_lists)
    
    # 创建适应度类
    if not hasattr(creator, "FitnessMax"):
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    if not hasattr(creator, "Individual"):
        creator.create("Individual", list, fitness=creator.FitnessMax)
    
    # 初始化工具箱
    toolbox = base.Toolbox()
    toolbox.register("individual", tools.initIterate, creator.Individual, create_individual)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    
    # 注册遗传操作 - 使用自适应混合交叉
    toolbox.register("mate", cxBlendAdaptive, alpha=0.5)
    toolbox.register("select", tools.selTournament, tournsize=3)

    adaptive_mutate_func = create_adaptive_mutate(diversity_threshold=0.1)
    toolbox.register("mutate", adaptive_mutate_func)
    
    # 添加边界检查装饰器
    toolbox.decorate("mate", check_bounds_decorator)
    toolbox.decorate("mutate", check_bounds_decorator)
    
    # 使用部分函数固定参数
    evaluate_with_params = partial(evaluate_strategy_global, initial_capital=200000, 
                                 fitness_weights=fitness_weights, max_drawdown_threshold=max_drawdown_threshold)
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
        
        # 评估初始最佳个体的详细表现
        all_fitnesses = []
        all_returns = []
        all_drawdowns = []
        all_sharpes = []
        
        for stock_sublist in stock_lists:
            fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
                best_individual, stock_sublist, 200000, fitness_weights, max_drawdown_threshold
            )
            all_fitnesses.append(fitness)
            all_returns.append(total_return)
            all_drawdowns.append(max_drawdown)
            all_sharpes.append(sharpe_ratio)
        
        avg_return = np.mean(all_returns)
        avg_drawdown = np.mean(all_drawdowns)
        avg_sharpe = np.mean(all_sharpes)
        
        # 计算初始多样性
        diversity_score = diversity(population)
        
        # 记录初始历史
        history['gen'].append(0)
        history['best_fitness'].append(best_fitness)
        history['best_return'].append(avg_return)
        history['best_drawdown'].append(avg_drawdown)
        history['best_sharpe'].append(avg_sharpe)
        history['avg_fitness'].append(record['avg'])
        history['min_fitness'].append(record['min'])
        history['max_fitness'].append(record['max'])
        history['diversity'].append(diversity_score)
        history['cx_prob'].append(cx_prob)
        history['mut_prob'].append(mut_prob)
        
        # 打印初始代信息
        logger.info(f"\n{'='*80}")
        logger.info(f"Initial Generation Summary (max_drawdown_threshold={max_drawdown_threshold}):")
        logger.info(f"{'='*80}")
        logger.info(f"Best Fitness: {best_fitness:.6f}")
        logger.info(f"Average Return: {avg_return:.2%}")
        logger.info(f"Average Drawdown: {avg_drawdown:.2%}")
        logger.info(f"Average Sharpe Ratio: {avg_sharpe:.4f}")
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
            diversity_score = diversity(population)
            offspring = adaptive_cx_mutate(offspring, toolbox, cx_prob, mut_prob, diversity_score)
            
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
            
            # 评估最佳个体的详细表现
            all_fitnesses = []
            all_returns = []
            all_drawdowns = []
            all_sharpes = []
            
            for stock_sublist in stock_lists:
                fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
                    best_individual, stock_sublist, 200000, fitness_weights, max_drawdown_threshold
                )
                all_fitnesses.append(fitness)
                all_returns.append(total_return)
                all_drawdowns.append(max_drawdown)
                all_sharpes.append(sharpe_ratio)
            
            avg_return = np.mean(all_returns)
            avg_drawdown = np.mean(all_drawdowns)
            avg_sharpe = np.mean(all_sharpes)
            
            # 更新交叉和变异概率
            diversity_score = diversity(population)
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
            history['avg_fitness'].append(record['avg'])
            history['min_fitness'].append(record['min'])
            history['max_fitness'].append(record['max'])
            history['diversity'].append(diversity_score)
            history['cx_prob'].append(cx_prob)
            history['mut_prob'].append(mut_prob)
            
            # 检查早停条件
            # 1. 检查适应度是否不再提升
            if len(best_fitness_history) > 1:
                if abs(best_fitness - max(best_fitness_history[:-1])) < 1e-8:
                    no_improvement_count += 1
                else:
                    no_improvement_count = 0
            
            # 2. 检查多样性是否过低
            if diversity_score < diversity_threshold:
                low_diversity_count += 1
            else:
                low_diversity_count = 0
            
            # 打印当前代信息
            logger.info(f"\n{'='*80}")
            logger.info(f"Generation {gen} Summary (max_drawdown_threshold={max_drawdown_threshold}):")
            logger.info(f"{'='*80}")
            logger.info(f"Best Fitness: {best_fitness:.6f}")
            logger.info(f"Average Return: {avg_return:.2%}")
            logger.info(f"Average Drawdown: {avg_drawdown:.2%}")
            logger.info(f"Average Sharpe Ratio: {avg_sharpe:.4f}")
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
                for i, param in enumerate(OPTIMIZABLE_PARAMS):
                    min_val, max_val, param_type = PARAM_RANGES[param]
                    value = best_individual[i]
                    # 确保值在合理范围内
                    if value < min_val or value > max_val:
                        value = np.clip(value, min_val, max_val)
                    logger.info(f"  {param}: {value:.6f} ({param_type.__name__})")

            logger.info(f"{'='*80}\n")

            # 定期保存结果
            if gen % save_interval == 0 or gen == num_generations:
                best_params = decode_individual(best_individual)
                save_optimization_state(gen, best_individual, best_params, best_fitness, 
                                      avg_return, avg_drawdown, avg_sharpe, stock_lists, 
                                      fitness_weights, max_drawdown_threshold, strategy_name)
            
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
        best_params = decode_individual(best_individual)
        
        # 评估最终最佳个体的表现
        all_fitnesses = []
        all_returns = []
        all_drawdowns = []
        all_sharpes = []
        
        for stock_sublist in stock_lists:
            fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
                best_individual, stock_sublist, 200000, fitness_weights, max_drawdown_threshold
            )
            all_fitnesses.append(fitness)
            all_returns.append(total_return)
            all_drawdowns.append(max_drawdown)
            all_sharpes.append(sharpe_ratio)
        
        avg_return = np.mean(all_returns)
        avg_drawdown = np.mean(all_drawdowns)
        avg_sharpe = np.mean(all_sharpes)
        
        return best_individual, best_params, best_fitness, avg_return, avg_drawdown, avg_sharpe, logbook, history

def save_optimization_state(gen, individual, params, fitness, total_return, 
                           max_drawdown, sharpe_ratio, stock_lists, fitness_weights,
                           max_drawdown_threshold=0.25, strategy_name="default"):

    """保存优化状态 - 添加更多信息"""
    # 创建特定策略和回撤阈值的目录
    results_dir = f"optimization_results_{strategy_name}_{max_drawdown_threshold}"
    capital_dir = f"capital_curves_{strategy_name}_{max_drawdown_threshold}"
    os.makedirs(results_dir, exist_ok=True)
    os.makedirs(capital_dir, exist_ok=True)
    
    # 保存参数
    state = {
        'generation': gen,
        'fitness': fitness,
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'params': params,
        'timestamp': datetime.datetime.now().isoformat(),
        'individual': individual,  # 保存原始个体
        'max_drawdown_threshold': max_drawdown_threshold,
        'strategy_name': strategy_name
    }
    
    # 保存为JSON
    with open(f"{results_dir}/gen_{gen:04d}.json", "w") as f:
        json.dump(state, f, indent=2, default=lambda o: o.tolist() if hasattr(o, 'tolist') else o)
    
    # 保存为Pickle
    with open(f"{results_dir}/gen_{gen:04d}.pkl", "wb") as f:
        pickle.dump(state, f)
    
    # 保存收益曲线图
    if multiprocessing.current_process().name == 'MainProcess':
        _, _, _, _, capital_curves = evaluate_strategy(
            individual, stock_lists, fitness_weights=fitness_weights, 
            return_capital_curve=True, max_drawdown_threshold=max_drawdown_threshold
        )
        # 绘制平均资金曲线
        avg_capital_curve = np.mean([curve for curve in capital_curves if len(curve) > 0], axis=0)
        plot_capital_curve(avg_capital_curve, gen, total_return, max_drawdown, sharpe_ratio, capital_dir, max_drawdown_threshold, strategy_name)
    
    logger.info(f"Saved state for generation {gen} with max_drawdown_threshold={max_drawdown_threshold}: "
                f"Fitness={fitness:.4f}, Return={total_return:.2%}")

def main(stock_lists, population_size=50, num_generations=50, 
        fitness_weights=(0.2, 0.5, 0.3), save_interval=5,  # 调整权重，更注重回撤
        early_stopping_patience=20, diversity_threshold=0.05, strategy_name="default"):
    """主函数：优化参数并显示结果，添加早停参数"""
    logger.info("Starting genetic algorithm optimization...")
    logger.info(f"Strategy name: {strategy_name}")
    logger.info(f"Population size: {population_size}, Generations: {num_generations}")
    logger.info(f"Fitness weights: Return={fitness_weights[0]}, Drawdown={fitness_weights[1]}, Sharpe={fitness_weights[2]}")
    logger.info(f"Save interval: Every {save_interval} generations")
    logger.info(f"Early stopping patience: {early_stopping_patience} generations")
    logger.info(f"Diversity threshold: {diversity_threshold}")
    logger.info(f"Number of stock sublists: {len(stock_lists)}")
    logger.info(f"Number of stocks in first sublist: {len(stock_lists[0])}")
    
    # 检查股票数据
    for i, stock in enumerate(stock_lists[0][:3]):  # 只检查前3个股票
        logger.info(f"Stock {i+1}: {stock['stock_code']}")
        logger.info(f"  Trade price: {stock['trade_price']}")
        logger.info(f"  date: {stock['datekey']}")
    
    # 同时运行两个不同回撤阈值的优化
    results = {}
    for max_drawdown_threshold in [0.25, 0.15]:
        logger.info(f"\n{'#'*80}")
        logger.info(f"Starting optimization with max_drawdown_threshold={max_drawdown_threshold}")
        logger.info(f"{'#'*80}")
        
        # 运行遗传算法优化
        try:
            (best_individual, best_params, best_fitness, 
             best_return, best_drawdown, sharpe_ratio, logbook, history) = setup_genetic_algorithm(
                stock_lists,
                population_size=population_size,
                num_generations=num_generations,
                fitness_weights=fitness_weights,
                save_interval=save_interval,
                early_stopping_patience=early_stopping_patience,
                diversity_threshold=diversity_threshold,
                max_drawdown_threshold=max_drawdown_threshold,
                strategy_name=strategy_name
            )
            
            # 存储结果
            results[max_drawdown_threshold] = {
                'best_individual': best_individual,
                'best_params': best_params,
                'best_fitness': best_fitness,
                'best_return': best_return,
                'best_drawdown': best_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'logbook': logbook,
                'history': history
            }
            
            # 打印优化结果
            logger.info(f"\nOptimization completed for max_drawdown_threshold={max_drawdown_threshold}!")
            logger.info(f"Best fitness: {best_fitness:.4f}")
            logger.info(f"Total return: {best_return:.2%}")
            logger.info(f"Max drawdown: {best_drawdown:.2%}")
            logger.info(f"Sharpe ratio: {sharpe_ratio:.4f}")
            logger.info("\nOptimized parameters:")
            for param, value in best_params.items():
                param_type = PARAM_RANGES.get(param, (0, 0, float))[2].__name__
                logger.info(f"{param}: {value} ({param_type})")
            
            # 保存最佳参数
            results_dir = f"optimization_results_{strategy_name}_{max_drawdown_threshold}"
            with open(f"{results_dir}/best_params.pkl", "wb") as f:
                pickle.dump({
                    'params': best_params,
                    'fitness': best_fitness,
                    'return': best_return,
                    'drawdown': best_drawdown,
                    'sharpe': sharpe_ratio,
                    'individual': best_individual,
                    'max_drawdown_threshold': max_drawdown_threshold,
                    'strategy_name': strategy_name
                }, f)
            
            with open(f"{results_dir}/best_params.json", "w") as f:
                json.dump({
                    'params': best_params,
                    'fitness': best_fitness,
                    'return': best_return,
                    'drawdown': best_drawdown,
                    'sharpe': sharpe_ratio,
                    'individual': best_individual.tolist() if hasattr(best_individual, 'tolist') else list(best_individual),
                    'max_drawdown_threshold': max_drawdown_threshold,
                    'strategy_name': strategy_name
                }, f, indent=2)
            
            # 保存完整历史记录
            with open(f"{results_dir}/optimization_history.pkl", "wb") as f:
                pickle.dump(history, f)
            
            # 保存历史为JSON
            with open(f"{results_dir}/optimization_history.json", "w") as f:
                json.dump(history, f, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o), indent=2)
            
            logger.info(f"Best parameters saved to {results_dir}/")
            
            # 生成详细报告
            generate_final_report(best_params, best_fitness, best_return, best_drawdown, sharpe_ratio, history, max_drawdown_threshold, strategy_name)
            
            # 绘制结果
            plot_optimization_results(logbook, best_params, best_return, best_drawdown, sharpe_ratio, max_drawdown_threshold, strategy_name)
            plot_optimization_history(history, max_drawdown_threshold, strategy_name)
            
        except Exception as e:
            logger.error(f"Error in main optimization for max_drawdown_threshold={max_drawdown_threshold}: {str(e)}")
            logger.error(traceback.format_exc())
    
    return results

def generate_final_report(params, fitness, total_return, max_drawdown, sharpe_ratio, history, max_drawdown_threshold=0.25, strategy_name="default"):
    """生成最终优化报告"""
    # 创建特定策略和回撤阈值的目录
    results_dir = f"optimization_results_{strategy_name}_{max_drawdown_threshold}"
    
    report = {
        "optimization_date": datetime.datetime.now().isoformat(),
        "strategy_name": strategy_name,
        "total_generations": len(history['gen']),
        "best_fitness": fitness,
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "max_drawdown_threshold": max_drawdown_threshold,
        "optimized_parameters": params,
        "optimization_history": {
            "generations": history['gen'],
            "best_fitness": history['best_fitness'],
            "best_return": history['best_return'],
            "best_drawdown": history['best_drawdown'],
            "best_sharpe": history['best_sharpe'],
            "avg_fitness": history['avg_fitness'],
            "min_fitness": history['min_fitness'],
            'max_fitness': history['max_fitness'],
            'diversity': history['diversity']
        }
    }
    
    # 保存报告
    with open(f"{results_dir}/final_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    # 文本格式报告
    with open(f"{results_dir}/final_report.txt", "w") as f:
        f.write("="*80 + "\n")
        f.write("STOCK MONITORING STRATEGY OPTIMIZATION REPORT\n")
        f.write("="*80 + "\n\n")
        f.write(f"Strategy Name: {strategy_name}\n")
        f.write(f"Optimization Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Max Drawdown Threshold: {max_drawdown_threshold}\n")
        f.write(f"Total Generations: {len(history['gen'])}\n")
        f.write(f"Best Fitness: {fitness:.6f}\n")
        f.write(f"Total Return: {total_return:.2%}\n")
        f.write(f"Max Drawdown: {max_drawdown:.2%}\n")
        f.write(f"Sharpe Ratio: {sharpe_ratio:.4f}\n\n")
        
        f.write("Optimized Parameters:\n")
        f.write("-"*80 + "\n")
        for param, value in params.items():
            param_type = PARAM_RANGES.get(param, (0, 0, float))[2].__name__
            f.write(f"{param.ljust(35)}: {value:.6f} ({param_type})\n")
        
        f.write("\nOptimization Summary:\n")
        f.write("-"*80 + "\n")
        best_gen = np.argmax(history['best_fitness'])
        f.write(f"Best generation: {best_gen}\n")
        f.write(f"Best fitness in generation {best_gen}: {history['best_fitness'][best_gen]:.6f}\n")
        f.write(f"Max fitness improvement: {max(history['best_fitness']) - min(history['best_fitness']):.6f}\n")
        f.write(f"Average population fitness: {np.mean(history['avg_fitness']):.6f}\n")
        
        logger.info(f"Final report generated for max_drawdown_threshold={max_drawdown_threshold}")

def plot_capital_curve(capital_curve, gen, total_return, max_drawdown, sharpe_ratio, capital_dir="capital_curves", max_drawdown_threshold=0.25, strategy_name="default"):
    """绘制并保存资金曲线图"""
    plt.figure(figsize=(12, 6))
    
    # 绘制资金曲线
    plt.plot(capital_curve, 'b-', linewidth=2)
    plt.xlabel("Trade")
    plt.ylabel("Capital")
    plt.title(f"Average Capital Curve (Gen {gen}, Strategy: {strategy_name}, Max Drawdown Threshold={max_drawdown_threshold})\n"
              f"Return: {total_return:.2%} | Drawdown: {max_drawdown:.2%} | Sharpe: {sharpe_ratio:.2f}")
    plt.grid(True)
    
    # 标记最高点和最低点
    peak_idx = np.argmax(capital_curve)
    trough_idx = np.argmin(capital_curve[peak_idx:]) + peak_idx
    
    plt.plot(peak_idx, capital_curve[peak_idx], 'ro', markersize=8, label="Peak")
    plt.plot(trough_idx, capital_curve[trough_idx], 'go', markersize=8, label="Trough")
    
    # 添加回撤区域
    capital_array = np.array(capital_curve)
    peak = np.maximum.accumulate(capital_array)
    plt.fill_between(range(len(capital_array)), 
                     capital_array, 
                     peak, 
                     color='red', alpha=0.1)
    
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{capital_dir}/capital_gen_{gen:04d}.png", dpi=150)
    plt.close()

def plot_optimization_history(history, max_drawdown_threshold=0.25, strategy_name="default"):
    """绘制优化历史指标"""
    # 创建特定策略和回撤阈值的目录
    results_dir = f"optimization_results_{strategy_name}_{max_drawdown_threshold}"
    
    plt.figure(figsize=(14, 10))
    
    # 1. 适应度变化
    plt.subplot(2, 2, 1)
    plt.plot(history['gen'], history['best_fitness'], 'b-o')
    plt.xlabel("Generation")
    plt.ylabel("Fitness")
    plt.title(f"Best Fitness Evolution (Strategy: {strategy_name}, Max Drawdown Threshold={max_drawdown_threshold})")
    plt.grid(True)
    
    # 2. 总收益变化
    plt.subplot(2, 2, 2)
    plt.plot(history['gen'], [r * 100 for r in history['best_return']], 'g-o')
    plt.xlabel("Generation")
    plt.ylabel("Total Return (%)")
    plt.title(f"Total Return Evolution (Strategy: {strategy_name}, Max Drawdown Threshold={max_drawdown_threshold})")
    plt.grid(True)
    
    # 3. 最大回撤变化
    plt.subplot(2, 2, 3)
    plt.plot(history['gen'], [d * 100 for d in history['best_drawdown']], 'r-o')
    plt.xlabel("Generation")
    plt.ylabel("Max Drawdown (%)")
    plt.title(f"Max Drawdown Evolution (Strategy: {strategy_name}, Max Drawdown Threshold={max_drawdown_threshold})")
    plt.grid(True)
    
    # 4. 夏普比率变化
    plt.subplot(2, 2, 4)
    plt.plot(history['gen'], history['best_sharpe'], 'm-o')
    plt.xlabel("Generation")
    plt.ylabel("Sharpe Ratio")
    plt.title(f"Sharpe Ratio Evolution (Strategy: {strategy_name}, Max Drawdown Threshold={max_drawdown_threshold})")
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig(f"{results_dir}/optimization_metrics_evolution.png", dpi=200)
    plt.show()

def plot_optimization_results(logbook, best_params, best_return, best_drawdown, sharpe_ratio, max_drawdown_threshold=0.25, strategy_name="default"):
    """绘制优化结果"""
    # 创建特定策略和回撤阈值的目录
    results_dir = f"optimization_results_{strategy_name}_{max_drawdown_threshold}"
    
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
    plt.title(f"Evolution of Fitness (Strategy: {strategy_name}, Max Drawdown Threshold={max_drawdown_threshold})")
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
    plt.title(f"Optimized Parameters (Strategy: {strategy_name}, Max Drawdown Threshold={max_drawdown_threshold})")
    
    # 3. 添加参数值文本
    plt.subplot(3, 1, 3)
    plt.axis('off')
    param_text = "\n".join([f"{param}: {value:.6f}" for param, value in best_params.items()])
    plt.text(0.1, 0.5, 
             f"Optimized Strategy Parameters (Strategy: {strategy_name}, Max Drawdown Threshold={max_drawdown_threshold}):\n\n{param_text}\n\n"
             f"Total Return: {best_return:.2%}\n"
             f"Max Drawdown: {best_drawdown:.2%}\n"
             f"Sharpe Ratio: {sharpe_ratio:.4f}",
             fontsize=12, 
             bbox=dict(facecolor='lightyellow', alpha=0.5))
    
    # 添加整体标题
    plt.suptitle(
        f"Optimized Stock Monitoring Strategy\n"
        f"Strategy: {strategy_name}\n"
        f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        fontsize=16
    )
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(f"{results_dir}/final_optimization_results.png", dpi=300)
    plt.show()

def generate_sample_stock_data(n_days=100, n_stocks_per_day=3):
    """生成示例股票数据"""
    stock_list = []
    
    for day in range(n_days):
        for i in range(n_stocks_per_day):
            stock_code = f"{600000 + day * n_stocks_per_day + i}"
            stock_name = f"Stock-{stock_code}"
            
            # 生成随机价格
            base_price = random.uniform(10, 100)
            open_price = base_price * random.uniform(0.95, 1.05)
            close_price = open_price * random.uniform(0.95, 1.05)
            high_price = max(open_price, close_price) * random.uniform(1.0, 1.08)
            low_price = min(open_price, close_price) * random.uniform(0.92, 1.0)
            
            stock_infos = {
                'strategy_name': 'momentum',
                'order_price': base_price,
                'trade_price': open_price,
                'open_price': open_price,
                'close_price': close_price,
                'high_price': high_price,
                'low_price': low_price,
                'origin_trade_price': base_price,
                'limit_up_price': close_price * 1.1,
                'limit_down_price': close_price * 0.9,
                'row_id': day * n_stocks_per_day + i,
                'monitor_type': 1,
                'tick_datas': [
                    {'price': open_price + j * (close_price - open_price) / 10} 
                    for j in range(10)
                ]
            }
            
            mkt_datas = {
                'ma5': np.mean([open_price, close_price, high_price, low_price, base_price]),
                'ma10': np.mean([open_price, close_price, high_price, low_price, base_price] * 2),
                'ma20': np.mean([open_price, close_price, high_price, low_price, base_price] * 4),
                'ma30': np.mean([open_price, close_price, high_price, low_price, base_price] * 6),
                'ma60': np.mean([open_price, close_price, high_price, low_price, base_price] * 12)
            }
            
            stock_list.append({
                'stock_code': stock_code,
                'stock_name': stock_name,
                'stock_infos': stock_infos,
                'mkt_datas': mkt_datas
            })
    
    return stock_list

if __name__ == "__main__":
    from evaluater_generate_datas_expand_params import build_evaluater_1to2_data_list_from_file

    file_dict = {
        '小高开追涨': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_xgkzz.csv',
        '接力倒接力3': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_dd3.csv',
        '接力倒接力4': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_dd4.csv',
        '接力倒接力5': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_dd5.csv',
        '低位高强低吸': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_dwgqdx.csv',
        '高强中低开低吸前1': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_gqzdkq1.csv',
        '高强中低开低吸前2': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_gqzdkq2.csv',
        '高强中低开低吸2': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_gqzdk2.csv',
        '高位高强追涨': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_gwgqzz.csv',
        '启动低吸': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_qddx.csv',
        '低位断板低吸': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_dwdbdx.csv',
        '中位小低开低吸': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_zwxdkdx.csv',
        '中位中强小低开低吸': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_zwzqxdk.csv',
        '高强中高开追涨': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_gqzgkzz.csv',
        '倒接力3': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_d3.csv',
        '倒接力4': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_d4.csv',
        '倒接力5': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_d5.csv',
        '首红断': r'd:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_shd.csv',
    }

    missing_files = []
    for strategy_name, file_path in file_dict.items():
        if not os.path.exists(file_path):
            missing_files.append((strategy_name, file_path))

    # 如果有缺失的文件，抛出异常
    if missing_files:
        error_message = "以下文件路径不存在:\n"
        for strategy, path in missing_files:
            error_message += f"策略 '{strategy}': {path}\n"
        raise FileNotFoundError(error_message)

    print("所有文件路径均存在！")

    for strategy_name, file_path in file_dict.items():
    
        stock_lists = build_evaluater_1to2_data_list_from_file(200, file_path)
        
        logger.info(f"Generated {len(stock_lists)} stock sublists, each with {len(stock_lists[0])} stocks， strategy_name: {strategy_name}")
        
        results = main(
            stock_lists,
            population_size=300,
            num_generations=300,
            fitness_weights=(0.33, 0.34, 0.33),  # 更注重回撤
            save_interval=10,
            early_stopping_patience=20,  # 20代没有改进就停止
            diversity_threshold=0.05,  # 多样性低于0.05视为过低
            strategy_name=strategy_name  # 添加策略名称参数
        )