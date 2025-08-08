import numpy as np
import random
from scipy.signal import savgol_filter
import logging
import sys
import time
sys.path.append(r"D:\workspace\TradeX\ezMoney")
from common import constants
from date_utils import date as dt
import json
import datetime
import os
from xtquant import xttrader
import pandas as pd
import akshare as ak
import multiprocessing
import matplotlib.pyplot as plt
import traceback
from xtquant import xtdata
import concurrent.futures
import sqlite3
import pandas as pd
from tqdm import tqdm  
logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('strategy_optimization.log', encoding='utf-8')
        ]
    )
logger = logging.getLogger('StrategyOptimization')
    
def init_process():
    xtdata.connect(port=58611)


strategy_name_to_max_down_pct = {
    '高强中低开低吸': 5.5,
    '低位高强中低开低吸': 3,
    '低位高强低吸': 5.5,
    '低位孕线低吸': 5.5,
    '低位中强中低开低吸': 5.5,
    '中强中低开低吸': 5.5,
    '首红断低吸': 5.5,
    '一进二弱转强': 4,
    '高位高强追涨': 5.5,
}

class TripleFilter:
    """三级滤波价格平滑器"""
    def __init__(self, ema_alpha=0.15, kalman_q=0.02, kalman_r=0.05, sg_window=21):
        self.ema_alpha = ema_alpha
        self.kalman_q = kalman_q
        self.kalman_r = kalman_r
        self.sg_window = int(sg_window)  # 确保为整数
        
        self.ema = None
        self.kalman_x = None
        self.kalman_p = 1.0
        self.price_buffer = []
        
    def update(self, price):
        # EMA滤波
        if self.ema is None:
            self.ema = price
        else:
            self.ema = self.ema_alpha * price + (1 - self.ema_alpha) * self.ema
        
        # Kalman滤波
        if self.kalman_x is None:
            self.kalman_x = self.ema
        else:
            p_pred = self.kalman_p + self.kalman_q
            k = p_pred / (p_pred + self.kalman_r)
            self.kalman_x = self.kalman_x + k * (self.ema - self.kalman_x)
            self.kalman_p = (1 - k) * p_pred
        
        # SG滤波
        self.price_buffer.append(self.kalman_x)
        if len(self.price_buffer) > self.sg_window:
            self.price_buffer.pop(0)
        
        if len(self.price_buffer) >= self.sg_window:
            return savgol_filter(self.price_buffer, self.sg_window, 3)[-1]
        return self.kalman_x

