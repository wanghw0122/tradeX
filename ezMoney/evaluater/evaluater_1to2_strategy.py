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
# from evaluater.evaluater_generate_datas import build_evaluater_1to2_data_list_from_file

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定义参数范围和类型
PARAM_RANGES = {
    'per_step_tick_gap': (1, 10, int),
    'cold_start_steps': (1, 20, int),
    'max_abserve_tick_steps': (5, 30, int),
    'max_abserce_avg_price_down_steps': (1, 15, int),
    'stop_profit_open_hc_pct': (-0.1, 0.0, float),
    'stop_profit_pct': (0, 0, float),
    'dynamic_hc_stop_profit_thres': (0, 5, float),
    'static_hc_stop_profit_pct': (1, 1, float),
    'last_close_price_hc_pct': (-0.04, 0.0, float),
    'last_day_sell_thres': (0.01, 1.0, float),
    'last_day_sell_huiche': (0.001, 0.02, float)
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
    'last_day_sell_huiche'
]

# 无风险年化收益率 (0%)
RISK_FREE_RATE = 0
DAILY_RISK_FREE_RATE = RISK_FREE_RATE / 252

# 创建输出目录
os.makedirs("optimization_results", exist_ok=True)
os.makedirs("capital_curves", exist_ok=True)

def create_individual():
    """创建个体（一组参数）"""
    individual = []
    for param in OPTIMIZABLE_PARAMS:
        min_val, max_val, param_type = PARAM_RANGES[param]
        
        # 根据参数类型生成不同的随机值
        if param_type == int:
            # 整数参数：生成整数
            individual.append(random.randint(min_val, max_val))
        elif param_type == bool:
            # 布尔参数：生成0或1
            individual.append(random.randint(0, 1))
        else:
            # 浮点数参数：生成浮点数
            individual.append(random.uniform(min_val, max_val))
    
    return individual

def decode_individual(individual):
    """将遗传算法中的个体解码为参数字典 - 添加验证和类型转换"""
    params = {}
    for i, param in enumerate(OPTIMIZABLE_PARAMS):
        min_val, max_val, param_type = PARAM_RANGES[param]
        value = individual[i]
        
        # 确保值在合理范围内
        if value < min_val or value > max_val:
            logger.warning(f"Parameter {param} value {value} out of range [{min_val}, {max_val}]. Clamping.")
            value = np.clip(value, min_val, max_val)
        
        # 根据参数类型进行转换
        if param_type == int:
            value = int(round(value))
        elif param_type == bool:
            value = bool(round(value))
        else:
            value = float(value)
        
        # 特殊处理：max_abserve_tick_steps 需要乘以10
        if param == 'max_abserve_tick_steps':
            value *= 10
        
        params[param] = value
    
    # 添加固定参数
    params['stop_profit_pct'] = 0.0
    params['static_hc_stop_profit_pct'] = 1.0
    
    return params
    
    # 添加固定参数
    params['stop_profit_pct'] = 0.0
    params['static_hc_stop_profit_pct'] = 1.0
    
    return params

