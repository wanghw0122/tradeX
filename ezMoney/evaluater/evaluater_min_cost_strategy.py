import sys
sys.path.append(r"D:\workspace\TradeX\ezMoney")

from arrow import get
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from deap import base, creator, tools, algorithms
import random
import os
import json
import logging
import multiprocessing
import traceback
from datetime import datetime
from monitor.min_cost_order_backtest import MinCostOrderMonitor

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 定义参数范围和类型
PARAM_RANGES = {
    'remaining_buy_down_min_pct': (0, 0.02, float),      # 0.1% - 2%
    'max_strategy_down_pct': (1.0, 15.0, float),         # 1% - 10%
    'base_buy_gap_ticks': (10, 200, int),                # 50-500个tick
    'base_buy_down_min_pct': (-0.05, 0.05, float),       # 0.1% - 2%
    'base_buy_times': (5, 15, int),                      # 1-10次
    'base_max_buy_ticks': (10, 2400, int),               # 100-1000个tick
    'max_buy_ticks': (10, 2400, int),                    # 200-2000个tick
    'base_budget_pct': (0, 1, float),                    # 1% - 10%
}

# 需要优化的参数列表
OPTIMIZABLE_PARAMS = list(PARAM_RANGES.keys())

# 固定参数（TripleFilter和SignalDetector的参数）
FIXED_PARAMS = {
    "ema_alpha": 0.11731169217801875,
    "kalman_q": 0.05,
    "kalman_r": 0.032779386595630504,
    "sg_window": 13,
    "macd_fast": 2,
    "macd_slow_ratio": 1.923502368920664,
    "macd_signal": 2,
    "ema_fast": 4,
    "ema_slow_ratio": 2.0120113875614254,
    "volume_window": 10,
    "price_confirm_ticks": 6,
    "strength_confirm_ticks": 7,
    "strength_threshold": 0.3,
    "volume_weight": 0.9841988854678615,
    "use_price_confirm": False,
    "use_strength_confirm": False,
    "dead_cross_threshold": 0.05,
    'price_drop_threshold': 0.008308440100195527,
    'max_confirm_ticks': 20,
    'debug': False
}

# 全局tick数据缓存
tick_data_cache = {}

def get_tick_data_main(stock_code, date_str, func):
    """获取tick数据的函数，带缓存功能"""
    cache_key = f"{stock_code}_{date_str}"
    
    # 检查缓存
    if cache_key in tick_data_cache:
        logger.info(f"Using cached tick data for {cache_key}")
        return tick_data_cache[cache_key]
    
    # 如果没有缓存，则下载数据
    logger.info(f"Downloading tick data for {cache_key}")
    try:
        res = func(stock_code, date_str)
        if res is None:
            logger.error(f"Error getting tick data for {stock_code} on {date_str}")
            return None
        tick_data_cache[cache_key] = res
        return res
    except Exception as e:
        traceback.print_exc()
        logger.error(f"Error getting tick data for {stock_code} on {date_str}: {str(e)}")
        return None

class SharedData:
    """共享数据类，用于多进程间传递数据"""
    def __init__(self, trading_df, tick_data_cache):
        self.trading_df = trading_df
        self.tick_data_cache = tick_data_cache
    
    def __getstate__(self):
        return self.__dict__
    
    def __setstate__(self, state):
        self.__dict__.update(state)

def init_worker(shared_data):
    """初始化工作进程"""
    global global_shared_data
    global_shared_data = shared_data

def get_tick_data_from_cache(stock_code, date_str):
    """从缓存中获取tick数据"""
    global global_shared_data
    cache_key = f"{stock_code}_{date_str}"
    return global_shared_data.tick_data_cache.get(cache_key, None)