class SignalDetector:
    """买点信号检测器"""
    def __init__(self, macd_fast=12, macd_slow_ratio=2.15, macd_signal=9, 
                 ema_fast=10, ema_slow_ratio=1.5, volume_window=10,
                 price_confirm_ticks=3, strength_confirm_ticks=2, strength_threshold=0.5, 
                 volume_weight=0.4,
                 use_price_confirm=True,  # 是否使用价格确认
                 use_strength_confirm=True,  # 是否使用强度确认
                 dead_cross_threshold=0.3,  # 死叉信号强度阈值
                 price_drop_threshold=0.005,  # 价格下跌阈值 (0.5%)
                 max_confirm_ticks=10,  # 最大确认tick数
                 debug=False):
        # 确保周期参数为整数
        self.macd_fast = int(macd_fast)
        self.macd_slow = int(macd_slow_ratio * macd_fast)  # 计算后取整
        self.macd_signal = int(macd_signal)
        self.ema_fast = int(ema_fast)
        self.ema_slow = int(ema_slow_ratio * self.ema_fast)  # 计算后取整
        self.volume_window = int(volume_window)
        self.price_confirm_ticks = int(price_confirm_ticks)
        self.strength_confirm_ticks = int(strength_confirm_ticks)
        self.strength_threshold = strength_threshold
        self.use_price_confirm = use_price_confirm
        self.use_strength_confirm = use_strength_confirm
        self.dead_cross_threshold = dead_cross_threshold
        self.price_drop_threshold = price_drop_threshold
        self.max_confirm_ticks = max_confirm_ticks
        self.tech_weight = 1.0  # 固定为1
        self.volume_weight = volume_weight
        self.debug = debug
        
        # MACD状态
        self.macd_dif = None
        self.macd_dea = None
        self.last_macd_dif = None
        self.last_macd_dea = None
        
        # EMA状态
        self.ema_fast_val = None
        self.ema_slow_val = None
        self.last_ema_fast = None
        self.last_ema_slow = None
        
        # 成交量
        self.volume_history = []
        
        # 信号确认
        self.pending_signal = None
        self.confirm_count = 0
        self.confirm_strength = 0.0
        self.price_confirm_count = 0
        self.confirm_prices = []
        self.confirm_ticks = 0  # 信号确认计时器
        
        # 调试信息
        self.strength_history = []
    
    def update(self, price, volume):
        """更新状态并检测信号"""
        # 保存成交量
        self.volume_history.append(volume)
        if len(self.volume_history) > self.volume_window:
            self.volume_history.pop(0)
        
        # 更新MACD
        self.last_macd_dif = self.macd_dif
        self.last_macd_dea = self.macd_dea
        
        # 计算MACD (简化的增量计算)
        # if self.macd_dif is None:
        #     self.macd_dif = price
        #     self.macd_dea = price
        # else:
        #     # DIF = EMA(close, fast) - EMA(close, slow)
        #     alpha_fast = 2 / (self.macd_fast + 1)
        #     alpha_slow = 2 / (self.macd_slow + 1)
        #     self.macd_dif = self.macd_dif + alpha_fast * (price - self.macd_dif)
        #     self.macd_dif = self.macd_dif - alpha_slow * (price - self.macd_dif)
            
        #     # DEA = EMA(DIF, signal)
        #     alpha_signal = 2 / (self.macd_signal + 1)
        #     self.macd_dea = self.macd_dea + alpha_signal * (self.macd_dif - self.macd_dea)
        
        if self.macd_dif is None:
            self.macd_dif = 0
            self.macd_dea = 0
            self.ema_fast_macd = price
            self.ema_slow_macd = price
        else:
            # 计算快速EMA
            alpha_fast = 2 / (self.macd_fast + 1)
            self.ema_fast_macd += alpha_fast * (price - self.ema_fast_macd)
            
            # 计算慢速EMA
            alpha_slow = 2 / (self.macd_slow + 1)
            self.ema_slow_macd += alpha_slow * (price - self.ema_slow_macd)
            
            # 计算DIF = EMA(fast) - EMA(slow)
            self.macd_dif = self.ema_fast_macd - self.ema_slow_macd
            
            # 计算DEA（信号线）= EMA(DIF, signal_period)
            alpha_signal = 2 / (self.macd_signal + 1)
            self.macd_dea += alpha_signal * (self.macd_dif - self.macd_dea)
        
        # 更新EMA
        self.last_ema_fast = self.ema_fast_val
        self.last_ema_slow = self.ema_slow_val
        
        if self.ema_fast_val is None:
            self.ema_fast_val = price
            self.ema_slow_val = price
        else:
            alpha_fast = 2 / (self.ema_fast + 1)
            alpha_slow = 2 / (self.ema_slow + 1)
            self.ema_fast_val = self.ema_fast_val + alpha_fast * (price - self.ema_fast_val)
            self.ema_slow_val = self.ema_slow_val + alpha_slow * (price - self.ema_slow_val)
        
        # 检测新信号
        signal = self._detect_signal(price, volume)
        
        # 检查是否有待确认信号
        if self.pending_signal:
            # 增加确认计时器
            self.confirm_ticks += 1
            
            # 1. 检查是否超过最大确认时间
            if self.confirm_ticks > self.max_confirm_ticks:
                if self.debug:
                    logger.info(f"信号超时取消! 类型: {self.pending_signal['type']}, "
                               f"经过ticks: {self.confirm_ticks}")
                self._reset_pending_signal()
                return None
            
            # 2. 检查是否出现死叉信号
            dead_cross_strength = self._detect_dead_cross()
            if dead_cross_strength > self.dead_cross_threshold:
                if self.debug:
                    logger.info(f"死叉信号取消! 类型: {self.pending_signal['type']}, "
                               f"死叉强度: {dead_cross_strength:.4f}")
                self._reset_pending_signal()
                return None
            
            # 3. 检查价格是否跌破信号触发价一定比例
            if price < self.pending_signal['price'] * (1 - self.price_drop_threshold):
                if self.debug:
                    logger.info(f"价格跌破取消! 类型: {self.pending_signal['type']}, "
                               f"信号价: {self.pending_signal['price']:.4f}, "
                               f"当前价: {price:.4f}, "
                               f"跌幅: {(self.pending_signal['price'] - price)/self.pending_signal['price']:.4f}")
                self._reset_pending_signal()
                return None
            
            # 保存后续价格用于确认
            self.confirm_prices.append(price)
            
            # 1. 技术指标强度确认
            if self.use_strength_confirm:
                # 计算当前技术指标强度（仅计算信号类型对应的指标）
                current_tech_strength = self._calculate_tech_strength(self.pending_signal['type'])
                
                # 强度增加确认
                strength_increase = current_tech_strength - self.confirm_strength
                if strength_increase > 0:
                    self.confirm_count += 1
                    
                    # 调试输出
                    if self.debug:
                        logger.debug(f"强度确认计数: {self.confirm_count}/{self.strength_confirm_ticks}, "
                                    f"强度增加: {strength_increase:.4f}, "
                                    f"当前强度: {current_tech_strength:.4f}")
            
            # 2. 价格确认（后续价格超过信号价格）
            if self.use_price_confirm:
                if price > self.pending_signal['price']:
                    self.price_confirm_count += 1
                    
                    # 调试输出
                    if self.debug:
                        logger.debug(f"价格确认计数: {self.price_confirm_count}/{self.price_confirm_ticks}, "
                                    f"当前价格: {price:.4f}, 信号价格: {self.pending_signal['price']:.4f}")
            
            # 检查确认条件
            strength_ok = (not self.use_strength_confirm) or (self.confirm_count >= self.strength_confirm_ticks)
            price_ok = (not self.use_price_confirm) or (self.price_confirm_count >= self.price_confirm_ticks)
            
            # 如果都不需要确认，则直接确认
            if not self.use_price_confirm and not self.use_strength_confirm:
                strength_ok = True
                price_ok = True
            
            if strength_ok and price_ok:
                confirmed_signal = self.pending_signal
                self._reset_pending_signal()
                
                if self.debug:
                    logger.info(f"信号确认! 类型: {confirmed_signal['type']}, "
                               f"强度: {confirmed_signal['strength']:.2f}, "
                               f"价格: {confirmed_signal['price']:.4f}, "
                               f"确认用时: {self.confirm_ticks} ticks")
                    if self.use_price_confirm:
                        logger.info(f"价格确认序列: {self.confirm_prices}")
                
                return confirmed_signal
        elif signal and self.debug:
            logger.info(f"新信号! 类型: {signal['type']}, "
                       f"强度: {signal['strength']:.2f}, "
                       f"价格: {signal['price']:.4f}")
        
        # 返回新信号
        if signal:
            # 如果都不需要确认，则直接返回信号
            if not self.use_price_confirm and not self.use_strength_confirm:
                if self.debug:
                    logger.info(f"立即确认信号! 类型: {signal['type']}, "
                               f"强度: {signal['strength']:.2f}, "
                               f"价格: {signal['price']:.4f}")
                return signal
            
            # 否则设置为待确认信号
            self.pending_signal = signal
            self.confirm_count = 0
            self.price_confirm_count = 0
            self.confirm_strength = signal['tech_strength']
            self.confirm_prices = []
            self.confirm_ticks = 0
            
            # 记录强度历史
            self.strength_history.append({
                'tick': len(self.strength_history),
                'strength': signal['strength'],
                'tech_strength': signal['tech_strength'],
                'volume_strength': signal['volume_strength']
            })
        
        return None
    
    def _reset_pending_signal(self):
        """重置待确认信号状态"""
        self.pending_signal = None
        self.confirm_count = 0
        self.price_confirm_count = 0
        self.confirm_strength = 0.0
        self.confirm_prices = []
        self.confirm_ticks = 0
    
    def _calculate_tech_strength(self, signal_type):
        """根据信号类型计算当前技术指标强度"""
        tech_strength = 0.0
        tech_count = 0
        
        # 根据信号类型计算相应的技术指标强度
        if signal_type in ['macd', 'both']:
            # MACD强度
            if self.macd_dif is not None and self.macd_dea is not None:
                macd_diff = self.macd_dif - self.macd_dea
                macd_strength = macd_diff / abs(self.macd_dea) if self.macd_dea != 0 else 0.0
                tech_strength += macd_strength
                tech_count += 1
        
        if signal_type in ['ema', 'both']:
            # EMA强度
            if self.ema_fast_val is not None and self.ema_slow_val is not None:
                ema_diff = self.ema_fast_val - self.ema_slow_val
                ema_strength = ema_diff / abs(self.ema_slow_val) if self.ema_slow_val != 0 else 0.0
                tech_strength += ema_strength
                tech_count += 1
        
        # 计算平均技术强度
        if tech_count > 0:
            return tech_strength / tech_count
        return 0.0
    
    def _detect_dead_cross(self):
        """检测死叉信号并返回信号强度"""
        dead_cross_strength = 0.0
        dead_cross_count = 0
        
        # MACD死叉
        if self.last_macd_dif is not None and self.last_macd_dea is not None:
            if self.last_macd_dif > self.last_macd_dea and self.macd_dif < self.macd_dea:
                macd_diff = self.macd_dea - self.macd_dif
                macd_strength = macd_diff / abs(self.macd_dea) if self.macd_dea != 0 else 0.0
                dead_cross_strength += macd_strength
                dead_cross_count += 1
        
        # EMA死叉
        if self.last_ema_fast is not None and self.last_ema_slow is not None:
            if self.last_ema_fast > self.last_ema_slow and self.ema_fast_val < self.ema_slow_val:
                ema_diff = self.ema_slow_val - self.ema_fast_val
                ema_strength = ema_diff / abs(self.ema_slow_val) if self.ema_slow_val != 0 else 0.0
                dead_cross_strength += ema_strength
                dead_cross_count += 1
        
        # 计算平均死叉强度
        if dead_cross_count > 0:
            return dead_cross_strength / dead_cross_count
        return 0.0
    
    def _detect_signal(self, price, volume):
        """检测潜在买点信号并计算信号强度"""
        signal_type = None
        tech_strength = 0.0
        tech_count = 0
        volume_strength = 0.0
        
        # MACD金叉
        macd_cross = False
        if self.last_macd_dif is not None and self.last_macd_dea is not None:
            if self.last_macd_dif < self.last_macd_dea and self.macd_dif > self.macd_dea:
                macd_cross = True
                signal_type = 'macd'
                
                # 计算MACD强度：DIF与DEA的差值
                macd_diff = self.macd_dif - self.macd_dea
                macd_strength = macd_diff / abs(self.macd_dea) if self.macd_dea != 0 else 0.0
                tech_strength += macd_strength
                tech_count += 1
        
        # EMA金叉
        ema_cross = False
        if self.last_ema_fast is not None and self.last_ema_slow is not None:
            if self.last_ema_fast < self.last_ema_slow and self.ema_fast_val > self.ema_slow_val:
                ema_cross = True
                if signal_type is None:
                    signal_type = 'ema'
                else:
                    signal_type = 'both'  # 同时触发MACD和EMA
                
                # 计算EMA强度：快线与慢线的差值
                ema_diff = self.ema_fast_val - self.ema_slow_val
                ema_strength = ema_diff / abs(self.ema_slow_val) if self.ema_slow_val != 0 else 0.0
                tech_strength += ema_strength
                tech_count += 1
        
        # 量能放大
        avg_length = min(self.volume_window, len(self.volume_history))
        if avg_length > 0:
            avg_volume = sum(self.volume_history[-avg_length:]) / avg_length
            volume_strength = min(volume / (avg_volume + 1), 5) - 1.0  # 0-1范围
        else:
            volume_strength = 0.0
        
        # 计算综合信号强度
        if signal_type and tech_count > 0:
            # 计算平均技术强度
            avg_tech_strength = tech_strength / tech_count
            
            # 综合强度 = 技术指标强度 * 技术权重 + 成交量强度 * 成交量权重
            strength = (avg_tech_strength * self.tech_weight + 
                        volume_strength * self.volume_weight)
            
            # 检查是否达到强度阈值
            if strength >= self.strength_threshold:
                # 调试输出
                if self.debug:
                    logger.debug(f"潜在信号: {signal_type}, "
                                f"技术强度: {avg_tech_strength:.4f}, "
                                f"成交量强度: {volume_strength:.4f}, "
                                f"综合强度: {strength:.4f}")
                
                return {
                    'price': price,
                    'type': signal_type,
                    'strength': strength,
                    'tech_strength': avg_tech_strength,
                    'volume_strength': volume_strength
                }
        
        return None

