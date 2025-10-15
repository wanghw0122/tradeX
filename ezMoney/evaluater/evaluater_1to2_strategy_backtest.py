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
import pandas as pd
import csv
from typing import List, Dict, Any, Tuple

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

y = 4

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
    'sell_max_days': (1, y, int),
}

# 需要优化的参数列表
OPTIMIZABLE_PARAMS = list(PARAM_RANGES.keys())

class BacktestResult:
    """回测结果类"""
    def __init__(self):
        self.trades = []  # 交易记录列表
        self.capital_curve = []  # 资金曲线
        self.initial_capital = 0
        
    def add_trade(self, strategy_name, stock_code, stock_name, trade_date, buy_price, 
                 sell_price, sell_date, return_rate, profit, is_profitable, sell_tick_steps=-1):
        """添加交易记录"""
        self.trades.append({
            'strategy_name': strategy_name,
            'stock_code': stock_code,
            'stock_name': stock_name,
            'trade_date': trade_date,
            'buy_price': buy_price,
            'sell_price': sell_price,
            'sell_date': sell_date,
            'return_rate': return_rate,
            'profit': profit,
            'is_profitable': is_profitable,
            'sell_tick_steps': sell_tick_steps  # 添加卖出时的tick steps
        })
    
    def to_dataframe(self):
        """将交易记录转换为DataFrame"""
        return pd.DataFrame(self.trades)
    
    def save_to_csv(self, filename):
        """保存交易记录到CSV文件"""
        df = self.to_dataframe()
        df.to_csv(filename, index=False, encoding='utf-8-sig')
        
    def calculate_statistics(self):
        """计算回测统计指标"""
        df = self.to_dataframe()
        if df.empty:
            return {}
        
        total_trades = len(df)
        profitable_trades = len(df[df['is_profitable'] == True])
        loss_trades = total_trades - profitable_trades
        win_rate = profitable_trades / total_trades if total_trades > 0 else 0
        
        total_profit = df['profit'].sum()
        avg_profit = df['profit'].mean() if total_trades > 0 else 0
        max_profit = df['profit'].max() if total_trades > 0 else 0
        min_profit = df['profit'].min() if total_trades > 0 else 0
        
        avg_return_rate = df['return_rate'].mean() if total_trades > 0 else 0
        max_return_rate = df['return_rate'].max() if total_trades > 0 else 0
        min_return_rate = df['return_rate'].min() if total_trades > 0 else 0
        
        # 计算最大回撤
        capital_array = np.array(self.capital_curve)
        peak = np.maximum.accumulate(capital_array)
        drawdowns = (peak - capital_array) / peak
        max_drawdown = np.max(drawdowns) if len(drawdowns) > 0 else 0
        
        # 计算夏普比率
        returns = np.diff(capital_array) / capital_array[:-1]
        sharpe_ratio = np.mean(returns) / (np.std(returns) + 1e-8) * np.sqrt(252) if len(returns) > 0 else 0
        
        return {
            'total_trades': total_trades,
            'profitable_trades': profitable_trades,
            'loss_trades': loss_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'max_profit': max_profit,
            'min_profit': min_profit,
            'avg_return_rate': avg_return_rate,
            'max_return_rate': max_return_rate,
            'min_return_rate': min_return_rate,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'final_capital': capital_array[-1] if len(capital_array) > 0 else self.initial_capital
        }