def decode_individual(individual):
    """将遗传算法个体解码为参数字典"""
    params = {}
    for i, param in enumerate(OPTIMIZABLE_PARAMS):
        min_val, max_val, param_type = PARAM_RANGES[param]
        value = individual[i]
        
        # 确保值在合理范围内
        if value < min_val or value > max_val:
            value = np.clip(value, min_val, max_val)
        
        # 转换类型
        if param_type == int:
            value = int(round(value))
        
        params[param] = value
    
    return params

def calculate_max_drawdown(cumulative_returns):
    """计算最大回撤"""
    peak = cumulative_returns[0]
    max_drawdown = 0
    drawdown_start = 0
    drawdown_end = 0
    
    for i, value in enumerate(cumulative_returns):
        if value > peak:
            peak = value
        
        drawdown = (peak - value) / peak
        if drawdown > max_drawdown:
            max_drawdown = drawdown
            drawdown_end = i
            
            # 找到回撤开始的点
            for j in range(i, -1, -1):
                if cumulative_returns[j] >= peak:
                    drawdown_start = j
                    break
    
    return max_drawdown, drawdown_start, drawdown_end

def evaluate_individual(individual):
    """评估单个个体的适应度"""
    try:
        # 获取全局共享数据
        global global_shared_data
        trading_df = global_shared_data.trading_df
        
        # 解码参数
        params = decode_individual(individual)
        all_params = {**FIXED_PARAMS, **params}
        base_budget_pct = all_params['base_budget_pct']
        
        # 初始化结果存储
        initial_budget = 200000
        current_budget = initial_budget
        total_return = 0
        daily_results = []
        
        # 记录每日资金变化，用于计算回撤
        daily_budgets = [initial_budget]
        
        # 记录基础预算和剩余预算的收益
        base_budget_returns = []
        remaining_budget_returns = []
        
        # 记录胜率相关数据
        winning_days = 0
        total_trade_days = 0
        
        # 对每个交易日进行处理
        for idx, row in trading_df.iterrows():
            stock_code = row['stock_code']
            trade_date = row['trade_date']  # 已经是字符串格式
            sell_price = row['sell_price']
            strategy_name = row['strategy_name']
            stock_name = row['stock_name']
            
            # 计算当天的预算分配
            day_base_budget = current_budget * base_budget_pct
            day_budget = current_budget - day_base_budget
            
            # 确保预算合理
            day_base_budget = max(0, day_base_budget)
            day_budget = max(0, day_budget)
            
            # 从缓存中获取tick数据
            tick_data = get_tick_data_from_cache(stock_code, trade_date)
            if tick_data is None:
                # 如果没有tick数据，跳过这一天
                logger.error(f"Error getting tick data for {stock_code} on {trade_date}")
                daily_results.append({
                    'date': trade_date,
                    'stock_code': stock_code,
                    'stock_name': stock_name,
                    'strategy_name': strategy_name,
                    'daily_budget': current_budget,
                    'daily_investment': 0,
                    'daily_return': 0,
                    'daily_ratio': 0,
                    'daily_real_return_rate': 0,
                    'daily_budget_return_rate': 0,
                    'has_trade': False,
                    'base_budget_return': 0,
                    'remaining_budget_return': 0,
                    'base_budget': day_base_budget,
                    'remaining_budget': day_budget
                })
                daily_budgets.append(current_budget)
                continue
            
            # 设置参数
            day_params = all_params.copy()
            day_params['base_budget'] = day_base_budget
            day_params['budget'] = day_budget
            
            # 初始化监控器
            monitor = MinCostOrderMonitor(
                stock_code, 
                stock_name, 
                strategy_name, 
                day_params,
                row.get('sub_strategy_str', '')
            )
            
            # 运行回测
            buy_signals = monitor.run_backtest(tick_data)
            
            # 计算该交易的收益
            trade_investment = 0
            trade_return = 0
            base_budget_investment = 0
            base_budget_return = 0
            remaining_budget_investment = 0
            remaining_budget_return = 0
            
            for signal in buy_signals:
                # 计算买入成本
                cost = signal['sell1'] * signal['volume']
                trade_investment += cost
                
                # 计算卖出收益
                revenue = sell_price * signal['volume']
                signal_return = revenue - cost
                trade_return += signal_return
                
                # 区分基础预算和剩余预算的收益
                if signal.get('is_base_buy', False):
                    base_budget_investment += cost
                    base_budget_return += signal_return
                else:
                    remaining_budget_investment += cost
                    remaining_budget_return += signal_return
            
            # 记录交易详情（使用交易前的预算）
            trade_ratio = trade_investment / current_budget if current_budget > 0 else 0
            trade_real_return_rate = trade_return / current_budget if current_budget > 0 else 0
            trade_budget_return_rate = trade_return / trade_investment if trade_investment > 0 else 0
            has_trade = trade_investment > 0
            
            # 计算基础预算和剩余预算的收益率
            base_budget_return_rate = base_budget_return / day_base_budget if day_base_budget > 0 else 0
            remaining_budget_return_rate = remaining_budget_return / day_budget if day_budget > 0 else 0
            
            # 更新胜率统计
            if has_trade:
                total_trade_days += 1
                if trade_return > 0:
                    winning_days += 1

            # 记录每日结果（使用交易前的预算）
            daily_results.append({
                'date': trade_date,
                'stock_code': stock_code,
                'stock_name': stock_name,
                'strategy_name': strategy_name,
                'daily_budget': current_budget,
                'daily_investment': trade_investment,
                'daily_return': trade_return,
                'daily_ratio': trade_ratio,
                'daily_real_return_rate': trade_real_return_rate,
                'daily_budget_return_rate': trade_budget_return_rate,
                'has_trade': has_trade,
                'base_budget_return': base_budget_return,
                'remaining_budget_return': remaining_budget_return,
                'base_budget_return_rate': base_budget_return_rate,
                'remaining_budget_return_rate': remaining_budget_return_rate,
                'base_budget': day_base_budget,
                'remaining_budget': day_budget
            })
            
            # 记录基础预算和剩余预算的收益
            base_budget_returns.append(base_budget_return)
            remaining_budget_returns.append(remaining_budget_return)

            # 更新总预算（在所有计算完成后）
            current_budget += trade_return
            total_return += trade_return
            daily_budgets.append(current_budget)
        
        # 计算最大回撤
        max_drawdown, drawdown_start, drawdown_end = calculate_max_drawdown(daily_budgets)
        
        # 计算胜率
        win_rate = winning_days / total_trade_days if total_trade_days > 0 else 0
        
        # 计算总收益率
        total_return_rate = total_return / initial_budget
        
        # 计算基础预算和剩余预算的总收益率
        base_budget_total_return = sum(base_budget_returns)
        remaining_budget_total_return = sum(remaining_budget_returns)
        base_budget_total_return_rate = base_budget_total_return / initial_budget
        remaining_budget_total_return_rate = remaining_budget_total_return / initial_budget
        
        # 计算统计指标
        trade_days = len([d for d in daily_results if d['has_trade']])
        total_days = len(daily_results)
        trade_day_ratio = trade_days / total_days if total_days > 0 else 0
        
        avg_daily_ratio = np.mean([d['daily_ratio'] for d in daily_results if d['has_trade']]) if trade_days > 0 else 0
        avg_daily_real_return = np.mean([d['daily_real_return_rate'] for d in daily_results if d['has_trade']]) if trade_days > 0 else 0
        avg_daily_budget_return = np.mean([d['daily_budget_return_rate'] for d in daily_results if d['has_trade']]) if trade_days > 0 else 0
        
        logger.info(f"Individual evaluated: fitness={total_return_rate:.6f}, "
                   f"Trade days: {trade_days}/{total_days} ({trade_day_ratio:.2%}), "
                   f"Win rate: {win_rate:.2%}, Max drawdown: {max_drawdown:.2%}")
        
        # 返回适应度和详细结果
        return (total_return_rate, daily_results, {
            'total_return_rate': total_return_rate,
            'trade_days': trade_days,
            'total_days': total_days,
            'trade_day_ratio': trade_day_ratio,
            'win_rate': win_rate,
            'max_drawdown': max_drawdown,
            'drawdown_start': drawdown_start,
            'drawdown_end': drawdown_end,
            'avg_daily_ratio': avg_daily_ratio,
            'avg_daily_real_return': avg_daily_real_return,
            'avg_daily_budget_return': avg_daily_budget_return,
            'final_budget': current_budget,
            'base_budget_total_return_rate': base_budget_total_return_rate,
            'remaining_budget_total_return_rate': remaining_budget_total_return_rate,
            'base_budget_total_return': base_budget_total_return,
            'remaining_budget_total_return': remaining_budget_total_return
        })
    
    except Exception as e:
        logger.error(f"Error evaluating individual: {str(e)}")
        logger.error(traceback.format_exc())
        return (0.0, [], {})