def backtest_single_stock_once(stock_data, strategy_name, params):
    """单只股票回测（带详细日志和可视化）"""
    # 创建输出目录
    output_dir = f"backtest_results/{datetime.now().strftime('%Y%m%d_%H%M%S')}_{strategy_name}"
    os.makedirs(output_dir, exist_ok=True)
    
    # 提取股票数据
    base_price = stock_data['base_price']
    total_budget = stock_data['budget']
    base_budget = stock_data['base_budget']
    down_price = stock_data['down_price']
    prices = stock_data['prices']
    volumes = stock_data['volumes']
    last_close_price = stock_data['last_close_price']
    datekey = stock_data['datekey']
    stock_code = stock_data['stock_code']
    
    # 计算实际最低价
    min_price = min(prices)
    if min_price <= 0:
        raise ValueError(f"最低价必须大于0 {min_price} {strategy_name}")
    max_down_pct = (base_price - down_price) / base_price
    
    # 初始化组件
    filter = TripleFilter(
        ema_alpha=params['ema_alpha'],
        kalman_q=params['kalman_q'],
        kalman_r=params['kalman_r'],
        sg_window=params['sg_window']
    )
    
    # 启用调试模式
    detector_params = params.copy()
    detector_params['debug'] = True
    
    detector = SignalDetector(
        macd_fast=params['macd_fast'],
        macd_slow_ratio=params['macd_slow_ratio'],
        macd_signal=params['macd_signal'],
        ema_fast=params['ema_fast'],
        ema_slow_ratio=params['ema_slow_ratio'],
        volume_window=params['volume_window'],
        price_confirm_ticks=params['price_confirm_ticks'],
        strength_confirm_ticks=params['strength_confirm_ticks'],
        strength_threshold=params['strength_threshold'],
        use_price_confirm=params['use_price_confirm'],
        use_strength_confirm=params['use_strength_confirm'],
        dead_cross_threshold=params.get('dead_cross_threshold', 0.3),
        price_drop_threshold=params.get('price_drop_threshold', 0.005),
        max_confirm_ticks=params.get('max_confirm_ticks', 10),
        volume_weight=params['volume_weight'],
        debug=True  # 强制启用调试模式
    )
    
    # 状态变量
    buy_points = []  # (tick_index, 价格, 金额, 信号强度, 买入原因)
    reference_price = base_price
    remaining_budget = total_budget
    left_base_budget = base_budget
    last_base_buy_tick_time = 0
    
    # 记录平滑价格和原始价格
    smooth_prices = []
    raw_prices = []
    
    # 记录每个tick的状态
    tick_logs = []
    
    logger.info(f"\n{'='*80}")
    logger.info(f"开始回测: 股票 {stock_code}, 日期 {datekey}, 策略 {strategy_name}")
    logger.info(f"初始价格: {base_price:.4f}, 总预算: {total_budget:.2f}, 基准预算: {base_budget:.2f}")
    logger.info(f"参数设置: {params}")
    logger.info(f"{'='*80}\n")
    
    # 处理每个tick
    for i, (raw_price, volume) in enumerate(zip(prices, volumes)):
        # 记录当前状态
        tick_info = {
            'tick': i,
            'raw_price': raw_price,
            'volume': volume,
            'remaining_budget': remaining_budget,
            'left_base_budget': left_base_budget,
            'reference_price': reference_price,
            'action': None,
            'action_reason': None,
            'action_amount': 0
        }
        
        # 平滑价格
        smooth_price = filter.update(raw_price)
        smooth_prices.append(smooth_price)
        raw_prices.append(raw_price)
        
        # 检测信号
        signal = detector.update(smooth_price, volume)
        
        buy_action = False
        buy_reason = None
        buy_amount = 0
        base_buy_budget = 0
        buy_total_budget = 0
        
        if signal and i <= 410:
            # 计算价格差异（相对于基准价）
            price_diff = (reference_price - raw_price) / base_price
            
            # 基准预算买入逻辑
            if (raw_price - down_price) / base_price < 0.01 and left_base_budget > 0:
                base_buy_budget = left_base_budget
                left_base_budget = 0
                last_base_buy_tick_time = i
                buy_reason = f"触及下跌价格线({down_price:.4f})"
                buy_action = True
            elif (base_price - raw_price) / base_price > 0.01 and left_base_budget > 0:
                down_base_pct = (base_price - raw_price) / base_price
                base_buy_budget = max(1/3, down_base_pct / max_down_pct) * base_budget
                base_buy_budget = min(base_buy_budget, left_base_budget)
                left_base_budget = left_base_budget - base_buy_budget
                last_base_buy_tick_time = i
                buy_reason = f"价格下跌({down_base_pct*100:.2f}%)触发基准买入"
                buy_action = True
                
            # 信号买入逻辑
            if price_diff >= 0.01 and remaining_budget > 0:
                buy_pct = price_diff * 100 / strategy_name_to_max_down_pct[strategy_name]
                buy_total_budget = buy_pct * total_budget
                
                if buy_pct > 1/4 or buy_total_budget > 20000:
                    # 执行买入
                    remaining_budget -= buy_total_budget
                    reference_price = raw_price
                    buy_reason = f"信号买入({signal['type']}, 强度:{signal['strength']:.4f})"
                    buy_action = True
            
            if buy_total_budget + base_buy_budget > 0:
                total_buy_amount = buy_total_budget + base_buy_budget
                buy_points.append((i, raw_price, total_buy_amount, signal['strength'] if signal else 0, buy_reason))
                
                # 记录买入日志
                logger.info(f"Tick {i:4d} - 买入操作: {buy_reason}")
                logger.info(f"    价格: {raw_price:.4f}, 金额: {total_buy_amount:.2f} "
                          f"(信号部分: {buy_total_budget:.2f}, 基准部分: {base_buy_budget:.2f})")
                logger.info(f"    剩余总预算: {remaining_budget:.2f}, 剩余基准预算: {left_base_budget:.2f}")
                
                tick_info['action'] = 'BUY'
                tick_info['action_reason'] = buy_reason
                tick_info['action_amount'] = total_buy_amount
                
        # 其他买入逻辑
        elif (raw_price - down_price) / base_price < 0.01 and left_base_budget > 0 and raw_price <= base_price and i <= 410:
            base_buy_budget = left_base_budget
            left_base_budget = 0
            buy_points.append((i, raw_price, base_buy_budget, 0, "触及下跌价格线"))
            last_base_buy_tick_time = i
            buy_action = True
            
            logger.info(f"Tick {i:4d} - 买入操作: 触及下跌价格线({down_price:.4f})")
            logger.info(f"    价格: {raw_price:.4f}, 金额: {base_buy_budget:.2f}")
            logger.info(f"    剩余基准预算: {left_base_budget:.2f}")
            
            tick_info['action'] = 'BUY'
            tick_info['action_reason'] = "触及下跌价格线"
            tick_info['action_amount'] = base_buy_budget
            
        elif raw_price < base_price and i - last_base_buy_tick_time > 100 and left_base_budget > 0 and i <= 410:
            base_buy_budget = min(left_base_budget, base_budget * 1/3)
            left_base_budget = left_base_budget - base_buy_budget
            buy_points.append((i, raw_price, base_buy_budget, 0, "长时间未买入"))
            last_base_buy_tick_time = i
            buy_action = True
            
            logger.info(f"Tick {i:4d} - 买入操作: 长时间未买入(超过100 ticks)")
            logger.info(f"    价格: {raw_price:.4f}, 金额: {base_buy_budget:.2f}")
            logger.info(f"    剩余基准预算: {left_base_budget:.2f}")
            
            tick_info['action'] = 'BUY'
            tick_info['action_reason'] = "长时间未买入"
            tick_info['action_amount'] = base_buy_budget
            
        elif i > 200 and raw_price < base_price and left_base_budget > 0 and i <= 410:
            base_buy_budget = left_base_budget
            left_base_budget = 0
            buy_points.append((i, raw_price, base_buy_budget, 0, "尾盘买入"))
            last_base_buy_tick_time = i
            buy_action = True
            
            logger.info(f"Tick {i:4d} - 买入操作: 尾盘买入(超过200 ticks)")
            logger.info(f"    价格: {raw_price:.4f}, 金额: {base_buy_budget:.2f}")
            logger.info(f"    剩余基准预算: {left_base_budget:.2f}")
            
            tick_info['action'] = 'BUY'
            tick_info['action_reason'] = "尾盘买入"
            tick_info['action_amount'] = base_buy_budget
        
        # 记录tick日志
        tick_info.update({
            'smooth_price': smooth_price,
            'remaining_budget_after': remaining_budget,
            'left_base_budget_after': left_base_budget,
            'reference_price_after': reference_price
        })
        
        tick_logs.append(tick_info)
        
        # 详细tick日志（每10个tick或当有操作时）
        if buy_action or i % 10 == 0:
            logger.debug(f"Tick {i:4d} - 价格: {raw_price:.4f} (平滑: {smooth_price:.4f}), "
                       f"成交量: {volume}, 预算: {remaining_budget:.2f}/{left_base_budget:.2f}")

    # 计算平均成本
    if buy_points:
        total_value = sum(price * amount for _, price, amount, _, _ in buy_points)
        total_amount = sum(amount for _, _, amount, _, _ in buy_points)
        if total_amount <= 0:
            raise ValueError(f"总金额必须大于0 {buy_points} {strategy_name}")
        amount_use_pct = total_amount / (base_budget + total_budget)
        avg_cost = total_value / total_amount
    else:
        avg_cost = base_price
        amount_use_pct = 0
    
    # 计算成本差距
    gap_ratio = (avg_cost - min_price) / min_price
    
    # 记录最终结果
    logger.info(f"\n{'='*80}")
    logger.info(f"回测结果: 股票 {stock_code}, 日期 {datekey}")
    logger.info(f"平均成本: {avg_cost:.4f}, 最低价: {min_price:.4f}, 差距比率: {gap_ratio:.4f}")
    logger.info(f"买入次数: {len(buy_points)}, 预算使用率: {amount_use_pct*100:.2f}%")
    logger.info(f"剩余总预算: {remaining_budget:.2f}, 剩余基准预算: {left_base_budget:.2f}")
    
    # 记录买入点详情
    logger.info("\n买入点详情:")
    for idx, (tick, price, amount, strength, reason) in enumerate(buy_points):
        logger.info(f"#{idx+1} - Tick {tick}: 价格={price:.4f}, 金额={amount:.2f}, "
                   f"强度={strength:.4f}, 原因={reason}")
    
    # 保存详细日志到CSV
    df_logs = pd.DataFrame(tick_logs)
    df_logs.to_csv(f"{output_dir}/{stock_code}_{datekey}_tick_logs.csv", index=False)
    
    # 绘制价格曲线
    plt.figure(figsize=(15, 8))
    
    # 原始价格和平滑价格
    plt.plot(raw_prices, label='原始价格', alpha=0.7, linewidth=1)
    plt.plot(smooth_prices, label='平滑价格', alpha=0.9, linewidth=1.5)
    
    # 标记买入点
    buy_ticks = [point[0] for point in buy_points]
    buy_prices = [point[1] for point in buy_points]
    plt.scatter(buy_ticks, buy_prices, color='red', s=50, zorder=5, label='买入点')
    
    # 添加文本标注
    for i, (tick, price, amount, _, reason) in enumerate(buy_points):
        plt.annotate(f"#{i+1}: {reason}\n${price:.2f}", 
                    (tick, price),
                    textcoords="offset points", 
                    xytext=(0,10),
                    ha='center',
                    fontsize=8)
    
    # 添加参考线
    plt.axhline(y=base_price, color='green', linestyle='--', alpha=0.5, label='基准价格')
    plt.axhline(y=down_price, color='purple', linestyle='--', alpha=0.5, label='下跌价格线')
    plt.axhline(y=min_price, color='blue', linestyle='--', alpha=0.5, label='最低价格')
    
    plt.title(f"价格走势 - {stock_code} ({datekey})")
    plt.xlabel("Tick")
    plt.ylabel("价格")
    plt.legend()
    plt.grid(True, alpha=0.3)
    
    # 保存图像
    plt.savefig(f"{output_dir}/{stock_code}_{datekey}_price_chart.png", dpi=150)
    plt.close()
    
    logger.info(f"结果和图表已保存到: {output_dir}")
    
    return avg_cost, min_price, gap_ratio, len(buy_points), amount_use_pct, stock_code, datekey


