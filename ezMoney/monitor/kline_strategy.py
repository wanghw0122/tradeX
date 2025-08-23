import numpy as np
from collections import deque
from typing import List, Tuple, Optional, Deque, Dict, Any

class SimplifiedKLineStrategy:
    def __init__(self, stagnation_kline_ticks = 10, decline_kline_ticks = 15, yang_yin_threshold = 0.002, stagnation_n = 10,
                 stagnation_volume_ratio_threshold = 2.5, stagnation_ratio_threshold = 40, decline_volume_ratio_threshold = 2.5,
                 max_rebounds = 2, decline_ratio_threshold = 50):

        # K线参数
        self.stagnation_kline_ticks = stagnation_kline_ticks  # 放量滞涨K线包含的tick数
        self.decline_kline_ticks = decline_kline_ticks     # 放量下跌K线包含的tick数
        self.yang_threshold = yang_yin_threshold   # 阳线判定阈值(0.2%)
        self.yin_threshold = -yang_yin_threshold   # 阴线判定阈值(-0.2%)
        
        # 放量滞涨参数
        self.stagnation_n = stagnation_n             # 用于计算近期平均成交量的K线数量
        self.stagnation_volume_ratio_threshold = stagnation_volume_ratio_threshold  # 量比阈值
        self.stagnation_price_change_max_threshold = 4  # 价格变化阈值(0.5%)
        self.stagnation_price_change_min_threshold = -0.5  # 价格变化阈值(0.5%)
        self.stagnation_ratio_threshold = stagnation_ratio_threshold  # 量价背离比率阈值
        self.stagnation_confirmation_count = 1  # 放量滞涨确认信号个数
        
        # 放量下跌参数
        self.decline_start_kline = 0      # 启动窗口，从第几个K线开始检测
        self.decline_volume_ratio_threshold = decline_volume_ratio_threshold  # 放量下跌量比阈值
        self.decline_price_drop_threshold = -0.005  # 放量下跌跌幅阈值(-0.8%)
        self.decline_price_drop_sd_threshold = 0.1
        self.max_rebounds = max_rebounds   # 最大允许反弹次数k
        self.decline_ratio_threshold = decline_ratio_threshold  # 量价背离比率阈值
        
        # 状态变量
        self.stagnation_kline_count = 0   # 放量滞涨K线计数器
        self.decline_kline_count = 0      # 放量下跌K线计数器
        self.decline_signal_detected = False  # 是否检测到放量下跌信号
        self.rebound_count = 0            # 反弹次数计数
        self.rebound_started = False      # 是否处于反弹中
        self.last_decline_signal_kline_index = -1  # 上次放量下跌信号发生的K线索引
        self.last_rebound_check_kline_index = -1
        self.stagnation_signal_count = 0  # 放量滞涨信号计数
        self.stagnation_signal_detected = False  # 是否检测到放量滞涨信号
        
        # K线数据
        self.stagnation_klines = deque(maxlen=1000)  # 放量滞涨K线历史
        self.decline_klines = deque(maxlen=1000)    # 放量下跌K线历史
        self.current_stagnation_kline = None       # 当前放量滞涨K线
        self.current_decline_kline = None          # 当前放量下跌K线
        # 开盘信息
        self.open_price = 0.0
        self.avg_price = 0.0  # 均价线
        self.initialized = False
        
    def initialize(self, open_price: float, avg_price: float):
        if self.initialized:
            return
        """初始化开盘信息"""
        self.open_price = open_price
        self.avg_price = avg_price
        self.stagnation_kline_count = 0
        self.decline_kline_count = 0
        self.decline_signal_detected = False
        self.rebound_count = 0
        self.rebound_started = False
        self.last_decline_signal_kline_index = -1
        self.last_rebound_check_kline_index = -1
        self.stagnation_signal_count = 0
        self.stagnation_signal_detected = False
        self.current_stagnation_kline = None
        self.current_decline_kline = None
        self.stagnation_klines.clear()
        self.decline_klines.clear()
        self.initialized = True

        
    def update_tick_data(self, current_volume: float, current_price: float, 
                        current_avg_volume: float, current_avg_price: float = None):
        """更新tick数据"""
        # 更新均价线（如果提供）
        if current_avg_price is not None:
            self.avg_price = current_avg_price
            
        # 更新放量滞涨K线
        self.current_stagnation_kline = self.update_kline(
            current_volume, current_price, current_avg_volume,
            self.stagnation_kline_ticks, self.current_stagnation_kline, self.stagnation_klines,
            self.process_stagnation_kline
        )
        
        # 只有在没有检测到放量下跌信号时才更新放量下跌K线
        if not self.decline_signal_detected:
            self.current_decline_kline = self.update_kline(
                current_volume, current_price, current_avg_volume,
                self.decline_kline_ticks, self.current_decline_kline, self.decline_klines,
                self.process_decline_kline
            )
        else:
            # 如果已经检测到放量下跌信号，只更新K线但不处理（等待反弹）
            if self.current_decline_kline is None:
                self.current_decline_kline = {
                    'open': current_price,
                    'high': current_price,
                    'low': current_price,
                    'close': current_price,
                    'volume': current_volume,
                    'avg_volume': current_avg_volume,
                    'ticks': 1
                }
            else:
                self.current_decline_kline['high'] = max(self.current_decline_kline['high'], current_price)
                self.current_decline_kline['low'] = min(self.current_decline_kline['low'], current_price)
                self.current_decline_kline['close'] = current_price
                self.current_decline_kline['volume'] += current_volume
                self.current_decline_kline['avg_volume'] = current_avg_volume
                self.current_decline_kline['ticks'] += 1
                
                # 检查是否完成一个K线
                if self.current_decline_kline['ticks'] >= self.decline_kline_ticks:
                    # 保存K线但不处理，只用于后续的反弹检测
                    self.decline_klines.append(self.current_decline_kline.copy())
                    self.decline_kline_count += 1
                    self.current_decline_kline = None
    
    def update_kline(self, volume: float, price: float, avg_volume: float,
                    kline_ticks: int, current_kline: Dict[str, Any], 
                    klines_history: Deque, process_callback) -> Optional[Dict[str, Any]]:
        """更新K线数据"""
        if current_kline is None:
            # 开始新的K线
            current_kline = {
                'open': price,
                'high': price,
                'low': price,
                'close': price,
                'volume': volume,
                'avg_volume': avg_volume,  # 这里存储的是历史平均成交量
                'ticks': 1
            }
            return current_kline
        
        # 更新当前K线
        current_kline['high'] = max(current_kline['high'], price)
        current_kline['low'] = min(current_kline['low'], price)
        current_kline['close'] = price
        current_kline['volume'] += volume
        # 注意：这里不再对avg_volume求平均，保持为历史平均成交量
        current_kline['avg_volume'] = avg_volume  # 更新为最新的历史平均成交量
        current_kline['ticks'] += 1
        
        # 检查是否完成一个K线
        if current_kline['ticks'] >= kline_ticks:
            # 保存K线并重置
            klines_history.append(current_kline.copy())
            process_callback(current_kline)
            return None
        
        return current_kline
    
    def process_stagnation_kline(self, kline: Dict[str, Any]) -> bool:
        """处理放量滞涨K线"""
        self.stagnation_kline_count += 1
        
        # 计算价格变化
        price_change = (kline['close'] - kline['open']) / kline['open'] if kline['open'] > 0 else 0
        
        price_change = price_change * 100

        price_change_sd = max(price_change, 0) * 20 / self.stagnation_kline_ticks

        # 计算量比
        volume_ratio = self.calculate_stagnation_volume_ratio(kline)
        
        volume_price_ratio = volume_ratio / (price_change_sd + 0.001)
        
        # 检测放量滞涨条件
        condition1 = volume_ratio >= self.stagnation_volume_ratio_threshold  # 放量
        condition2 = price_change <= self.stagnation_price_change_max_threshold  # 滞涨
        condition3 = price_change >= self.stagnation_price_change_min_threshold  # 不是下跌
        condition4 = volume_price_ratio >= self.stagnation_ratio_threshold  # 量价背离
        
        if condition1 and condition2 and condition3 and condition4:
            # print(f"放量滞涨K线 {self.stagnation_kline_count}: "
            #       f"量比 {volume_ratio:.2f}, 涨幅 {price_change:.2f}%, 涨速 {price_change_sd:.2f}%, "
            #       f"量价比 {volume_price_ratio:.2f}")
            
            # 增加放量滞涨信号计数
            self.stagnation_signal_count += 1
            
            # 检查是否达到确认信号个数
            if self.stagnation_signal_count >= self.stagnation_confirmation_count:
                self.stagnation_signal_detected = True
                self.stagnation_signal_count = 0  # 重置计数
                return True
            
            return False
        
        # 如果条件不满足，重置计数
        self.stagnation_signal_count = 0
        return False
    
    def calculate_stagnation_volume_ratio(self, kline: Dict[str, Any]) -> float:
        """计算放量滞涨的量比"""
        # 如果K线数量不足（不包括当前K线），使用前5日平均成交量
        if len(self.stagnation_klines) <= self.stagnation_n:
            if kline['avg_volume'] > 0:
                return kline['volume'] / kline['avg_volume']
            return 1.0
        
        # 计算最近n个K线的平均成交量（排除当前K线）
        # 获取除了当前K线之外的最后n个K线
        recent_klines = list(self.stagnation_klines)[-self.stagnation_n-1:-1]
        avg_recent_volume = sum(k['volume'] for k in recent_klines) / len(recent_klines)
        
        # 计算量比
        if avg_recent_volume > 0:
            return kline['volume'] / avg_recent_volume
        return 1.0
    
    def process_decline_kline(self, kline: Dict[str, Any]) -> bool:
        """处理放量下跌K线"""
        self.decline_kline_count += 1
        
        # 检查是否达到启动窗口
        if self.decline_kline_count < self.decline_start_kline:
            return False
        
        # 计算从开盘到现在的价格变化
        price_change = (kline['close'] - self.open_price) / self.open_price if self.open_price > 0 else 0
        
        # 检查当前价格是否在均价之下
        below_avg_price = kline['close'] < self.avg_price
        
        # 计算K线涨跌幅
        kline_price_change = (kline['close'] - kline['open']) / kline['open'] if kline['open'] > 0 else 0
        
        # 判断K线是否为阴线
        is_yin = kline_price_change <= 0
        
        # 计算量比（使用从开盘到当前K线的总成交量）
        volume_ratio = self.calculate_decline_volume_ratio()

        price_change_sd = abs(price_change) * 100 * 20 / self.decline_kline_count / self.decline_kline_ticks

        condition_threshold_combine = volume_ratio * price_change_sd
        
        # 检测放量下跌条件
        condition1 = volume_ratio >= self.decline_volume_ratio_threshold  # 放量
        condition2 = price_change <= self.decline_price_drop_threshold    # 大幅下跌
        condition3 = below_avg_price  # 价格在均价之下
        condition4 = is_yin  # 当前K线是阴线

        condition5 = condition_threshold_combine >= self.decline_ratio_threshold
        condition6 = price_change_sd >= self.decline_price_drop_sd_threshold

        
        if condition1 and condition2 and condition3 and condition4 and condition5 and condition6:

            # print(f"放量下跌K线 {self.decline_kline_count}: "
            #       f"量比 {volume_ratio:.2f}, 跌幅 {price_change*100:.2f}%, 跌速 {price_change_sd:.2f}%"
            #       f"量价比 {condition_threshold_combine:.2f}, "
            #       f"低于均价: {below_avg_price}, 阴线: {is_yin}")
            
            # 检测到放量下跌信号，开始监听反弹
            self.decline_signal_detected = True
            self.last_decline_signal_kline_index = self.decline_kline_count
            self.last_rebound_check_kline_index = self.decline_kline_count

            self.rebound_count = 0
            self.rebound_started = False
            
            return True
            
        return False
    
    def calculate_decline_volume_ratio(self) -> float:
        """计算放量下跌的量比"""
        # 计算当前所有K线的总成交量
        total_volume = sum(k['volume'] for k in self.decline_klines)
        
        # 计算前5日同一时间段内的平均总成交量
        total_avg_volume = sum(k['avg_volume'] for k in self.decline_klines)
        
        # 计算量比
        if total_avg_volume > 0:
            return total_volume / total_avg_volume
        return 1.0
    
    def process_rebound(self, kline: Dict[str, Any]) -> bool:
        """处理反弹检测"""
        if not self.decline_signal_detected:
            return False
            
        # 检查是否超过均价线
        if kline['close'] >= self.avg_price:
            # 超过均价线，重置放量下跌检测
            self.decline_signal_detected = False
            self.rebound_count = 0
            self.rebound_started = False
            # print("价格超过均价线，重置放量下跌检测")
            return False
        
        # 计算K线涨跌幅
        price_change = (kline['close'] - kline['open']) / kline['open'] if kline['open'] > 0 else 0
        
        # 判断K线形态
        is_yang = price_change >= self.yang_threshold  # 阳线
        is_yin = price_change <= self.yin_threshold    # 阴线
        
        # 处理反弹逻辑
        if not self.rebound_started and is_yang:
            # 反弹开始：出现阳线
            self.rebound_started = True
            # print(f"反弹开始: 阳线涨幅 {price_change*100:.2f}%")
        elif self.rebound_started and is_yin:
            # 反弹结束：出现阴线
            self.rebound_started = False
            self.rebound_count += 1
            # print(f"反弹结束: 阴线跌幅 {price_change*100:.2f}%，反弹次数: {self.rebound_count}")
            
            # 检查反弹次数是否超过阈值
            if self.rebound_count >= self.max_rebounds:
                # 反弹次数超过阈值，发出卖出信号
                self.rebound_count = 0
                self.decline_signal_detected = False  # 重置信号检测
                return True
                
        return False
    
    def generate_signals(self) -> Tuple[int, int]:
        """
        生成信号
        返回: (放量滞涨信号, 放量下跌信号)
        1表示有信号，0表示无信号
        """
        stagnation_signal = 0
        decline_signal = 0
        
        # 1. 处理放量滞涨信号
        if self.stagnation_signal_detected:
            stagnation_signal = 1
            self.stagnation_signal_detected = False  # 重置信号
        
        # 2. 处理放量下跌信号
        if self.decline_klines and self.decline_signal_detected:
            # 获取最新的下跌K线
            latest_decline_kline = self.decline_klines[-1]
            
            # 检查是否是新的K线（通过K线计数判断）
            if self.decline_kline_count > self.last_rebound_check_kline_index:
                # 更新最后检查的K线索引
                self.last_rebound_check_kline_index = self.decline_kline_count
                
                # 处理反弹检测
                if self.process_rebound(latest_decline_kline):
                    decline_signal = 1
        
        return stagnation_signal, decline_signal