def create_individual():
    """创建个体（一组参数）"""
    individual = []
    for param in OPTIMIZABLE_PARAMS:
        min_val, max_val, param_type = PARAM_RANGES[param]
        
        if param_type == int:
            individual.append(random.randint(min_val, max_val))
        else:
            individual.append(random.uniform(min_val, max_val))
    
    return individual

def mutGaussian(individual, mu, sigma, indpb):
    """高斯变异操作"""
    size = len(individual)
    for i in range(size):
        if random.random() < indpb:
            # 获取当前参数的取值范围
            param_name = OPTIMIZABLE_PARAMS[i]
            min_val, max_val, param_type = PARAM_RANGES[param_name]
            
            # 应用高斯变异
            individual[i] += random.gauss(mu, sigma)
            
            # 确保在范围内
            individual[i] = max(min_val, min(individual[i], max_val))
            
            # 转换类型
            if param_type == int:
                individual[i] = int(round(individual[i]))
    
    return (individual,)

def setup_genetic_algorithm(trading_df, tick_data_cache, population_size=50, 
                           num_generations=20, n_processes=None, cxpb=0.5, mutpb=0.2):
    """设置并运行遗传算法"""
    # 创建共享数据对象
    shared_data = SharedData(trading_df, tick_data_cache)
    
    # 创建适应度类
    if not hasattr(creator, "FitnessMax"):
        creator.create("FitnessMax", base.Fitness, weights=(1.0,))
    if not hasattr(creator, "Individual"):
        creator.create("Individual", list, fitness=creator.FitnessMax)
    
    # 初始化工具箱
    toolbox = base.Toolbox()
    toolbox.register("individual", tools.initIterate, creator.Individual, create_individual)
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    
    # 注册遗传操作
    toolbox.register("mate", tools.cxBlend, alpha=0.5)
    toolbox.register("mutate", mutGaussian, mu=0, sigma=0.1, indpb=0.2)
    toolbox.register("select", tools.selTournament, tournsize=3)
    
    # 使用部分函数固定参数
    toolbox.register("evaluate", evaluate_individual)
    
    # 创建种群
    population = toolbox.population(n=population_size)
    
    # 设置并行处理
    if n_processes is None:
        n_processes = min(multiprocessing.cpu_count(), 8)
    
    logger.info(f"Using {n_processes} processes for parallel evaluation")
    
    # 创建进程池并初始化
    with multiprocessing.Pool(processes=n_processes, initializer=init_worker, initargs=(shared_data,)) as pool:
        toolbox.register("map", pool.map)
        
        # 评估初始种群
        fitnesses = list(toolbox.map(toolbox.evaluate, population))
        for ind, fit in zip(population, fitnesses):
            ind.fitness.values = (fit[0],)  # 只取适应度值
        
        # 记录最佳个体
        hof = tools.HallOfFame(1)
        hof.update(population)
        
        # 统计记录
        stats = tools.Statistics(lambda ind: ind.fitness.values[0])
        stats.register("avg", np.mean)
        stats.register("min", np.min)
        stats.register("max", np.max)
        
        # 进化循环
        for gen in range(1, num_generations + 1):
            # 选择下一代
            offspring = toolbox.select(population, len(population))
            
            # 克隆选中的个体
            offspring = list(map(toolbox.clone, offspring))
            
            # 应用交叉和变异
            for child1, child2 in zip(offspring[::2], offspring[1::2]):
                if random.random() < cxpb:
                    toolbox.mate(child1, child2)
                    del child1.fitness.values
                    del child2.fitness.values
            
            for mutant in offspring:
                if random.random() < mutpb:
                    toolbox.mutate(mutant)
                    del mutant.fitness.values
            
            # 评估新个体
            invalid_ind = [ind for ind in offspring if not ind.fitness.valid]
            fitnesses = toolbox.map(toolbox.evaluate, invalid_ind)
            for ind, fit in zip(invalid_ind, fitnesses):
                ind.fitness.values = (fit[0],)  # 只取适应度值
            
            # 更新种群
            population[:] = offspring
            
            # 更新名人堂
            hof.update(population)
            
            # 记录统计信息
            record = stats.compile(population)
            logger.info(f"Generation {gen}: {record}")
            
            # 定期保存结果
            if gen % 5 == 0:
                best_individual = hof[0]
                best_params = decode_individual(best_individual)
                
                # 评估最佳个体获取详细结果
                fitness, daily_results, stats_dict = evaluate_individual(best_individual)
                save_optimization_state(gen, best_individual, best_params, 
                                      fitness, daily_results, stats_dict)
        
        # 返回最佳个体
        return hof[0]