def backtest_single_stock(stock_data, strategy_name, params):

    """
    单只股票回测
    :param stock_data: dict - {base_price, budget, prices, volumes}
    :param params: dict - 策略参数
    :return: (avg_cost, min_price, gap_ratio)
    """
    base_price = stock_data['base_price']
    total_budget = stock_data['budget']
    base_budget = stock_data['base_budget']
    down_price = stock_data['down_price']
    prices = stock_data['prices']
    volumes = stock_data['volumes']
    last_close_price = stock_data['last_close_price']
    datekey = stock_data['datekey']
    stock_code = stock_data['stock_code']
    
    # 计算实际最低价（修正：使用传入数据中的最低价）
    min_price = min(prices)
    if min_price <= 0:
        raise ValueError(f"最低价必须大于0 {min_price} {strategy_name}")
    max_down_pct = (base_price - down_price) / base_price
    
    # 初始化组件
    filter = TripleFilter(
        ema_alpha=params['ema_alpha'],
        kalman_q=params['kalman_q'],
        kalman_r=params['kalman_r'],
        sg_window=params['sg_window']
    )
    
    detector = SignalDetector(
        macd_fast=params['macd_fast'],
        macd_slow_ratio=params['macd_slow_ratio'],
        macd_signal=params['macd_signal'],
        ema_fast=params['ema_fast'],
        ema_slow_ratio=params['ema_slow_ratio'],
        volume_window=params['volume_window'],
        price_confirm_ticks=params['price_confirm_ticks'],
        strength_confirm_ticks=params['strength_confirm_ticks'],
        strength_threshold=params['strength_threshold'],
        use_price_confirm=params['use_price_confirm'],
        use_strength_confirm=params['use_strength_confirm'],
        dead_cross_threshold=params.get('dead_cross_threshold', 0.3),
        price_drop_threshold=params.get('price_drop_threshold', 0.005),
        max_confirm_ticks=params.get('max_confirm_ticks', 10),
        volume_weight=params['volume_weight'],
        debug=params.get('debug', False)
    )
    
    # 状态变量
    buy_points = []  # (价格, 金额, 信号强度)
    reference_price = base_price
    remaining_budget = total_budget
    left_base_budget = base_budget
    last_base_buy_tick_time = 0
    
    # 处理每个tick
    for i, (raw_price, volume) in enumerate(zip(prices, volumes)):
        
        # 平滑价格
        smooth_price = filter.update(raw_price)
        
        # 检测信号
        signal = detector.update(smooth_price, volume)
        
        if signal:
            # 计算价格差异（相对于基准价）
            price_diff = (reference_price - raw_price) / base_price
            base_buy_budget = 0
            buy_total_budget = 0
            if (raw_price - down_price) / base_price < 0.01 and left_base_budget > 0:
                base_buy_budget = left_base_budget
                left_base_budget = 0
                last_base_buy_tick_time = i

            elif (base_price - raw_price) / base_price > 0.01 and left_base_budget > 0:
                down_base_pct = (base_price - raw_price) / base_price
                base_buy_budget = max(1/3, down_base_pct / max_down_pct) * base_budget
                base_buy_budget = min(base_buy_budget, left_base_budget)
                left_base_budget = left_base_budget - base_buy_budget
                last_base_buy_tick_time = i
                
            # 只有跌幅超过1%才买入
            if price_diff >= 0.005 and remaining_budget > 0:
                buy_pct = price_diff * 100 / strategy_name_to_max_down_pct[strategy_name]
                buy_amount = min(buy_pct * total_budget, remaining_budget)
                
                if buy_pct > 1/5 or buy_amount > 5000:
                    # 执行买入
                    buy_total_budget = buy_amount
                    # remaining_budget -= buy_amount
                    remaining_budget = max(0, remaining_budget - buy_amount)
                    
                    # 更新基准价格为当前买入价
                    reference_price = raw_price
                    
                    # 调试输出
                    if params.get('debug', False):
                        logger.info(f"买入点: 价格={raw_price:.4f}, "
                                   f"金额={buy_amount:.2f}, "
                                   f"强度={signal['strength']:.4f}")
            if buy_total_budget + base_buy_budget > 0:
                buy_points.append((raw_price, buy_total_budget + base_buy_budget, signal['strength']))
        elif (raw_price - down_price) / base_price < 0.01 and left_base_budget > 0 and raw_price <= base_price :
            base_buy_budget = left_base_budget
            left_base_budget = 0
            buy_points.append((raw_price, base_buy_budget, 0))
            last_base_buy_tick_time = i
        elif raw_price < base_price * 0.992 and (i - last_base_buy_tick_time >= 100 or last_base_buy_tick_time == 0) and left_base_budget > 0:
            base_buy_budget = min(left_base_budget, base_budget * 1/3)
            left_base_budget = left_base_budget - base_buy_budget
            buy_points.append((raw_price, base_buy_budget, 0))
            last_base_buy_tick_time = i
        elif i > 200 and raw_price < base_price * 0.992 and left_base_budget > 0:
            base_buy_budget = left_base_budget
            left_base_budget = 0
            buy_points.append((raw_price, base_buy_budget, 0))
            last_base_buy_tick_time = i

    # 计算平均成本
    if buy_points:
        total_value = sum(price * amount for price, amount, _ in buy_points)
        total_amount = sum(amount for _, amount, _ in buy_points)
        if total_amount <= 0:
            raise ValueError(f"总金额必须大于0 {buy_points} {strategy_name}")
        amount_use_pct = total_amount / (base_budget + total_budget)
        avg_cost = total_value / total_amount
    else:
        avg_cost = base_price
        amount_use_pct = 0
    
    # 计算成本差距
    gap_ratio = (avg_cost - min_price) / min_price
    
    return avg_cost, min_price, gap_ratio, len(buy_points), amount_use_pct, stock_code, datekey