def run_backtest(params: Dict[str, Any], stock_data_list: List[Dict], 
                strategy_name: str, initial_capital: float = 200000) -> BacktestResult:
    """
    运行回测
    
    参数:
        params: 策略参数字典
        stock_data_list: 股票数据列表
        strategy_name: 策略名称
        initial_capital: 初始资金
    
    返回:
        BacktestResult对象，包含所有交易记录和资金曲线
    """
    result = BacktestResult()
    result.initial_capital = initial_capital
    capital = initial_capital
    result.capital_curve = [capital]
    
    logger.info(f"开始回测策略: {strategy_name}, 股票数量: {len(stock_data_list)}")
    
    for stock_data in tqdm(stock_data_list, desc="回测进度"):
        try:
            stock_code = stock_data['stock_code']
            stock_name = stock_data.get('stock_name', '未知')
            trade_date = stock_data.get('datekey', '未知日期')
            trade_price = stock_data['trade_price']
            
            cur_res_datas = stock_data['cur_res_datas']
            if not cur_res_datas or len(cur_res_datas) != y:
                logger.warning(f"股票 {stock_code} 数据异常，跳过")
                continue
                
            i = 0
            actual_sell_price = 0
            actual_sell_prices = []
            sell_date = None
            sell_tick_steps = -1  # 默认值为-1，表示非tick级别卖出

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
                
                # 获取日期信息
                current_date = cur_res_data.get('date', 'unknown_date')
                
                if open_profit > params['day_zy_line']:
                    monitor_type = 1
                elif open_profit < params['day_zs_line']:
                    monitor_type = 2
                else:
                    monitor_type = 0
                
                if monitor_type == 0:
                    if params['sell_afternoon']:
                        if i >= params['sell_max_days'] or i >= y:
                            actual_sell_price = close
                            if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                actual_sell_price = next_open
                            if actual_sell_prices:
                                actual_sell_prices.append(actual_sell_price)
                                sell_date = current_date
                                break
                            else:
                                actual_sell_prices.append(actual_sell_price)
                                actual_sell_prices.append(actual_sell_price)
                                sell_date = current_date
                                break
                        if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                continue
                        if close_profit > params['day_zy_line'] or close_profit < params['day_zs_line']:
                            actual_sell_price = close
                            if params['sell_half_afternoon']:
                                if actual_sell_prices:
                                    actual_sell_prices.append(actual_sell_price)
                                    sell_date = current_date
                                    break
                                else:
                                    actual_sell_prices.append(actual_sell_price)
                                    continue
                            else:
                                if actual_sell_prices:
                                    actual_sell_prices.append(actual_sell_price)
                                    sell_date = current_date
                                    break
                                else:
                                    actual_sell_prices.append(actual_sell_price)
                                    actual_sell_prices.append(actual_sell_price)
                                    sell_date = current_date
                                    break
                        else:
                            if i >= params['sell_max_days'] or i >= y:
                                actual_sell_price = close
                                if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                    actual_sell_price = next_open
                                if actual_sell_prices:
                                    actual_sell_prices.append(actual_sell_price)
                                    sell_date = current_date
                                    break
                                else:
                                    actual_sell_prices.append(actual_sell_price)
                                    actual_sell_prices.append(actual_sell_price)
                                    sell_date = current_date
                                    break
                            else:
                                continue
                    else:
                        if i >= params['sell_max_days'] or i >= y:
                            actual_sell_price = close
                            if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                actual_sell_price = next_open
                            if actual_sell_prices:
                                actual_sell_prices.append(actual_sell_price)
                                sell_date = current_date
                                break
                            else:
                                actual_sell_prices.append(actual_sell_price)
                                actual_sell_prices.append(actual_sell_price)
                                sell_date = current_date
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
                        stock_name=stock_name,
                        stock_infos=stock_infos,
                        mkt_datas=mkt_datas,
                        params=params
                    )
                    sold, sell_price, current_tick_steps = monitor.get_result()

                    if sold:
                        sell_tick_steps = current_tick_steps  # 记录卖出时的tick steps
                        actual_sell_price = sell_price
                        if actual_sell_prices:
                            actual_sell_prices.append(actual_sell_price)
                            sell_date = current_date
                            break
                        else:
                            actual_sell_prices.append(actual_sell_price)
                            actual_sell_prices.append(actual_sell_price)
                            sell_date = current_date
                            break
                    else:
                        if i >= params['sell_max_days'] or i >= y:
                            actual_sell_price = close
                            if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                actual_sell_price = next_open
                            if actual_sell_prices:
                                actual_sell_prices.append(actual_sell_price)
                                sell_date = current_date
                                break
                            else:
                                actual_sell_prices.append(actual_sell_price)
                                actual_sell_prices.append(actual_sell_price)
                                sell_date = current_date
                                break
                        if params['sell_afternoon']:
                            if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                continue
                            if close_profit > params['day_zy_line'] or close_profit < params['day_zs_line']:
                                actual_sell_price = close
                                if params['sell_half_afternoon']:
                                    if actual_sell_prices:
                                        actual_sell_prices.append(actual_sell_price)
                                        sell_date = current_date
                                        break
                                    else:
                                        actual_sell_prices.append(actual_sell_price)
                                        continue
                                else:
                                    if actual_sell_prices:
                                        actual_sell_prices.append(actual_sell_price)
                                        sell_date = current_date
                                        break
                                    else:
                                        actual_sell_prices.append(actual_sell_price)
                                        actual_sell_prices.append(actual_sell_price)
                                        sell_date = current_date
                                        break
                            else:
                                if i >= params['sell_max_days'] or i >= y:
                                    actual_sell_price = close
                                    if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                        actual_sell_price = next_open
                                    if actual_sell_prices:
                                        actual_sell_prices.append(actual_sell_price)
                                        sell_date = current_date
                                        break
                                    else:
                                        actual_sell_prices.append(actual_sell_price)
                                        actual_sell_prices.append(actual_sell_price)
                                        sell_date = current_date
                                        break
                                else:
                                    continue
                        else:
                            if i >= params['sell_max_days'] or i >= y:
                                actual_sell_price = close
                                if cur_res_data['limit_up'] == 1 or cur_res_data['limit_down'] == 1:
                                    actual_sell_price = next_open
                                if actual_sell_prices:
                                    actual_sell_prices.append(actual_sell_price)
                                    sell_date = current_date
                                    break
                                else:
                                    actual_sell_prices.append(actual_sell_price)
                                    actual_sell_prices.append(actual_sell_price)
                                    sell_date = current_date
                                    break
                            else:
                                continue
            
            if len(actual_sell_prices) != 2:
                logger.warning(f"股票 {stock_code} 售卖异常，跳过")
                continue
            
            actual_sell_price = (actual_sell_prices[0] + actual_sell_prices[1]) / 2

            if trade_price > 0:
                shares = (capital / trade_price // 100) * 100
                cost = shares * trade_price
                revenue = shares * actual_sell_price
                profit = revenue - cost
                profit_pct = (actual_sell_price - trade_price) / trade_price
                is_profitable = profit > 0
                
                # 更新资金
                capital += profit
                result.capital_curve.append(capital)
                
                # 添加交易记录
                result.add_trade(
                    strategy_name=strategy_name,
                    stock_code=stock_code,
                    stock_name=stock_name,
                    trade_date=trade_date,
                    buy_price=trade_price,
                    sell_price=actual_sell_price,
                    sell_date=sell_date or trade_date,
                    return_rate=profit_pct,
                    profit=profit,
                    is_profitable=is_profitable,
                    sell_tick_steps=sell_tick_steps  # 添加卖出时的tick steps
                )
                
        except Exception as e:
            logger.error(f"处理股票 {stock_data.get('stock_code', '未知')} 时发生错误: {str(e)}")
            logger.error(traceback.format_exc())
            continue
    
    return result

def plot_backtest_results(result: BacktestResult, output_dir: str, strategy_name: str):
    """绘制回测结果图表"""
    os.makedirs(output_dir, exist_ok=True)
    
    # 绘制资金曲线
    plt.figure(figsize=(12, 6))
    plt.plot(result.capital_curve, 'b-', linewidth=2)
    plt.xlabel("交易次数")
    plt.ylabel("资金")
    plt.title(f"{strategy_name}策略资金曲线\n初始资金: {result.initial_capital:,} 最终资金: {result.capital_curve[-1]:,}")
    plt.grid(True)
    
    # 标记最高点和最低点
    capital_array = np.array(result.capital_curve)
    peak_idx = np.argmax(capital_array)
    trough_idx = np.argmin(capital_array[peak_idx:]) + peak_idx
    
    plt.plot(peak_idx, capital_array[peak_idx], 'ro', markersize=8, label="峰值")
    plt.plot(trough_idx, capital_array[trough_idx], 'go', markersize=8, label="谷值")
    
    # 添加回撤区域
    peak = np.maximum.accumulate(capital_array)
    plt.fill_between(range(len(capital_array)), 
                     capital_array, 
                     peak, 
                     color='red', alpha=0.1)
    
    plt.legend()
    plt.tight_layout()
    plt.savefig(f"{output_dir}/{strategy_name}_资金曲线.png", dpi=150)
    plt.close()
    
    # 绘制收益分布直方图
    if result.trades:
        df = result.to_dataframe()
        plt.figure(figsize=(10, 6))
        plt.hist(df['return_rate'] * 100, bins=50, alpha=0.7, color='blue')
        plt.xlabel("收益率 (%)")
        plt.ylabel("频次")
        plt.title(f"{strategy_name}策略收益率分布")
        plt.grid(True)
        plt.savefig(f"{output_dir}/{strategy_name}_收益率分布.png", dpi=150)
        plt.close()
    
    # 绘制每日收益曲线（如果有日期信息）
    if result.trades and 'sell_date' in result.trades[0]:
        try:
            df = result.to_dataframe()
            df['sell_date'] = pd.to_datetime(df['sell_date'])
            daily_profit = df.groupby('sell_date')['profit'].sum()
            
            plt.figure(figsize=(12, 6))
            daily_profit.plot(kind='bar', color=['red' if x < 0 else 'green' for x in daily_profit])
            plt.xlabel("日期")
            plt.ylabel("每日收益")
            plt.title(f"{strategy_name}策略每日收益")
            plt.xticks(rotation=45)
            plt.tight_layout()
            plt.savefig(f"{output_dir}/{strategy_name}_每日收益.png", dpi=150)
            plt.close()
        except Exception as e:
            logger.warning(f"无法绘制每日收益图: {str(e)}")

def run_backtest_with_params(params: Dict[str, Any], stock_data_file: str, strategy_name: str, 
                             initial_capital: float = 200000, output_dir: str = "backtest_results"):
    """
    使用参数字典运行回测
    
    参数:
        params: 策略参数字典
        stock_data_file: 股票数据文件路径
        strategy_name: 策略名称
        initial_capital: 初始资金
        output_dir: 输出目录
    """
    # 创建输出目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 加载股票数据
    logger.info(f"加载股票数据: {stock_data_file}")
    from evaluater_generate_datas_expand_params import build_evaluater_1to2_data_list_from_file
    stock_data_list = build_evaluater_1to2_data_list_from_file(250, stock_data_file)
    
    # 运行回测
    logger.info(f"开始回测策略: {strategy_name}")
    result = run_backtest(params, stock_data_list[0], strategy_name, initial_capital)
    
    # 保存交易记录
    csv_file = f"{output_dir}/{strategy_name}_交易记录.csv"
    result.save_to_csv(csv_file)
    logger.info(f"交易记录已保存到: {csv_file}")
    
    # 计算统计指标
    stats = result.calculate_statistics()
    stats_file = f"{output_dir}/{strategy_name}_统计指标.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    logger.info(f"统计指标已保存到: {stats_file}")
    
    # 打印统计摘要
    logger.info(f"\n{strategy_name}策略回测结果摘要:")
    logger.info(f"总交易次数: {stats['total_trades']}")
    logger.info(f"盈利交易次数: {stats['profitable_trades']}")
    logger.info(f"亏损交易次数: {stats['loss_trades']}")
    logger.info(f"胜率: {stats['win_rate']:.2%}")
    logger.info(f"总收益: {stats['total_profit']:.2f}")
    logger.info(f"平均收益: {stats['avg_profit']:.2f}")
    logger.info(f"最大收益: {stats['max_profit']:.2f}")
    logger.info(f"最小收益: {stats['min_profit']:.2f}")
    logger.info(f"平均收益率: {stats['avg_return_rate']:.2%}")
    logger.info(f"最大回撤: {stats['max_drawdown']:.2%}")
    logger.info(f"夏普比率: {stats['sharpe_ratio']:.2f}")
    logger.info(f"最终资金: {stats['final_capital']:.2f}")
    
    # 绘制图表
    plot_backtest_results(result, output_dir, strategy_name)
    logger.info(f"图表已保存到: {output_dir}")
    
    return result

def run_multiple_backtests_with_params(strategy_params_map: Dict[str, Dict], stock_data_file: str, 
                                      initial_capital: float = 200000, output_dir: str = "backtest_results"):
    """
    使用参数字典运行多个策略的回测
    
    参数:
        strategy_params_map: 策略名称到参数字典的映射
        stock_data_file: 股票数据文件路径
        initial_capital: 初始资金
        output_dir: 输出目录
    """
    results = {}
    
    for strategy_name, params in strategy_params_map.items():
        try:
            logger.info(f"\n{'='*80}")
            logger.info(f"开始回测策略: {strategy_name}")
            logger.info(f"{'='*80}")
            
            result = run_backtest_with_params(
                params, stock_data_file, strategy_name, initial_capital, output_dir
            )
            results[strategy_name] = result
            
        except Exception as e:
            logger.error(f"回测策略 {strategy_name} 时发生错误: {str(e)}")
            logger.error(traceback.format_exc())
    
    # 比较所有策略的表现
    if len(results) > 1:
        compare_strategies(results, output_dir)
    
    return results

def compare_strategies(results: Dict[str, BacktestResult], output_dir: str):
    """比较多个策略的表现"""
    comparison_data = []
    
    for strategy_name, result in results.items():
        stats = result.calculate_statistics()
        comparison_data.append({
            'strategy_name': strategy_name,
            'total_trades': stats['total_trades'],
            'profitable_trades': stats['profitable_trades'],
            'loss_trades': stats['loss_trades'],
            'win_rate': stats['win_rate'],
            'total_profit': stats['total_profit'],
            'avg_profit': stats['avg_profit'],
            'max_profit': stats['max_profit'],
            'min_profit': stats['min_profit'],
            'avg_return_rate': stats['avg_return_rate'],
            'max_drawdown': stats['max_drawdown'],
            'sharpe_ratio': stats['sharpe_ratio'],
            'final_capital': stats['final_capital']
        })
    
    # 保存比较结果
    comparison_df = pd.DataFrame(comparison_data)
    comparison_file = f"{output_dir}/策略比较.csv"
    comparison_df.to_csv(comparison_file, index=False, encoding='utf-8-sig')
    logger.info(f"策略比较结果已保存到: {comparison_file}")
    
    # 绘制策略比较图
    plt.figure(figsize=(14, 10))
    
    # 1. 资金曲线比较
    plt.subplot(2, 2, 1)
    for strategy_name, result in results.items():
        capital_normalized = np.array(result.capital_curve) / result.initial_capital
        plt.plot(capital_normalized, label=strategy_name)
    plt.xlabel("交易次数")
    plt.ylabel("标准化资金")
    plt.title("策略资金曲线比较")
    plt.legend()
    plt.grid(True)
    
    # 2. 胜率比较
    plt.subplot(2, 2, 2)
    win_rates = [result.calculate_statistics()['win_rate'] for result in results.values()]
    plt.bar(results.keys(), win_rates)
    plt.xlabel("策略")
    plt.ylabel("胜率")
    plt.title("策略胜率比较")
    plt.xticks(rotation=45)
    
    # 3. 夏普比率比较
    plt.subplot(2, 2, 3)
    sharpe_ratios = [result.calculate_statistics()['sharpe_ratio'] for result in results.values()]
    plt.bar(results.keys(), sharpe_ratios)
    plt.xlabel("策略")
    plt.ylabel("夏普比率")
    plt.title("策略夏普比率比较")
    plt.xticks(rotation=45)
    
    # 4. 最大回撤比较
    plt.subplot(2, 2, 4)
    max_drawdowns = [result.calculate_statistics()['max_drawdown'] for result in results.values()]
    plt.bar(results.keys(), max_drawdowns)
    plt.xlabel("策略")
    plt.ylabel("最大回撤")
    plt.title("策略最大回撤比较")
    plt.xticks(rotation=45)
    
    plt.tight_layout()
    plt.savefig(f"{output_dir}/策略比较.png", dpi=150)
    plt.close()
    
    logger.info("策略比较完成")

if __name__ == "__main__":
    # 定义策略和参数字典的映射
    strategy_params_map = {
        # '倒接力31':{
        #     "per_step_tick_gap": 1,
        #     "cold_start_steps": 45,
        #     "max_abserve_tick_steps": 385,
        #     "max_abserce_avg_price_down_steps": 3,
        #     "stop_profit_open_hc_pct": -0.13615309678470672,
        #     "dynamic_hc_stop_profit_thres": 4.043163172236562,
        #     "last_close_price_hc_pct": -0.005965932680446158,
        #     "last_day_sell_thres": 0.1311974104495398,
        #     "last_day_sell_huiche": 0.014237431607868577,
        #     "fd_mount": 20192858,
        #     "fd_vol_pct": 0.6888893564952334,
        #     "fd_ju_ticks": 50,
        #     "max_zb_times": 20,
        #     "stagnation_kline_ticks": 19,
        #     "decline_kline_ticks": 17,
        #     "yang_yin_threshold": 0.02944726584363552,
        #     "stagnation_n": 21,
        #     "stagnation_volume_ratio_threshold": 65.17825666664703,
        #     "stagnation_ratio_threshold": 172,
        #     "decline_volume_ratio_threshold": 62.11620869057822,
        #     "max_rebounds": 7,
        #     "decline_ratio_threshold": 663,
        #     "flxd_ticks": 111,
        #     "flzz_ticks": 224,
        #     "use_simiple_kline_strategy_flxd": True,
        #     "use_simiple_kline_strategy_flzz": True,
        #     "flzz_use_smooth_price": True,
        #     "flzz_zf_thresh": 0.06022472460958257,
        #     "kline_sell_flxd_zy": True,
        #     "kline_sell_flxd_zs": False,
        #     "kline_sell_flzz_zs": True,
        #     "kline_sell_flzz_zy": True,
        #     "last_open_price_hc_pct": 0.009927200217467848,
        #     "open_price_max_hc": -0.09956760551146909,
        #     "loss_per_step_tick_gap": 1,
        #     "loss_cold_start_steps": 2,
        #     "loss_max_abserve_tick_steps": 79,
        #     "loss_max_abserce_avg_price_down_steps": 10,
        #     "loss_dynamic_hc_stop_profit_thres": 0.812141265825588,
        #     "loss_last_close_price_hc_pct": -0.042775079490827976,
        #     "loss_last_open_price_hc_pct": -0.007738604220134396,
        #     "loss_open_price_max_hc": -0.08981981966595437,
        #     "loss_down_open_sell_wait_time": False,
        #     "down_open_sell_wait_time": True,
        #     "day_zy_line": 0.005415923150372701,
        #     "day_zs_line": -0.01169359128424749,
        #     "sell_afternoon": False,
        #     "sell_half_afternoon": False,
        #     "sell_max_days": 4,
        #     "stop_profit_pct": 0.0,
        #     "static_hc_stop_profit_pct": 1.0,
        #     "loss_static_hc_stop_profit_pct": 1.0
        # },

        # '高强中低开方向前2': {
        #         "per_step_tick_gap": 14,
        #         "cold_start_steps": 21,
        #         "max_abserve_tick_steps": 688,
        #         "max_abserce_avg_price_down_steps": 5,
        #         "stop_profit_open_hc_pct": -0.14434534146133335,
        #         "dynamic_hc_stop_profit_thres": 0.34887566466390285,
        #         "last_close_price_hc_pct": 0.009900010439712198,
        #         "last_day_sell_thres": 0.9793077824922035,
        #         "last_day_sell_huiche": 0.008733069801992736,
        #         "fd_mount": 103280507,
        #         "fd_vol_pct": 0.461307975507421,
        #         "fd_ju_ticks": 1,
        #         "max_zb_times": 1,
        #         "stagnation_kline_ticks": 29,
        #         "decline_kline_ticks": 33,
        #         "yang_yin_threshold": 0.010029104499523307,
        #         "stagnation_n": 29,
        #         "stagnation_volume_ratio_threshold": 48.944807796888036,
        #         "stagnation_ratio_threshold": 597,
        #         "decline_volume_ratio_threshold": 19.196195133475022,
        #         "max_rebounds": 0,
        #         "decline_ratio_threshold": 909,
        #         "flxd_ticks": 348,
        #         "flzz_ticks": 855,
        #         "use_simiple_kline_strategy_flxd": True,
        #         "use_simiple_kline_strategy_flzz": False,
        #         "flzz_use_smooth_price": False,
        #         "flzz_zf_thresh": 0.09846866528869569,
        #         "kline_sell_flxd_zy": False,
        #         "kline_sell_flxd_zs": True,
        #         "kline_sell_flzz_zs": True,
        #         "kline_sell_flzz_zy": True,
        #         "last_open_price_hc_pct": -0.017992408811599993,
        #         "open_price_max_hc": -0.0001556764463843429,
        #         "loss_per_step_tick_gap": 1,
        #         "loss_cold_start_steps": 1,
        #         "loss_max_abserve_tick_steps": 56,
        #         "loss_max_abserce_avg_price_down_steps": 12,
        #         "loss_dynamic_hc_stop_profit_thres": 0.010000000000000002,
        #         "loss_last_close_price_hc_pct": -0.04181789338891646,
        #         "loss_last_open_price_hc_pct": 0.009649778493764433,
        #         "loss_open_price_max_hc": -0.0006999835176486604,
        #         "loss_down_open_sell_wait_time": False,
        #         "down_open_sell_wait_time": False,
        #         "day_zy_line": 0.03271366441706974,
        #         "day_zs_line": -0.03630322411643912,
        #         "sell_afternoon": True,
        #         "sell_half_afternoon": True,
        #         "sell_max_days": 3,
        #         "stop_profit_pct": 0.0,
        #         "static_hc_stop_profit_pct": 1.0,
        #         "loss_static_hc_stop_profit_pct": 1.0
        #     },
        # '高强中低开低吸强方向前2':{
        #         "per_step_tick_gap": 11,
        #         "cold_start_steps": 22,
        #         "max_abserve_tick_steps": 159,
        #         "max_abserce_avg_price_down_steps": 6,
        #         "stop_profit_open_hc_pct": -0.08877130010961737,
        #         "dynamic_hc_stop_profit_thres": 1.5551440910534233,
        #         "last_close_price_hc_pct": 0.00904442326252453,
        #         "last_day_sell_thres": 0.19936768015963496,
        #         "last_day_sell_huiche": 0.0024135004211861023,
        #         "fd_mount": 81429663,
        #         "fd_vol_pct": 0.49984843051505834,
        #         "fd_ju_ticks": 7,
        #         "max_zb_times": 25,
        #         "stagnation_kline_ticks": 16,
        #         "decline_kline_ticks": 5,
        #         "yang_yin_threshold": 0.0022474535460190064,
        #         "stagnation_n": 15,
        #         "stagnation_volume_ratio_threshold": 36.97649609846565,
        #         "stagnation_ratio_threshold": 298,
        #         "decline_volume_ratio_threshold": 15.00439283406275,
        #         "max_rebounds": 0,
        #         "decline_ratio_threshold": 81,
        #         "flxd_ticks": 490,
        #         "flzz_ticks": 1043,
        #         "use_simiple_kline_strategy_flxd": True,
        #         "use_simiple_kline_strategy_flzz": True,
        #         "flzz_use_smooth_price": True,
        #         "flzz_zf_thresh": -0.019324393939138144,
        #         "kline_sell_flxd_zy": True,
        #         "kline_sell_flxd_zs": True,
        #         "kline_sell_flzz_zs": False,
        #         "kline_sell_flzz_zy": True,
        #         "last_open_price_hc_pct": 0.009207286167419407,
        #         "open_price_max_hc": -0.08980725552614663,
        #         "loss_per_step_tick_gap": 1,
        #         "loss_cold_start_steps": 1,
        #         "loss_max_abserve_tick_steps": 216,
        #         "loss_max_abserce_avg_price_down_steps": 1,
        #         "loss_dynamic_hc_stop_profit_thres": 7.060285489758057,
        #         "loss_last_close_price_hc_pct": -0.054885082285079455,
        #         "loss_last_open_price_hc_pct": -0.006892303797429984,
        #         "loss_open_price_max_hc": -0.012496595491574782,
        #         "loss_down_open_sell_wait_time": False,
        #         "down_open_sell_wait_time": True,
        #         "day_zy_line": 0.03291087567775239,
        #         "day_zs_line": -0.04726409163277622,
        #         "sell_afternoon": False,
        #         "sell_half_afternoon": True,
        #         "sell_max_days": 3,
        #         "stop_profit_pct": 0.0,
        #         "static_hc_stop_profit_pct": 1.0,
        #         "loss_static_hc_stop_profit_pct": 1.0
        #     },
        '首红断低吸第一高频': {
            "per_step_tick_gap": 16,
            "cold_start_steps": 4,
            "max_abserve_tick_steps": 829,
            "max_abserce_avg_price_down_steps": 10,
            "stop_profit_open_hc_pct": -0.002850435144143261,
            "dynamic_hc_stop_profit_thres": 0.5862656709578017,
            "last_close_price_hc_pct": -0.03820308472819503,
            "last_day_sell_thres": 0.21731518911257364,
            "last_day_sell_huiche": 0.013461334931976852,
            "fd_mount": 36375145,
            "fd_vol_pct": 0.638250890273812,
            "fd_ju_ticks": 5,
            "max_zb_times": 2,
            "stagnation_kline_ticks": 38,
            "decline_kline_ticks": 48,
            "yang_yin_threshold": 0.0021139232493034366,
            "stagnation_n": 26,
            "stagnation_volume_ratio_threshold": 37.95404882959419,
            "stagnation_ratio_threshold": 688,
            "decline_volume_ratio_threshold": 81.66145284444677,
            "max_rebounds": 4,
            "decline_ratio_threshold": 1468,
            "flxd_ticks": 267,
            "flzz_ticks": 991,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": True,
            "flzz_use_smooth_price": False,
            "flzz_zf_thresh": -0.008847071797489992,
            "kline_sell_flxd_zy": False,
            "kline_sell_flxd_zs": True,
            "kline_sell_flzz_zs": True,
            "kline_sell_flzz_zy": False,
            "last_open_price_hc_pct": -0.006555045038654269,
            "open_price_max_hc": -0.07958645661591879,
            "loss_per_step_tick_gap": 1,
            "loss_cold_start_steps": 0,
            "loss_max_abserve_tick_steps": 298,
            "loss_max_abserce_avg_price_down_steps": 7,
            "loss_dynamic_hc_stop_profit_thres": 0.5505881558458123,
            "loss_last_close_price_hc_pct": -0.060240407181819576,
            "loss_last_open_price_hc_pct": -0.0212662234889203,
            "loss_open_price_max_hc": -0.003036271395056148,
            "loss_down_open_sell_wait_time": True,
            "down_open_sell_wait_time": True,
            "day_zy_line": 0.005029501308747063,
            "day_zs_line": -0.11140574139868037,
            "sell_afternoon": True,
            "sell_half_afternoon": False,
            "sell_max_days": 2,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
    '首红断低吸第二高频': {
            "per_step_tick_gap": 13,
            "cold_start_steps": 20,
            "max_abserve_tick_steps": 938,
            "max_abserce_avg_price_down_steps": 7,
            "stop_profit_open_hc_pct": -0.0027353081350318434,
            "dynamic_hc_stop_profit_thres": 0.6013706338292539,
            "last_close_price_hc_pct": -0.03761245647986554,
            "last_day_sell_thres": 0.5205346765902945,
            "last_day_sell_huiche": 0.014781482579791231,
            "fd_mount": 42677175,
            "fd_vol_pct": 0.4181723815583741,
            "fd_ju_ticks": 44,
            "max_zb_times": 25,
            "stagnation_kline_ticks": 4,
            "decline_kline_ticks": 30,
            "yang_yin_threshold": 0.018985832261433848,
            "stagnation_n": 14,
            "stagnation_volume_ratio_threshold": 99.99829215257026,
            "stagnation_ratio_threshold": 1382,
            "decline_volume_ratio_threshold": 45.12608483836211,
            "max_rebounds": 13,
            "decline_ratio_threshold": 329,
            "flxd_ticks": 261,
            "flzz_ticks": 2000,
            "use_simiple_kline_strategy_flxd": True,
            "use_simiple_kline_strategy_flzz": False,
            "flzz_use_smooth_price": False,
            "flzz_zf_thresh": 0.09767952388231449,
            "kline_sell_flxd_zy": False,
            "kline_sell_flxd_zs": False,
            "kline_sell_flzz_zs": False,
            "kline_sell_flzz_zy": False,
            "last_open_price_hc_pct": -0.005446449194498333,
            "open_price_max_hc": -0.08545249106922401,
            "loss_per_step_tick_gap": 17,
            "loss_cold_start_steps": 27,
            "loss_max_abserve_tick_steps": 497,
            "loss_max_abserce_avg_price_down_steps": 5,
            "loss_dynamic_hc_stop_profit_thres": 0.10208033699906673,
            "loss_last_close_price_hc_pct": -0.024749296595047578,
            "loss_last_open_price_hc_pct": -0.0466017243182672,
            "loss_open_price_max_hc": -0.04212453021344702,
            "loss_down_open_sell_wait_time": True,
            "down_open_sell_wait_time": True,
            "day_zy_line": 0.016747394251459685,
            "day_zs_line": -0.11130382714739091,
            "sell_afternoon": True,
            "sell_half_afternoon": False,
            "sell_max_days": 3,
            "stop_profit_pct": 0.0,
            "static_hc_stop_profit_pct": 1.0,
            "loss_static_hc_stop_profit_pct": 1.0
        },
        # 可以添加更多策略...
    }
    
    # 股票数据文件
    stock_data_file = r'D:\workspace\TradeX\notebook\new_strategy_eval\date_1to2_stock_data_shd_1004.csv'
    
    # 运行回测
    results = run_multiple_backtests_with_params(
        strategy_params_map=strategy_params_map,
        stock_data_file=stock_data_file,
        initial_capital=200000,
        output_dir="backtest_results"
    )