def save_optimization_state(gen, individual, params, fitness, daily_results, stats_dict):
    """保存优化状态"""
    # 创建结果目录
    os.makedirs("optimization_results", exist_ok=True)
    
    # 保存参数
    state = {
        'generation': gen,
        'fitness': fitness,
        'params': params,
        'stats': stats_dict,
        'timestamp': datetime.now().isoformat(),
        'individual': individual
    }
    
    # 保存为JSON
    with open(f"optimization_results/gen_{gen:04d}.json", "w") as f:
        json.dump(state, f, indent=2, default=lambda o: o.tolist() if hasattr(o, 'tolist') else o)
    
    # 保存为Pickle
    import pickle
    with open(f"optimization_results/gen_{gen:04d}.pkl", "wb") as f:
        pickle.dump(state, f)
    
    # 保存每日结果
    daily_df = pd.DataFrame(daily_results)
    daily_df.to_csv(f"optimization_results/daily_results_gen_{gen:04d}.csv", index=False)
    
    # 评估最佳个体并绘制收益曲线
    if gen % 10 == 0:  # 每10代绘制一次收益曲线
        try:
            plot_optimization_results(daily_results, stats_dict, gen)
        except Exception as e:
            logger.error(f"Error plotting results for generation {gen}: {str(e)}")
    
    logger.info(f"Saved state for generation {gen}: Fitness={fitness:.6f}")