def genetic_algorithm_optimization(stocks_data, param_ranges, strategy_name,
                                  population_size=30, generations=1200,
                                  crossover_rate=0.85, mutation_rate=0.15,
                                  elite_size=5, debug=False):
    """
    遗传算法参数优化
    :param stocks_data: list of dict - 股票数据集
    :param param_ranges: dict - 参数范围 {param_name: (min, max)}
    :param population_size: int - 种群大小
    :param generations: int - 迭代代数
    :param crossover_rate: float - 交叉概率
    :param mutation_rate: float - 变异概率
    :param elite_size: int - 精英保留数量
    :return: (best_params, best_score, history)
    """
    
    logger.info(f"开始优化策略: {strategy_name}")
    logger.info(f"参数范围: {param_ranges}")
    logger.info(f"种群大小: {population_size}, 代数: {generations}")
    # 需要取整的参数列表
    int_params = ['sg_window', 'macd_fast', 'macd_signal', 'ema_fast', 'volume_window', 
                 'price_confirm_ticks', 'strength_confirm_ticks', 'max_confirm_ticks']
    
    # 布尔参数列表（0或1）
    bool_params = ['use_price_confirm', 'use_strength_confirm']
    
    # 初始化种群
    population = []
    for _ in range(population_size):
        individual = {}
        for param, (min_val, max_val) in param_ranges.items():
            if param in bool_params:
                # 布尔参数：随机选择0或1
                individual[param] = random.choice([True, False])
            else:
                value = random.uniform(min_val, max_val)
                # 对整数参数进行取整
                if param in int_params:
                    value = int(round(value))
                individual[param] = value
        population.append(individual)
    
    if len(stocks_data) > 300:
        selected_data = random.sample(stocks_data, 300)
        print(f"策略 {strategy_name}: 从 {len(stocks_data)} 只股票中随机选择 300 只进行评估")
    else:
        selected_data = stocks_data
        print(f"策略 {strategy_name}: 使用全部 {len(stocks_data)} 只股票进行评估")
    
    # 评估初始种群 - 修改：同时存储avg_gap和avg_amount_use_pct
    fitness_scores = []
    avg_gaps = []  # 新增：存储平均价差
    avg_amount_use_pcts = []  # 新增：存储平均仓位使用率
    
    for individual in population:
        individual['debug'] = debug
        try:
            score, avg_gap, avg_amount_use_pct = evaluate_params(selected_data, strategy_name, individual)
            fitness_scores.append(score)
            avg_gaps.append(avg_gap)  # 存储avg_gap
            avg_amount_use_pcts.append(avg_amount_use_pct)  # 存储avg_amount_use_pct
        except Exception as e:
            
            logger.error(f"评估失败: {e}")
            fitness_scores.append(float('inf'))
            avg_gaps.append(float('inf'))  # 添加默认值
            avg_amount_use_pcts.append(float('inf'))  # 添加默认值
    
    # 找到当前最佳个体
    best_idx = np.argmin(fitness_scores)
    best_params = population[best_idx].copy()
    best_score = fitness_scores[best_idx]
    best_avg_gap = avg_gaps[best_idx]  # 新增：最佳个体的avg_gap
    best_avg_amount_use_pct = avg_amount_use_pcts[best_idx]  # 新增：最佳个体的avg_amount_use_pct
    
    # 历史记录 - 新增字段
    history = {
        'generation': [],
        'best_score': [],
        'best_avg_gap': [],  # 新增：记录每代最佳avg_gap
        'best_avg_amount_use_pct': [],  # 新增：记录每代最佳仓位使用率
        'avg_score': [],
        'params': []
    }
    
    # 记录第一代（0代）结果
    history['generation'].append(0)
    history['best_score'].append(best_score)
    history['best_avg_gap'].append(best_avg_gap)  # 新增
    history['best_avg_amount_use_pct'].append(best_avg_amount_use_pct)  # 新增
    history['avg_score'].append(np.mean(fitness_scores))
    history['params'].append(best_params.copy())
    
    output_dir = f"optimization_results/{strategy_name}"
    os.makedirs(output_dir, exist_ok=True)
    
    # 保存初始状态
    save_intermediate_result(strategy_name, 0, best_params, best_score, output_dir)
    
    # 打印初始状态
    print(
        f"{strategy_name} - 初始状态: "
        f"最佳得分={best_score:.6f}, "
        f"平均价差={best_avg_gap:.6f}, "
        f"平均仓位使用率={best_avg_amount_use_pct:.6f}"
    )
    
    # 遗传算法主循环
    for gen in range(1, generations + 1):
        # 选择操作 - 锦标赛选择
        selected_parents = []
        for _ in range(population_size):
            # 随机选择3个个体进行锦标赛
            tournament = random.sample(range(population_size), 3)
            tournament_scores = [fitness_scores[i] for i in tournament]
            winner_idx = tournament[np.argmin(tournament_scores)]
            selected_parents.append(population[winner_idx])
        
        # 交叉操作
        new_population = []
        for i in range(0, population_size, 2):
            parent1 = selected_parents[i]
            parent2 = selected_parents[i + 1] if i + 1 < population_size else selected_parents[0]
            
            child1 = parent1.copy()
            child2 = parent2.copy()
            
            # 以一定概率进行交叉
            if random.random() < crossover_rate:
                for param in param_ranges.keys():
                    if param in bool_params:
                        # 布尔参数：50%概率交换
                        if random.random() < 0.5:
                            child1[param], child2[param] = child2[param], child1[param]
                    else:
                        # 数值参数：均匀交叉
                        if random.random() < 0.5:
                            child1[param], child2[param] = child2[param], child1[param]
            
            new_population.append(child1)
            if len(new_population) < population_size:
                new_population.append(child2)
        
        # 变异操作
        for individual in new_population:
            for param in param_ranges.keys():
                if random.random() < mutation_rate:
                    if param in bool_params:
                        # 布尔参数：翻转值
                        individual[param] = not individual[param]
                    else:
                        min_val, max_val = param_ranges[param]
                        # 高斯变异
                        mutation = random.gauss(0, (max_val - min_val) * 0.2)
                        new_val = individual[param] + mutation
                        
                        # 确保参数在范围内
                        new_val = max(min_val, min(max_val, new_val))
                        
                        # 对整数参数进行取整
                        if param in int_params:
                            new_val = int(round(new_val))
                        
                        individual[param] = new_val
        
        # 精英保留
        sorted_population = sorted(zip(fitness_scores, population), key=lambda x: x[0])
        elite = [ind for _, ind in sorted_population[:elite_size]]
        
        # 替换种群
        population = elite + new_population[:population_size - elite_size]
        
        # 评估新种群 - 修改：同时存储avg_gap和avg_amount_use_pct
        fitness_scores = []
        avg_gaps = []  # 重置
        avg_amount_use_pcts = []  # 重置
        
        for individual in population:
            individual['debug'] = debug
            try:
                score, avg_gap, avg_amount_use_pct = evaluate_params(selected_data, strategy_name, individual)
                fitness_scores.append(score)
                avg_gaps.append(avg_gap)
                avg_amount_use_pcts.append(avg_amount_use_pct)
            except Exception as e:
                logger.error(f"评估失败: {e}")
                fitness_scores.append(float('inf'))
                avg_gaps.append(float('inf'))
                avg_amount_use_pcts.append(float('inf'))
        
        # 更新最佳个体
        current_best_idx = np.argmin(fitness_scores)
        current_best_score = fitness_scores[current_best_idx]
        current_avg_gap = avg_gaps[current_best_idx]  # 当前代最佳avg_gap
        current_avg_amount_use_pct = avg_amount_use_pcts[current_best_idx]  # 当前代最佳仓位使用率
        
        # 如果当前代有更好的个体，更新全局最佳
        if current_best_score < best_score:
            best_params = population[current_best_idx].copy()
            best_score = current_best_score
            best_avg_gap = current_avg_gap
            best_avg_amount_use_pct = current_avg_amount_use_pct
        
        # 记录历史
        history['generation'].append(gen)
        history['best_score'].append(best_score)
        history['best_avg_gap'].append(best_avg_gap)  # 新增
        history['best_avg_amount_use_pct'].append(best_avg_amount_use_pct)  # 新增
        history['avg_score'].append(np.mean(fitness_scores))
        history['params'].append(best_params.copy())

        # 打印进度到终端 - 修改：添加avg_gap和avg_amount_use_pct
        print(
            f"{strategy_name} - 第 {gen}/{generations} 代: "
            f"最佳得分={best_score:.6f}, "
            f"平均价差={best_avg_gap:.6f}, "
            f"平均仓位使用率={best_avg_amount_use_pct:.6f}, "
            f"平均得分={np.mean(fitness_scores):.6f}"
        )

        if gen % 10 == 0:
            logger.info(
                f"策略 [{strategy_name}] 第 {gen}/{generations} 代 - "
                f"最佳得分: {best_score:.6f} - "
                f"平均价差: {best_avg_gap:.6f} - "
                f"平均仓位使用率: {best_avg_amount_use_pct:.6f} - "
                f"平均得分: {np.mean(fitness_scores):.6f}"
            )
            
            # 保存中间结果
            if gen % 10 == 0:
                save_intermediate_result(strategy_name, gen, best_params, best_score, output_dir)
                logger.info(f"已保存中间结果: {output_dir}")
    
    # 最终结果打印
    logger.info(
        f"策略 [{strategy_name}] 优化完成! "
        f"最佳得分: {best_score:.6f} - "
        f"平均价差: {best_avg_gap:.6f} - "
        f"平均仓位使用率: {best_avg_amount_use_pct:.6f}"
    )
    
    return best_params, best_score, history