def evaluate_strategy_on_single_list(individual, stock_sublist, initial_capital=200000, 
                                    fitness_weights=(0.4, 0.3, 0.3)):
    """
    评估策略在单个股票子列表上的表现
    
    参数:
        individual: 个体参数
        stock_sublist: 股票数据子列表
        initial_capital: 初始资金
        
    返回:
        fitness, total_return, max_drawdown, sharpe_ratio, capital_curve
    """
    try:
        params = decode_individual(individual)
        capital = initial_capital
        capital_curve = [capital]  # 记录每日结束后的资金
        daily_returns = []  # 记录每日收益率
        
        for stock_data in stock_sublist:
            # 解包股票数据
            stock_code = stock_data['stock_code']
            stock_name = stock_data['stock_name']
            stock_infos = stock_data['stock_infos']
            mkt_datas = stock_data['mkt_datas']
            
            # 确保参数在stock_infos中
            if 'params' in stock_infos:
                stock_infos['params'].update(params)
            else:
                stock_infos['params'] = params
            
            # 运行监控策略
            monitor = StockMonitor(
                stock_code=stock_code,
                stock_name=stock_name,
                stock_infos=stock_infos,
                mkt_datas=mkt_datas,
                params=stock_infos['params']
            )
            
            # 获取结果
            sold, sell_price = monitor.get_result()
            
            # 获取交易价格和收盘价
            trade_price = stock_infos['trade_price']
            close_price = stock_infos['close_price']

            
            # 计算实际卖出价格
            actual_sell_price = sell_price if sold else close_price
            if actual_sell_price <= 0:
                actual_sell_price = close_price  # 确保价格有效
            
            # 计算本次交易的收益（使用全部可用资金）
            # 确保不会购买0股
            if trade_price > 0:
                shares = (capital / trade_price // 100) * 100
                profit = shares * (actual_sell_price - trade_price)
                capital += profit
            else:
                logger.warning(f"Invalid trade price: {trade_price} for {stock_code}")
            
            # 记录当日结束资金
            capital_curve.append(capital)
            
            # 计算当日收益率
            if len(capital_curve) >= 2 and capital_curve[-2] > 0:  # 避免除以零
                daily_return = (capital_curve[-1] - capital_curve[-2]) / capital_curve[-2]
                daily_returns.append(daily_return)
        
        # 计算总收益率
        if initial_capital > 0:
            total_return = (capital - initial_capital) / initial_capital
        else:
            total_return = 0
        
        # 计算最大回撤 - 使用向量化方法提高效率
        if len(capital_curve) > 1:
            capital_array = np.array(capital_curve)
            peak = np.maximum.accumulate(capital_array)
            drawdowns = (peak - capital_array) / peak
            max_drawdown = np.max(drawdowns)
        else:
            max_drawdown = 0
        
        # 计算夏普比率（使用日收益）
        returns_array = np.array(daily_returns)
        if len(returns_array) > 1:
            excess_returns = returns_array - DAILY_RISK_FREE_RATE
            sharpe_ratio = np.mean(excess_returns) / (np.std(excess_returns) + 1e-8) * np.sqrt(252)
        else:
            sharpe_ratio = 0

        # 分解适应度权重
        w_return, w_drawdown, w_sharpe = fitness_weights
        
        # 计算适应度 - 使用加权几何平均
        return_component = max(1e-8, 1 + total_return)
        drawdown_component = max(1e-8, 1 - max_drawdown)
        sharpe_component = max(1e-8, sharpe_ratio)
        
        # 使用固定的权重
        fitness = (return_component ** w_return) * (drawdown_component ** w_drawdown) * (sharpe_component ** w_sharpe)
        
        return fitness, total_return, max_drawdown, sharpe_ratio, capital_curve
        
    except Exception as e:
        logger.error(f"Error evaluating strategy on single list: {str(e)}")
        # 返回极低的适应度值
        return 1e-8, -0.9, 0.9, 0, [initial_capital]

def evaluate_strategy(individual, stock_lists, initial_capital=200000, 
                      fitness_weights=(0.4, 0.3, 0.3), return_capital_curve=False):
    """
    评估策略在多个股票列表上的平均表现
    
    参数:
        individual: 个体参数
        stock_lists: 二维股票数据列表，每个元素是一个股票子列表
        initial_capital: 初始资金
        fitness_weights: 适应度权重 (return, drawdown, sharpe)
        return_capital_curve: 是否返回资金曲线
        
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
        logger.debug(f"Evaluating sublist {i+1}/{len(stock_lists)}")
        
        if return_capital_curve:
            fitness, total_return, max_drawdown, sharpe_ratio, capital_curve = evaluate_strategy_on_single_list(
                individual, stock_sublist, initial_capital, fitness_weights
            )
            all_capital_curves.append(capital_curve)
        else:
            fitness, total_return, max_drawdown, sharpe_ratio, _ = evaluate_strategy_on_single_list(
                individual, stock_sublist, initial_capital, fitness_weights
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
    logger.debug(f"Evaluated individual: avg_fitness={avg_fitness:.4f}, avg_return={avg_return:.2%}, "
                 f"avg_drawdown={avg_drawdown:.2%}, avg_sharpe={avg_sharpe:.2f}")
    
    if return_capital_curve:
        return avg_fitness, avg_return, avg_drawdown, avg_sharpe, all_capital_curves
    else:
        return avg_fitness, avg_return, avg_drawdown, avg_sharpe

def evaluate(individual, stock_lists, fitness_weights):
    """适应度评估函数"""
    fitness, _, _, _ = evaluate_strategy(individual, stock_lists, fitness_weights=fitness_weights)
    return (fitness,)

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
    
    # 归一化参数值
    normalized_pop = []
    for ind in population:
        normalized_ind = []
        for i, param in enumerate(OPTIMIZABLE_PARAMS):
            min_val, max_val, _ = PARAM_RANGES[param]
            # 归一化到[0,1]范围
            normalized_val = (ind[i] - min_val) / (max_val - min_val)
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

def setup_genetic_algorithm(stock_lists, population_size=50, num_generations=100, 
                           n_processes=None, fitness_weights=(0.4, 0.3, 0.3), 
                           save_interval=5):
    """
    设置并运行遗传算法（支持并行）
    
    参数:
        stock_lists: 二维股票数据列表，每个元素是一个股票子列表
        population_size: 种群大小
        num_generations: 代数
        n_processes: 并行进程数
        fitness_weights: 适应度权重 (return, drawdown, sharpe)
        save_interval: 保存间隔（代）
        
    返回:
        best_individual, best_params, best_fitness, best_return, 
        best_drawdown, sharpe_ratio, logbook, history
    """
    # 创建适应度类
    if not hasattr(creator, "FitnessMax"):
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    if not hasattr(creator, "Individual"):
        creator.create("Individual", list, fitness=creator.FitnessMax)
    
    # 初始化工具箱
    toolbox = base.Toolbox()
    toolbox.register("individual", tools.initIterate, creator.Individual, create_individual)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    
    # 注册遗传操作 - 使用自适应交叉和多种变异
    toolbox.register("mate", cxBlendAdaptive, alpha=0.5)
    
    # 注册多种变异算子
    toolbox.register("mutate_gaussian", mutGaussianAdaptive, mu=0, sigma=0.05, indpb=0.3)
    toolbox.register("mutate_uniform", mutUniformInt, indpb=0.3)
    
    # 使用锦标赛选择
    toolbox.register("select", tools.selTournament, tournsize=3)
    
    # 使用部分函数固定参数
    evaluate_with_params = partial(evaluate, stock_lists=stock_lists, fitness_weights=fitness_weights)
    toolbox.register("evaluate", evaluate_with_params)
    
    # 创建种群
    population = toolbox.population(n=population_size)
    
    # 设置并行处理 - 添加进程数限制
    if n_processes is None:
        n_processes = min(multiprocessing.cpu_count(), 8)  # 限制最大进程数
    
    logger.info(f"Using {n_processes} processes for parallel evaluation")
    logger.info(f"Number of stock sublists: {len(stock_lists)}")
    
    pool = multiprocessing.Pool(processes=n_processes)
    toolbox.register("map", pool.map)
    
    # 初始化统计和记录
    stats = tools.Statistics(lambda ind: ind.fitness.values[0])
    stats.register("avg", np.mean)
    stats.register("min", np.min)
    stats.register("max", np.max)
    stats.register("std", np.std)
    stats.register("diversity", lambda pop: diversity(pop))  # 添加多样性统计
    
    logbook = tools.Logbook()
    logbook.header = ["gen", "nevals"] + (stats.fields if stats else [])
    
    # 历史记录 - 添加更多信息
    history = {
        'gen': [],
        'best_fitness': [],
        'best_return': [],
        'best_drawdown': [],
        'best_sharpe': [],
        'best_params': [],
        'avg_fitness': [],
        'min_fitness': [],
        'diversity': []
    }
    
    # 运行遗传算法（带进度条）
    logger.info(f"Starting genetic optimization with {n_processes} processes...")
    logger.info(f"Fitness weights: Return={fitness_weights[0]}, Drawdown={fitness_weights[1]}, Sharpe={fitness_weights[2]}")
    
    pbar = tqdm(total=num_generations, desc="Genetic Optimization")
    
    # 评估初始种群
    fitnesses = list(toolbox.map(toolbox.evaluate, population))
    for ind, fit in zip(population, fitnesses):
        ind.fitness.values = fit
    
    # 记录初始状态
    record = stats.compile(population)
    logbook.record(gen=0, nevals=len(population), **record)
    
    # 保存初始状态
    best_individual = tools.selBest(population, k=1)[0]
    best_fitness = best_individual.fitness.values[0]
    _, best_return, best_drawdown, best_sharpe = evaluate_strategy(
        best_individual, stock_lists, fitness_weights=fitness_weights
    )
    best_params = decode_individual(best_individual)
    
    history['gen'].append(0)
    history['best_fitness'].append(best_fitness)
    history['best_return'].append(best_return)
    history['best_drawdown'].append(best_drawdown)
    history['best_sharpe'].append(best_sharpe)
    history['best_params'].append(best_params)
    history['avg_fitness'].append(record['avg'])
    history['min_fitness'].append(record['min'])
    history['diversity'].append(record['diversity'])
    
    # 保存初始结果
    save_optimization_state(0, best_individual, best_params, best_fitness, 
                           best_return, best_drawdown, best_sharpe, stock_lists)
    
    # 添加精英保留策略 - 保留历史最佳个体
    hof = tools.HallOfFame(1)
    hof.update(population)
    
    # 添加早停机制 - 基于多样性和适应度
    no_improvement_count = 0
    last_best_fitness = best_fitness  # 记录上一代的最佳适应度
    diversity_threshold = 0.1  # 多样性阈值
    
    # 开始进化
    for gen in range(1, num_generations + 1):
        # 动态调整变异策略
        current_diversity = diversity(population)
        
        # 根据多样性选择变异策略
        if current_diversity < diversity_threshold:
            # 多样性低时使用更强的变异
            mutate_func = toolbox.mutate_uniform
            mutation_rate = 0.4  # 提高变异率
            logger.info(f"Low diversity ({current_diversity:.3f}), using uniform mutation")
        else:
            # 多样性高时使用温和的变异
            mutate_func = toolbox.mutate_gaussian
            mutation_rate = 0.2  # 正常变异率
        
        # 生成下一代 - 动态调整交叉和变异概率
        offspring = algorithms.varOr(population, toolbox, lambda_=population_size, 
                                    cxpb=0.7, mutpb=mutation_rate)
        
        # 评估新个体 - 添加超时处理
        fitnesses = []
        start_time = time.time()
        for ind in offspring:
            try:
                # 使用apply_async实现超时控制
                result = pool.apply_async(toolbox.evaluate, (ind,))
                # 设置30分钟超时
                fitness = result.get(timeout=1800)
                fitnesses.append(fitness)
            except multiprocessing.TimeoutError:
                logger.warning(f"Evaluation timed out for individual in generation {gen}")
                # 分配低适应度
                fitnesses.append((0.0,))
            except Exception as e:
                logger.error(f"Evaluation failed: {str(e)}")
                # 分配低适应度
                fitnesses.append((0.0,))
        
        eval_time = time.time() - start_time
        logger.info(f"Generation {gen} evaluation completed in {eval_time:.2f} seconds")
        
        for ind, fit in zip(offspring, fitnesses):
            ind.fitness.values = fit
        
        # 选择下一代 - 加入精英保留
        population = toolbox.select(population + offspring, population_size)
        hof.update(population)
        
        # 定期引入新个体（每10代）以增加多样性
        if gen % 10 == 0:
            logger.info(f"Introducing new individuals at generation {gen}")
            # 替换10%的最差个体
            population.sort(key=lambda x: x.fitness.values[0])
            replace_count = max(1, int(0.1 * len(population)))
            for i in range(replace_count):
                new_ind = toolbox.individual()
                new_ind.fitness.values = toolbox.evaluate(new_ind)
                population[i] = new_ind
        
        # 记录统计信息
        record = stats.compile(population)
        logbook.record(gen=gen, nevals=len(offspring), **record)
        
        # 获取当前最佳个体
        best_individual = hof[0]
        best_fitness = best_individual.fitness.values[0]
        _, best_return, best_drawdown, best_sharpe = evaluate_strategy(
            best_individual, stock_lists, fitness_weights=fitness_weights
        )
        best_params = decode_individual(best_individual)
        
        # 更新历史记录
        history['gen'].append(gen)
        history['best_fitness'].append(best_fitness)
        history['best_return'].append(best_return)
        history['best_drawdown'].append(best_drawdown)
        history['best_sharpe'].append(best_sharpe)
        history['best_params'].append(best_params)
        history['avg_fitness'].append(record['avg'])
        history['min_fitness'].append(record['min'])
        history['diversity'].append(record['diversity'])
        
        # 检查是否有改进（与上一代的最佳适应度比较）
        # 添加1e-5容差，避免浮点精度问题
        fitness_improved = best_fitness > last_best_fitness + 1e-5
        diversity_ok = current_diversity > diversity_threshold / 2
        
        if not fitness_improved:
            no_improvement_count += 1
            logger.info(f"No improvement for {no_improvement_count} generations, diversity: {current_diversity:.3f}")
        else:
            # 有改进，重置计数器
            no_improvement_count = 0
            last_best_fitness = best_fitness
            logger.info(f"New best fitness: {best_fitness:.4f} (improvement)")
        
        # 早停机制：基于适应度和多样性
        # 连续10代无改进且多样性低则停止
        if no_improvement_count >= 10 and not diversity_ok:
            logger.info(f"Early stopping at generation {gen} due to no improvement for 10 generations and low diversity")
            pbar.update(num_generations - gen + 1)  # 更新进度条
            break
        
        # 定期保存结果
        if gen % save_interval == 0 or gen == num_generations:
            save_optimization_state(gen, best_individual, best_params, best_fitness, 
                                   best_return, best_drawdown, best_sharpe, stock_lists)
        
        # 记录当前代统计信息
        logger.info(f"Generation {gen}: best_fitness={best_fitness:.4f}, avg_fitness={record['avg']:.4f}, "
                   f"min_fitness={record['min']:.4f}, diversity={record['diversity']:.3f}, "
                   f"no_improvement={no_improvement_count}")
        
        pbar.update()
    
    pbar.close()
    pool.close()
    pool.join()
    
    # 获取最终最佳个体
    best_individual = hof[0]
    best_fitness = best_individual.fitness.values[0]
    _, best_return, best_drawdown, best_sharpe = evaluate_strategy(
        best_individual, stock_lists, fitness_weights=fitness_weights
    )
    best_params = decode_individual(best_individual)
    
    return best_individual, best_params, best_fitness, best_return, best_drawdown, best_sharpe, logbook, history

def save_optimization_state(gen, individual, params, fitness, total_return, 
                           max_drawdown, sharpe_ratio, stock_lists):
    """保存优化状态 - 添加更多信息"""
    # 保存参数
    state = {
        'generation': gen,
        'fitness': fitness,
        'total_return': total_return,
        'max_drawdown': max_drawdown,
        'sharpe_ratio': sharpe_ratio,
        'params': params,
        'timestamp': datetime.datetime.now().isoformat(),
        'individual': individual  # 保存原始个体
    }
    
    # 保存为JSON
    with open(f"optimization_results/gen_{gen:04d}.json", "w") as f:
        json.dump(state, f, indent=2, default=lambda o: o.tolist() if hasattr(o, 'tolist') else o)
    
    # 保存为Pickle
    with open(f"optimization_results/gen_{gen:04d}.pkl", "wb") as f:
        pickle.dump(state, f)
    
    # 保存收益曲线图
    if multiprocessing.current_process().name == 'MainProcess':
        _, _, _, _, capital_curves = evaluate_strategy(
            individual, stock_lists, return_capital_curve=True
        )
        # 绘制平均资金曲线
        avg_capital_curve = np.mean([curve for curve in capital_curves if len(curve) > 0], axis=0)
        plot_capital_curve(avg_capital_curve, gen, total_return, max_drawdown, sharpe_ratio)
    
    logger.info(f"Saved state for generation {gen}: Fitness={fitness:.4f}, Return={total_return:.2%}")

def main(stock_lists, population_size=50, num_generations=50, 
        fitness_weights=(0.4, 0.3, 0.3), save_interval=5):
    """主函数：优化参数并显示结果"""
    logger.info("Starting genetic algorithm optimization...")
    logger.info(f"Population size: {population_size}, Generations: {num_generations}")
    logger.info(f"Fitness weights: Return={fitness_weights[0]}, Drawdown={fitness_weights[1]}, Sharpe={fitness_weights[2]}")
    logger.info(f"Save interval: Every {save_interval} generations")
    logger.info(f"Number of stock sublists: {len(stock_lists)}")
    
    # 运行遗传算法优化
    (best_individual, best_params, best_fitness, 
     best_return, best_drawdown, sharpe_ratio, logbook, history) = setup_genetic_algorithm(
        stock_lists,
        population_size=population_size,
        num_generations=num_generations,
        fitness_weights=fitness_weights,
        save_interval=save_interval
    )
    
    # 打印优化结果
    logger.info("\nOptimization completed!")
    logger.info(f"Best fitness: {best_fitness:.4f}")
    logger.info(f"Total return: {best_return:.2%}")
    logger.info(f"Max drawdown: {best_drawdown:.2%}")
    logger.info(f"Sharpe ratio: {sharpe_ratio:.4f}")
    logger.info("\nOptimized parameters:")
    for param, value in best_params.items():
        param_type = PARAM_RANGES.get(param, (0, 0, float))[2].__name__
        logger.info(f"{param}: {value} ({param_type})")
    
    # 保存最佳参数
    with open("optimization_results/best_params.pkl", "wb") as f:
        pickle.dump({
            'params': best_params,
            'fitness': best_fitness,
            'return': best_return,
            'drawdown': best_drawdown,
            'sharpe': sharpe_ratio,
            'individual': best_individual
        }, f)
    
    with open("optimization_results/best_params.json", "w") as f:
        json.dump({
            'params': best_params,
            'fitness': best_fitness,
            'return': best_return,
            'drawdown': best_drawdown,
            'sharpe': sharpe_ratio,
            'individual': best_individual.tolist() if hasattr(best_individual, 'tolist') else list(best_individual)
        }, f, indent=2)
    
    # 保存完整历史记录
    with open("optimization_results/optimization_history.pkl", "wb") as f:
        pickle.dump(history, f)
    
    # 保存历史为JSON
    with open("optimization_results/optimization_history.json", "w") as f:
        json.dump(history, f, default=lambda o: o.tolist() if hasattr(o, 'tolist') else str(o), indent=2)
    
    logger.info("Best parameters saved to optimization_results/")
    
    # 生成详细报告
    generate_final_report(best_params, best_fitness, best_return, best_drawdown, sharpe_ratio, history)
    
    # 绘制结果
    plot_optimization_results(logbook, best_params, best_return, best_drawdown, sharpe_ratio)
    plot_optimization_history(history)
    
    return best_params, history

def generate_final_report(params, fitness, total_return, max_drawdown, sharpe_ratio, history):
    """生成最终优化报告"""
    report = {
        "optimization_date": datetime.datetime.now().isoformat(),
        "total_generations": len(history['gen']),
        "best_fitness": fitness,
        "total_return": total_return,
        "max_drawdown": max_drawdown,
        "sharpe_ratio": sharpe_ratio,
        "optimized_parameters": params,
        "optimization_history": {
            "generations": history['gen'],
            "best_fitness": history['best_fitness'],
            "best_return": history['best_return'],
            "best_drawdown": history['best_drawdown'],
            "best_sharpe": history['best_sharpe'],
            "avg_fitness": history['avg_fitness'],
            "min_fitness": history['min_fitness']
        }
    }
    
    # 保存报告
    with open("optimization_results/final_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    # 文本格式报告
    with open("optimization_results/final_report.txt", "w") as f:
        f.write("="*80 + "\n")
        f.write("STOCK MONITORING STRATEGY OPTIMIZATION REPORT\n")
        f.write("="*80 + "\n\n")
        f.write(f"Optimization Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
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
        
        logger.info("Final report generated")

def plot_capital_curve(capital_curve, gen, total_return, max_drawdown, sharpe_ratio):
    """绘制并保存资金曲线图"""
    plt.figure(figsize=(12, 6))
    
    # 绘制资金曲线
    plt.plot(capital_curve, 'b-', linewidth=2)
    plt.xlabel("Trade")
    plt.ylabel("Capital")
    plt.title(f"Average Capital Curve (Gen {gen})\n"
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
    plt.savefig(f"capital_curves/capital_gen_{gen:04d}.png", dpi=150)
    plt.close()

def plot_optimization_history(history):
    """绘制优化历史指标"""
    plt.figure(figsize=(14, 10))
    
    # 1. 适应度变化
    plt.subplot(2, 2, 1)
    plt.plot(history['gen'], history['best_fitness'], 'b-o')
    plt.xlabel("Generation")
    plt.ylabel("Fitness")
    plt.title("Best Fitness Evolution")
    plt.grid(True)
    
    # 2. 总收益变化
    plt.subplot(2, 2, 2)
    plt.plot(history['gen'], [r * 100 for r in history['best_return']], 'g-o')
    plt.xlabel("Generation")
    plt.ylabel("Total Return (%)")
    plt.title("Total Return Evolution")
    plt.grid(True)
    
    # 3. 最大回撤变化
    plt.subplot(2, 2, 3)
    plt.plot(history['gen'], [d * 100 for d in history['best_drawdown']], 'r-o')
    plt.xlabel("Generation")
    plt.ylabel("Max Drawdown (%)")
    plt.title("Max Drawdown Evolution")
    plt.grid(True)
    
    # 4. 夏普比率变化
    plt.subplot(2, 2, 4)
    plt.plot(history['gen'], history['best_sharpe'], 'm-o')
    plt.xlabel("Generation")
    plt.ylabel("Sharpe Ratio")
    plt.title("Sharpe Ratio Evolution")
    plt.grid(True)
    
    plt.tight_layout()
    plt.savefig("optimization_results/optimization_metrics_evolution.png", dpi=200)
    plt.show()

def plot_optimization_results(logbook, best_params, best_return, best_drawdown, sharpe_ratio):
    """绘制优化结果"""
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
    param_text = "\n".join([f"{param}: {value:.6f}" for param, value in best_params.items()])
    plt.text(0.1, 0.5, 
             f"Optimized Strategy Parameters:\n\n{param_text}\n\n"
             f"Total Return: {best_return:.2%}\n"
             f"Max Drawdown: {best_drawdown:.2%}\n"
             f"Sharpe Ratio: {sharpe_ratio:.4f}",
             fontsize=12, 
             bbox=dict(facecolor='lightyellow', alpha=0.5))
    
    # 添加整体标题
    plt.suptitle(
        f"Optimized Stock Monitoring Strategy\n"
        f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        fontsize=16
    )
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig("optimization_results/final_optimization_results.png", dpi=300)
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
    from evaluater_generate_datas import build_evaluater_1to2_data_list_from_file
    
    # 生成示例股票数据（实际应用中应替换为真实数据）
    # 创建二维股票列表：多个股票子列表
    stock_lists = []
    n_sublists = 5  # 5个子列表
    stocks_per_sublist = 10  # 每个子列表10只股票
    
    for i in range(n_sublists):
        stock_sublist = build_evaluater_1to2_data_list_from_file(stocks_per_sublist)
        stock_lists.append(stock_sublist)
    
    logger.info(f"Generated {len(stock_lists)} stock sublists, each with {stocks_per_sublist} stocks")
    
    # 优化参数
    best_params, history = main(
        stock_lists,
        population_size=7,
        num_generations=10,
        fitness_weights=(0.5, 0.3, 0.2),  # 自定义权重
        save_interval=1  # 每代保存一次
    )