def plot_optimization_results(daily_results, stats_dict, gen):
    """绘制优化结果"""
    # 创建结果数据框架
    daily_df = pd.DataFrame(daily_results)
    
    # 计算累计收益
    daily_df['cumulative_return'] = daily_df['daily_return'].cumsum()
    daily_df['cumulative_budget'] = 200000 + daily_df['cumulative_return']
    
    # 计算基础预算和剩余预算的累计收益
    daily_df['base_budget_cumulative_return'] = daily_df['base_budget_return'].cumsum()
    daily_df['remaining_budget_cumulative_return'] = daily_df['remaining_budget_return'].cumsum()
    
    # 绘制收益曲线
    plt.figure(figsize=(20, 15))
    
    # 1. 累计收益曲线
    plt.subplot(3, 3, 1)
    plt.plot(range(len(daily_df)), daily_df['cumulative_return'], 'b-')
    plt.title('累计收益曲线')
    plt.xlabel('交易日序号')
    plt.ylabel('累计收益')
    plt.grid(True)
    
    # 2. 累计资金曲线
    plt.subplot(3, 3, 2)
    plt.plot(range(len(daily_df)), daily_df['cumulative_budget'], 'g-')
    plt.title('累计资金曲线')
    plt.xlabel('交易日序号')
    plt.ylabel('资金总额')
    plt.grid(True)
    
    # 3. 每日收益率
    plt.subplot(3, 3, 3)
    plt.bar(range(len(daily_df)), daily_df['daily_real_return_rate'])
    plt.title('每日实际收益率')
    plt.xlabel('交易日序号')
    plt.ylabel('收益率')
    plt.grid(True)
    
    # 4. 每日投资比例
    plt.subplot(3, 3, 4)
    plt.bar(range(len(daily_df)), daily_df['daily_ratio'])
    plt.title('每日投资比例')
    plt.xlabel('交易日序号')
    plt.ylabel('投资比例')
    plt.grid(True)
    
    # 5. 交易天数统计
    plt.subplot(3, 3, 5)
    labels = ['交易天数', '非交易天数']
    sizes = [stats_dict['trade_days'], stats_dict['total_days'] - stats_dict['trade_days']]
    plt.pie(sizes, labels=labels, autopct='%1.1f%%')
    plt.title('交易天数比例')
    
    # 6. 两种预算的累计收益对比
    plt.subplot(3, 3, 6)
    plt.plot(range(len(daily_df)), daily_df['base_budget_cumulative_return'], 'b-', label='基础预算收益')
    plt.plot(range(len(daily_df)), daily_df['remaining_budget_cumulative_return'], 'r-', label='剩余预算收益')
    plt.title('两种预算的累计收益对比')
    plt.xlabel('交易日序号')
    plt.ylabel('累计收益')
    plt.legend()
    plt.grid(True)
    
    # 7. 两种预算的每日收益对比
    plt.subplot(3, 3, 7)
    x = range(len(daily_df))
    width = 0.35
    plt.bar([i - width/2 for i in x], daily_df['base_budget_return'], width, label='基础预算收益')
    plt.bar([i + width/2 for i in x], daily_df['remaining_budget_return'], width, label='剩余预算收益')
    plt.title('两种预算的每日收益对比')
    plt.xlabel('交易日序号')
    plt.ylabel('每日收益')
    plt.legend()
    plt.grid(True)
    
    # 8. 回撤曲线
    # 计算每日回撤
    cumulative_max = daily_df['cumulative_budget'].cummax()
    drawdown = (cumulative_max - daily_df['cumulative_budget']) / cumulative_max
    plt.subplot(3, 3, 8)
    plt.plot(range(len(daily_df)), drawdown, 'r-')
    plt.title('回撤曲线')
    plt.xlabel('交易日序号')
    plt.ylabel('回撤比例')
    plt.grid(True)
    
    # 标记最大回撤区间
    max_dd_start = stats_dict.get('drawdown_start', 0)
    max_dd_end = stats_dict.get('drawdown_end', 0)
    if max_dd_end > max_dd_start:
        plt.axvspan(max_dd_start, max_dd_end, color='red', alpha=0.3, label=f'最大回撤: {stats_dict.get("max_drawdown", 0):.2%}')
        plt.legend()
    
    # 9. 参数值展示
    plt.subplot(3, 3, 9)
    plt.axis('off')
    param_text = "\n".join([f"{k}: {v:.4f}" for k, v in stats_dict.items() 
                          if k not in ['final_budget', 'drawdown_start', 'drawdown_end']])
    plt.text(0.1, 0.5, f"统计指标:\n{param_text}", fontsize=8)
    
    plt.suptitle(f'Generation {gen} - Total Return: {stats_dict["total_return_rate"]:.4f}, Final Budget: {stats_dict["final_budget"]:.2f}')
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(f"optimization_results/performance_gen_{gen:04d}.png", dpi=150)
    plt.close()
    
    # 保存详细统计信息
    stats_df = pd.DataFrame([stats_dict])
    stats_df.to_csv(f"optimization_results/stats_gen_{gen:04d}.csv", index=False)