# def genetic_algorithm_optimization(stocks_data, param_ranges, strategy_name,
#                                   population_size=30, generations=1200,
#                                   crossover_rate=0.85, mutation_rate=0.15,
#                                   elite_size=5, debug=False):
#     """
#     遗传算法参数优化
#     :param stocks_data: list of dict - 股票数据集
#     :param param_ranges: dict - 参数范围 {param_name: (min, max)}
#     :param population_size: int - 种群大小
#     :param generations: int - 迭代代数
#     :param crossover_rate: float - 交叉概率
#     :param mutation_rate: float - 变异概率
#     :param elite_size: int - 精英保留数量
#     :return: (best_params, best_score, history)
#     """
    
#     logger.info(f"开始优化策略: {strategy_name}")
#     logger.info(f"参数范围: {param_ranges}")
#     logger.info(f"种群大小: {population_size}, 代数: {generations}")
#     # 需要取整的参数列表
#     int_params = ['sg_window', 'macd_fast', 'macd_signal', 'ema_fast', 'volume_window', 
#                  'price_confirm_ticks', 'strength_confirm_ticks', 'max_confirm_ticks']
    
#     # 布尔参数列表（0或1）
#     bool_params = ['use_price_confirm', 'use_strength_confirm']
    
#     # 初始化种群
#     population = []
#     for _ in range(population_size):
#         individual = {}
#         for param, (min_val, max_val) in param_ranges.items():
#             if param in bool_params:
#                 # 布尔参数：随机选择0或1
#                 individual[param] = random.choice([True, False])
#             else:
#                 value = random.uniform(min_val, max_val)
#                 # 对整数参数进行取整
#                 if param in int_params:
#                     value = int(round(value))
#                 individual[param] = value
#         population.append(individual)
    
#     # 评估初始种群
#     fitness_scores = []
#     for individual in population:
#         individual['debug'] = debug
#         try:
#             score, avg_gap, avg_amount_use_pct = evaluate_params(stocks_data, strategy_name, individual)
#             fitness_scores.append(score)
#         except Exception as e:
#             logger.error(f"评估失败: {e}")
#             fitness_scores.append(float('inf'))
    
#     # 找到当前最佳个体
#     best_idx = np.argmin(fitness_scores)
#     best_params = population[best_idx].copy()
#     best_score = fitness_scores[best_idx]
    
#     # 历史记录
#     history = {
#         'generation': [],
#         'best_score': [],
#         'avg_score': [],
#         'params': []
#     }
    
#     # 记录每一代的最佳分数
#     history['generation'].append(0)
#     history['best_score'].append(best_score)
#     history['avg_score'].append(np.mean(fitness_scores))
#     history['params'].append(best_params.copy())
#     output_dir = f"optimization_results/{strategy_name}"
#     os.makedirs(output_dir, exist_ok=True)
    
#     # 保存初始状态
#     save_intermediate_result(strategy_name, 0, best_params, best_score, output_dir)
#     # 遗传算法主循环
#     for gen in range(1, generations + 1):
#         # 选择操作 - 锦标赛选择
#         selected_parents = []
#         for _ in range(population_size):
#             # 随机选择3个个体进行锦标赛
#             tournament = random.sample(range(population_size), 3)
#             tournament_scores = [fitness_scores[i] for i in tournament]
#             winner_idx = tournament[np.argmin(tournament_scores)]
#             selected_parents.append(population[winner_idx])
        
#         # 交叉操作
#         new_population = []
#         for i in range(0, population_size, 2):
#             parent1 = selected_parents[i]
#             parent2 = selected_parents[i + 1] if i + 1 < population_size else selected_parents[0]
            
#             child1 = parent1.copy()
#             child2 = parent2.copy()
            
#             # 以一定概率进行交叉
#             if random.random() < crossover_rate:
#                 for param in param_ranges.keys():
#                     if param in bool_params:
#                         # 布尔参数：50%概率交换
#                         if random.random() < 0.5:
#                             child1[param], child2[param] = child2[param], child1[param]
#                     else:
#                         # 数值参数：均匀交叉
#                         if random.random() < 0.5:
#                             child1[param], child2[param] = child2[param], child1[param]
            
#             new_population.append(child1)
#             if len(new_population) < population_size:
#                 new_population.append(child2)
        
#         # 变异操作
#         for individual in new_population:
#             for param in param_ranges.keys():
#                 if random.random() < mutation_rate:
#                     if param in bool_params:
#                         # 布尔参数：翻转值
#                         individual[param] = not individual[param]
#                     else:
#                         min_val, max_val = param_ranges[param]
#                         # 高斯变异
#                         mutation = random.gauss(0, (max_val - min_val) * 0.2)
#                         new_val = individual[param] + mutation
                        
#                         # 确保参数在范围内
#                         new_val = max(min_val, min(max_val, new_val))
                        
#                         # 对整数参数进行取整
#                         if param in int_params:
#                             new_val = int(round(new_val))
                        
#                         individual[param] = new_val
#         # if gen % 10 == 0:
#         #     logger.info(
#         #         f"策略 [{strategy_name}] 第 {gen}/{generations} 代 - "
#         #         f"最佳得分: {best_score:.6f} - "
#         #         f"平均得分: {np.mean(fitness_scores):.6f}"
#         #     )
            
#         #     # 保存中间结果
#         #     if gen % 30 == 0:
#         #         save_intermediate_result(strategy_name, gen, best_params, best_score, output_dir)
#         #         logger.info(f"已保存中间结果: {output_dir}")
        
        
#         # 精英保留
#         sorted_population = sorted(zip(fitness_scores, population), key=lambda x: x[0])
#         elite = [ind for _, ind in sorted_population[:elite_size]]
        
#         # 替换种群
#         population = elite + new_population[:population_size - elite_size]
        
#         # 评估新种群
#         fitness_scores = []
#         for individual in population:
#             individual['debug'] = debug
#             try:
#                 score, avg_gap, avg_amount_use_pct = evaluate_params(stocks_data, strategy_name, individual)
#                 fitness_scores.append(score)
#             except Exception as e:
#                 logger.error(f"评估失败: {e}")
#                 fitness_scores.append(float('inf'))
        
#         # 更新最佳个体
#         current_best_idx = np.argmin(fitness_scores)
#         current_best_score = fitness_scores[current_best_idx]
        
#         if current_best_score < best_score:
#             best_params = population[current_best_idx].copy()
#             best_score = current_best_score
        
#         # 记录历史
#         history['generation'].append(gen)
#         history['best_score'].append(best_score)
#         history['avg_score'].append(np.mean(fitness_scores))
#         history['params'].append(best_params.copy())

#         # 打印进度到终端
#         print(
#             f"{strategy_name} - 第 {gen}/{generations} 代: "
#             f"最佳得分={best_score:.6f}, "
#             f"平均得分={np.mean(fitness_scores):.6f}"
#         )

#         if gen % 10 == 0:
#             logger.info(
#                 f"策略 [{strategy_name}] 第 {gen}/{generations} 代 - "
#                 f"最佳得分: {best_score:.6f} - "
#                 f"平均得分: {np.mean(fitness_scores):.6f}"
#             )
            
#             # 保存中间结果
#             if gen % 30 == 0:
#                 save_intermediate_result(strategy_name, gen, best_params, best_score, output_dir)
#                 logger.info(f"已保存中间结果: {output_dir}")
#         # 打印进度
#         # print(f"Generation {gen}/{generations} - Best: {best_score:.6f} - Avg: {np.mean(fitness_scores):.6f}")
#     logger.info(f"策略 [{strategy_name}] 优化完成! 最佳得分: {best_score:.6f}")
#     return best_params, best_score, history