# 使用示例
def example_usage():
    # 初始化策略
    strategy = SimplifiedKLineStrategy()
    
    # 设置开盘信息
    open_price = 100.0
    avg_price = 100.5
    strategy.initialize(open_price, avg_price)
    
    # 模拟实时数据流
    n_ticks = 500
    stagnation_signals = 0
    decline_signals = 0
    
    # 设置随机种子以便复现结果
    np.random.seed(42)
    
    for i in range(n_ticks):
        # 生成模拟数据 (实际应用中应使用真实数据)
        volume_today = np.random.rand() * 1000 + 500  # 当日成交量
        volume_avg_prev5 = np.random.rand() * 800 + 400  # 前5日平均成交量
        
        # 模拟价格走势 - 先下跌后多次反弹但未超过均价
        if i < 200:
            price_today = 100 - i * 0.1  # 前期下跌
        elif i < 300:
            # 第一次反弹
            price_today = 80 + (i - 200) * 0.15
        elif i < 350:
            # 回落
            price_today = 95 - (i - 300) * 0.1
        elif i < 400:
            # 第二次反弹
            price_today = 90 + (i - 350) * 0.12
        elif i < 450:
            # 回落
            price_today = 96 - (i - 400) * 0.1
        else:
            # 第三次反弹
            price_today = 91 + (i - 450) * 0.1
            
        # 均价线缓慢上升
        avg_price_today = 95 + i * 0.02
        
        # 更新数据
        strategy.update_tick_data(volume_today, price_today, volume_avg_prev5, avg_price_today)
        
        # 生成信号
        stagnation_signal, decline_signal = strategy.generate_signals()
        
        if stagnation_signal == 1:
            stagnation_signals += 1
            print(f"Tick {i}: 放量滞涨信号, 价格: {price_today:.2f}, 均价: {avg_price_today:.2f}")
        
        if decline_signal == 1:
            decline_signals += 1
            print(f"Tick {i}: 放量下跌信号, 价格: {price_today:.2f}, 开盘价: {open_price:.2f}")
    
    # 输出统计
    print(f"\n总计放量滞涨信号: {stagnation_signals} 个")
    print(f"总计放量下跌信号: {decline_signals} 个")

# 执行示例
if __name__ == "__main__":
    example_usage()