def main():
    """主函数"""
    # 加载交易数据
    trading_df = pd.read_csv(r'D:\workspace\TradeX\backtest_results\倒接力31_交易记录.csv')
    
    # 确保日期已经是字符串格式，不需要转换
    logger.info(f"Loaded {len(trading_df)} trading records")
    from evaluater_generate_datas_expand_params import get_tick_data
    
    # 预先缓存所有需要的tick数据
    logger.info("Pre-caching tick data...")
    unique_stock_dates = trading_df[['stock_code', 'trade_date']].drop_duplicates()
    
    for _, row in unique_stock_dates.iterrows():
        stock_code = row['stock_code']
        trade_date = row['trade_date']  # 已经是字符串格式
        get_tick_data_main(stock_code, trade_date, get_tick_data)  # 这会自动缓存数据
    
    logger.info(f"Pre-cached {len(tick_data_cache)} tick data files")
    
    # 运行遗传算法优化
    best_individual = setup_genetic_algorithm(
        trading_df, 
        tick_data_cache,  # 直接传递缓存字典
        population_size=30, 
        num_generations=30,
        n_processes=20
    )
    
    # 解码最佳参数
    best_params = decode_individual(best_individual)
    
    # 评估最佳个体获取详细结果
    best_fitness, daily_results, stats_dict = evaluate_individual(best_individual)
    
    # 打印最佳参数
    logger.info("Optimization completed!")
    logger.info(f"Best fitness: {best_fitness:.6f}")
    logger.info("Best parameters:")
    for param, value in best_params.items():
        logger.info(f"  {param}: {value}")
    
    # 打印统计信息
    logger.info("Optimization statistics:")
    for key, value in stats_dict.items():
        logger.info(f"  {key}: {value}")
    
    # 保存最终结果
    daily_df = pd.DataFrame(daily_results)
    daily_df.to_csv("optimization_results/final_daily_results.csv", index=False)
    
    # 保存最佳参数
    with open("optimization_results/best_params.json", "w") as f:
        json.dump(best_params, f, indent=2)
    
    # 保存统计信息
    stats_df = pd.DataFrame([stats_dict])
    stats_df.to_csv("optimization_results/final_stats.csv", index=False)
    
    # 绘制最终结果
    plot_optimization_results(daily_results, stats_dict, "final")
    
    # 绘制参数重要性图
    param_names = list(best_params.keys())
    param_values = list(best_params.values())
    
    plt.figure(figsize=(10, 6))
    plt.barh(range(len(param_names)), param_values)
    plt.yticks(range(len(param_names)), param_names)
    plt.xlabel('Parameter Value')
    plt.title('Optimized Parameter Values')
    plt.tight_layout()
    plt.savefig("optimization_results/parameter_values.png", dpi=150)
    plt.close()
    
    # 创建详细的交易结果文件，类似于输入的dataframe
    trading_df_with_results = trading_df.copy()
    
    # 添加优化后的结果列
    for col in daily_df.columns:
        if col not in trading_df_with_results.columns:
            trading_df_with_results[col] = daily_df[col]
    
    # 保存详细的交易结果
    trading_df_with_results.to_csv("optimization_results/detailed_trading_results.csv", index=False)
    logger.info("Saved detailed trading results to optimization_results/detailed_trading_results.csv")

if __name__ == "__main__":
    main()