def save_intermediate_result(strategy_name, generation, best_params, best_score, output_dir):
    """保存中间结果"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result = {
        "strategy": strategy_name,
        "generation": generation,
        "best_score": best_score,
        "best_params": best_params,
        "timestamp": timestamp
    }
    
    filename = f"{output_dir}/intermediate_gen_{generation}_{timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:  # 添加 encoding='utf-8'
        json.dump(result, f, indent=4, ensure_ascii=False)  # 添加 ensure_ascii=False
    
    logger.info(f"{strategy_name} 已保存中间结果: {filename}")

def save_final_result(strategy_name, best_params, best_score, output_dir):
    """保存最终结果"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    result = {
        "strategy": strategy_name,
        "best_score": best_score,
        "best_params": best_params,
        "timestamp": timestamp
    }
    
    filename = f"{output_dir}/final_result_{timestamp}.json"
    with open(filename, 'w', encoding='utf-8') as f:  # 添加 encoding='utf-8'
        json.dump(result, f, indent=4, ensure_ascii=False)  # 添加 ensure_ascii=False
    
    logger.info(f"已保存最终结果: {filename}")


# def evaluate_params(stocks_data, strategy_name, params):

#     """
#     评估参数在股票数据集上的表现
#     :return: 平均成本差距比例
#     """
#     total_gap = 0
#     count = 0
    
#     # 如果股票数据太多，随机选择100个进行评估
#     if len(stocks_data) > 150:
#         selected_data = random.sample(stocks_data, 150)
#     else:
#         selected_data = stocks_data
    
#     for stock_data in selected_data:
#         try:
#             _, _, gap_ratio, _ = backtest_single_stock(stock_data, strategy_name, params)
#             total_gap += gap_ratio
#             count += 1
#         except Exception as e:
#             logger.error(f"回测失败: {e}")
#             logger.error(f"错误堆栈信息:\n{traceback.format_exc()}")
#             # 返回一个很大的值表示无效参数
#             return float('inf')
    
#     return total_gap / count if count > 0 else float('inf')

def evaluate_params(stocks_data, strategy_name, params):
    """
    评估参数在股票数据集上的表现
    :return: 平均成本差距比例
    """
    total_gap = 0
    count = 0
    
    # # 如果股票数据太多，随机选择150个进行评估
    # if len(stocks_data) > 150:
    #     selected_data = random.sample(stocks_data, 150)
    #     print(f"策略 {strategy_name}: 从 {len(stocks_data)} 只股票中随机选择 150 只进行评估")
    # else:
    #     selected_data = stocks_data
    #     print(f"策略 {strategy_name}: 使用全部 {len(stocks_data)} 只股票进行评估")
    selected_data = stocks_data
    # 创建进度条
    progress_bar = tqdm(
        total=len(selected_data),
        desc=f"策略 {strategy_name} 参数评估",
        bar_format="{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}]"
    )
    # 存储失败的回测信息
    failed_tests = []
    total_amount_use_pct = 0
    max_amount_use_pct = 0
    min_amount_use_pct = 1
    max_amount_use_code = ''
    min_amount_use_code = ''
    max_amount_use_datekey = ''
    min_amount_use_datekey = ''
    for idx, stock_data in enumerate(selected_data):
        progress_bar.set_postfix_str(f"当前: {idx+1}/{len(selected_data)}")
        
        try:
            _, _, gap_ratio, buy_count, amount_use_pct, stock_code, datekey = backtest_single_stock(stock_data, strategy_name, params)
            if amount_use_pct > max_amount_use_pct:
                max_amount_use_pct = amount_use_pct
                max_amount_use_code = stock_code
                max_amount_use_datekey = datekey
            if amount_use_pct < min_amount_use_pct:
                min_amount_use_pct = amount_use_pct
                min_amount_use_code = stock_code
                min_amount_use_datekey = datekey
            total_amount_use_pct += amount_use_pct
            total_gap += gap_ratio
            count += 1
            stock_code = stock_data.get('stock_code', '未知')
            # 显示当前股票的回测结果
            # progress_bar.write(f"  股票 {stock_code}: 成本差距={gap_ratio:.4f}, 买入点={buy_count}个")
            
        except Exception as e:
            error_msg = f"回测失败: {str(e)}"
            progress_bar.write(f"【错误】{error_msg}")
            progress_bar.write(f"【堆栈跟踪】{traceback.format_exc()}")
            failed_tests.append({
                "stock": stock_data.get('stock_code', '未知'),
                "date": stock_data.get('datekey', '未知'),
                "error": error_msg,
                "traceback": traceback.format_exc()
            })
    
    # 关闭进度条
    progress_bar.close()
    
    # 打印失败统计
    if failed_tests:
        print(f"策略 {strategy_name}: 回测失败统计 ({len(failed_tests)} 次失败):")
        for i, fail in enumerate(failed_tests[:5]):  # 最多显示前5个错误
            print(f"  失败 {i+1}: 股票={fail['stock']}, 日期={fail['date']}")
            print(f"      错误: {fail['error']}")
        if len(failed_tests) > 5:
            print(f"  还有 {len(failed_tests)-5} 个失败未显示...")
    
    # 计算平均差距
    if count > 0:
        avg_gap = total_gap / count
        avg_amount_use_pct = total_amount_use_pct / count
        print(f"策略 {strategy_name}: 参数评估完成, 平均成本差距={avg_gap:.6f}, 成功回测={count}/{len(selected_data)}, 平均使用资金比例={avg_amount_use_pct:.6f}, 最大使用资金比例={max_amount_use_pct:.6f}, 最大使用资金股票={max_amount_use_code}, 最大使用资金日期={max_amount_use_datekey}, 最小使用资金比例={min_amount_use_pct:.6f}, 最小使用资金股票={min_amount_use_code}, 最小使用资金日期={min_amount_use_datekey}")
        return avg_gap / (avg_amount_use_pct + 1e-6), avg_gap, avg_amount_use_pct
    else:
        print(f"策略 {strategy_name}: 所有回测均失败, 返回无限大值")
        return float('inf')


def build_all_stock_datas(strategy_name, min_num=3):
    # 获取股票列表
    all_stocks = {}
    all_stocks_info = xtdata.get_stock_list_in_sector('沪深A股')
    for stock in all_stocks_info:
        if stock.startswith('60') or stock.startswith('00'):
            cde = stock.split('.')[0]
            all_stocks[cde] = stock

    # 定义查询月份
    months = ['202409', '202410', '202411', '202412', '202501', '202502', 
              '202503', '202504', '202505', '202506', '202507', '202508']

    
    # 从数据库合并数据
    combined_df = pd.DataFrame()
    for month in months:
        conn = sqlite3.connect('D:\workspace\TradeX\ezMoney\sqlite_db\strategy_data.db')
        db_name = 'strategy_data_aftermarket_%s' % month
        query = "SELECT * FROM %s WHERE (sub_strategy_name = '%s') AND stock_rank <= %s" % (
            db_name, strategy_name, min_num)
        df = pd.read_sql_query(query, conn)
        combined_df = pd.concat([combined_df, df], ignore_index=True)
        conn.close()
    
    # 准备下载任务
    tasks = []
    if 'date_key' in combined_df.columns and 'stock_code' in combined_df.columns:
        for _, row in combined_df.iterrows():
            code_part = row['stock_code'].split('.')[0]
            if code_part in all_stocks:
                converted_stock_code = all_stocks[code_part]
                tasks.append((row['date_key'], converted_stock_code))
    else:
        print("combined_df 中缺少 date_key 或 stock_code 列")
        return []

    # 多线程下载
    print(f"开始下载股票数据，共 {len(tasks)} 个任务...")
    results = []
    
    # 使用线程池执行任务
    with concurrent.futures.ThreadPoolExecutor() as executor:
        # 提交所有任务
        future_to_task = {
            executor.submit(build_stock_datas, stock_code, datekey): (datekey, stock_code)
            for datekey, stock_code in tasks
        }
        
        # 创建进度条
        with tqdm(total=len(tasks), desc="下载进度", unit="task") as pbar:
            for future in concurrent.futures.as_completed(future_to_task):
                datekey, stock_code = future_to_task[future]
                try:
                    data = future.result()
                    if data:
                        results.append(data)
                except Exception as e:
                    print(f"\n下载失败 [{datekey} {stock_code}]: {str(e)}")
                finally:
                    pbar.update(1)  # 更新进度条
                    pbar.set_postfix_str(f"最新: {stock_code}")

    print(f"\n所有股票数据下载完成！成功下载 {len(results)}/{len(tasks)} 个数据")
    return results

def build_stock_datas(stock_code, datekey):
    # from xtquant import xtdata
    # xtdata.connect(port=58611)
    import numpy as np
    if '-' in datekey:
        n_data_key = datekey.replace('-', '')
    else:
        n_data_key = datekey
    xtdata.download_history_data(stock_code, 'tick', n_data_key, n_data_key)
    all_tick_data = xtdata.get_market_data(stock_list=[stock_code], period='tick', start_time=n_data_key, end_time=n_data_key)

    # 假设 all_tick_data['000759.SZ'] 是 numpy.void 数组
    if isinstance(all_tick_data[stock_code], np.ndarray) and all_tick_data[stock_code].dtype.type is np.void:
        df = pd.DataFrame(all_tick_data[stock_code].tolist(), columns=all_tick_data[stock_code].dtype.names)
    else:
        raise
    df['datetime'] = pd.to_datetime(df['time'], unit='ms').dt.tz_localize('UTC')
    # 将 UTC 时间转换为上海时间
    df['datetime'] = df['datetime'].dt.tz_convert('Asia/Shanghai')

    # 筛选出 9:30 之后的行
    time_930 = pd.to_datetime('09:30:00').time()
    filtered_df = df[df['datetime'].dt.time >= time_930]
    pre_volume = -1

    pre_930_df = df[df['datetime'].dt.time < time_930]
    if not pre_930_df.empty:
        last_row_pre_930 = pre_930_df.iloc[-1]
        pre_volume = last_row_pre_930.to_dict()['volume']

    else:
        print('last row error.')
        raise
    
    if pre_volume < 0:
        print('pre_volume error.')
        raise

    current_tick_steps = -1

    prices = []
    volumes = []
    limit_down_price = -1
    base_price = -1
    last_close_price = -1
    budget = 50000
    base_budget = 50000
    last_volume = pre_volume
    min_price = 100000
    for index, row in filtered_df.iterrows():
        current_tick_steps = current_tick_steps + 1
        if current_tick_steps > 405:
            break
        data = row.to_dict()
        timestamp = data['time']
        lastPrice = data['lastPrice']
        min_price = min(min_price, lastPrice)
        open = data['open']
        high = data['high']
        low = data['low']
        lastClose = data['lastClose']
        volume = data['volume']
        amount = data['amount']
        if amount <= 0 or volume <= 0:
            print(f"amount <= 0 or volume <= 0. error.")
            continue
        if lastPrice <= 0:
            print(f"lastPrice <= 0. {stock_code} {datekey}")
            continue
        if last_volume == -1:
            volumes.append(volume)
            last_volume = volume
        else:
            delta_volume = volume - last_volume
            if delta_volume < 0:
                print(f"delta_volume < 0. {stock_code} {datekey}")
                continue
            volumes.append(delta_volume)
            last_volume = volume
        
        if limit_down_price < 0:
            limit_down_price, _ = constants.get_limit_price(lastClose, stock_code)
        if current_tick_steps ==0:
            base_price = lastPrice
        if last_close_price < 0:
            last_close_price = lastClose
        prices.append(lastPrice)

    if min_price < base_price:

        return {
            'base_price': base_price,
            'budget': budget,
            'prices': prices,
            'base_budget': base_budget,
            'volumes': volumes,
            'down_price': limit_down_price,
            'last_close_price': last_close_price,
            'stock_code': stock_code,
            'datekey': datekey
        }
    else:
        return {}

# 修改运行策略优化函数
def run_strategy_optimization(strategy_name):
    """运行单个策略的优化过程"""
    try:
        logger.info(f"===== 开始优化策略: {strategy_name} =====")
        start_time = time.time()
        
        # 构建股票数据
        logger.info(f"为策略 {strategy_name} 构建股票数据...")
        stocks_data = build_all_stock_datas(strategy_name=strategy_name)
        logger.info(f"为策略 {strategy_name} 构建了 {len(stocks_data)} 个股票数据")
        
        # 定义参数范围
        param_ranges = {
            'ema_alpha': (0.03, 0.3),
            'kalman_q': (0.01, 0.05),
            'kalman_r': (0.02, 0.1),
            'sg_window': (7, 21),
            'macd_fast': (2, 12),
            'macd_slow_ratio': (1.2, 3),
            'macd_signal': (2, 15),
            'ema_fast': (2, 12),
            'ema_slow_ratio': (1.2, 3),
            'volume_window': (2, 14),
            'price_confirm_ticks': (1, 10),
            'strength_confirm_ticks': (1, 10),
            'strength_threshold': (0.3, 5),
            'volume_weight': (0.05, 1.0),
            'use_price_confirm': (True, False),  # 布尔值范围
            'use_strength_confirm': (True, False),  # 布尔值范围
            'dead_cross_threshold': (0, 0.05),
            'price_drop_threshold': (0.001, 0.02),
            'max_confirm_ticks': (1, 20)
        }
        
        # 运行优化
        best_params, best_score, history = genetic_algorithm_optimization(
            stocks_data, param_ranges, strategy_name,
            population_size=40,
            generations=300,
            crossover_rate=0.85,
            mutation_rate=0.25,
            elite_size=8,
            debug=False
        )
        
        # 打印和保存结果
        logger.info(f"策略 [{strategy_name}] 优化完成!")
        logger.info(f"最佳得分: {best_score:.6f}")
        logger.info("最佳参数:")
        for param, value in best_params.items():
            if param not in ['debug']:
                if isinstance(value, float):
                    logger.info(f"  {param}: {value:.4f}")
                elif isinstance(value, bool):
                    logger.info(f"  {param}: {'开启' if value else '关闭'}")
                else:
                    logger.info(f"  {param}: {value}")
        
        # 保存最终结果
        output_dir = f"optimization_results/{strategy_name}"
        save_final_result(strategy_name, best_params, best_score, output_dir)
        logger.info(f"最终结果已保存到: {output_dir}")
        
        # 保存优化过程图像
        save_optimization_plot(strategy_name, history, output_dir)
        
        # 计算并打印运行时间
        end_time = time.time()
        duration = end_time - start_time
        hours, rem = divmod(duration, 3600)
        minutes, seconds = divmod(rem, 60)
        logger.info(
            f"策略 {strategy_name} 优化完成, 耗时: "
            f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"
        )
        
        return True
    except Exception as e:
        logger.error(f"策略 {strategy_name} 优化过程中出错: {str(e)}", exc_info=True)
        return False



def save_optimization_plot(strategy_name, history, output_dir):
    """保存优化过程图像"""
    plt.figure(figsize=(12, 6))
    plt.plot(history['generation'], history['best_score'], 'b-', label='Best Score')
    plt.plot(history['generation'], history['avg_score'], 'r--', label='Average Score')
    plt.xlabel('Generation')
    plt.ylabel('Cost Gap Ratio')
    plt.title(f'Genetic Algorithm Optimization Progress - {strategy_name}')
    plt.legend()
    plt.grid(True)
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{output_dir}/optimization_plot_{strategy_name}_{timestamp}.png"
    plt.savefig(filename)
    plt.close()
    
    logger.info(f"已保存优化过程图像: {filename}")


# 修改主函数
if __name__ == "__main__":
    # 主进程日志配置
    
    logger.info("===== 策略优化程序启动 =====")
    logger.info(f"开始时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 创建结果目录
    os.makedirs("optimization_results", exist_ok=True)
    logger.info("创建优化结果目录")
    
    from xtquant import xtdatacenter as xtdc
    xtdc.set_token("26e6009f4de3bfb2ae4b89763f255300e96d6912")

    print('xtdc.init')
    xtdc.init() # 初始化行情模块，加载合约数据，会需要大约十几秒的时间
    print('done')
    listen_addr = xtdc.listen(port = 58611)
    print(f'done, listen_addr:{listen_addr}')

    strategy_names = [
        '高强中低开低吸', '低位高强低吸', '低位中强中低开低吸', 
        '中强中低开低吸', '首红断低吸', '低位高强中低开低吸', '低位孕线低吸',
        '一进二弱转强',
        '高位高强追涨',
    ]

    # strategy_names = [
    #     '一进二弱转强',
    #     '高位高强追涨',
    # ]
    
    import concurrent.futures

    from concurrent.futures import ProcessPoolExecutor
    results = {}
    
    with ProcessPoolExecutor(max_workers=10, initializer=init_process) as executor:
        futures = {}
        for strategy_name in strategy_names:
            logger.info(f"提交策略优化任务: {strategy_name}")
            future = executor.submit(run_strategy_optimization, strategy_name)
            futures[future] = strategy_name
            time.sleep(2)  # 稍微延迟避免资源冲突
        
        # 等待所有任务完成并收集结果
        for future in concurrent.futures.as_completed(futures):
            strategy_name = futures[future]
            try:
                status = future.result()
                results[strategy_name] = "成功" if status else "失败"
                logger.info(f"策略 {strategy_name} 优化任务完成, 状态: {results[strategy_name]}")
            except Exception as e:
                results[strategy_name] = "异常"
                logger.error(f"策略 {strategy_name} 优化任务异常: {str(e)}", exc_info=True)
    
    # 打印最终结果摘要
    logger.info("===== 所有策略优化完成 =====")
    logger.info("优化结果摘要:")
    for strategy, status in results.items():
        logger.info(f"  {strategy}: {status}")
    
    logger.info(f"结束时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("程序执行完毕")