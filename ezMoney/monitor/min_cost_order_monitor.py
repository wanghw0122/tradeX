
from re import sub
from scipy.signal import savgol_filter
import sys
import time
sys.path.append(r"D:\workspace\TradeX\ezMoney")
from common import constants
import datetime
import traceback
import threading
import queue
from sqlite_processor.mysqlite import SQLiteManager

from xtquant import xtconstant

from logger import strategy_logger as logger


strategy_name_to_max_down_pct = {
    '高强中低开低吸': 6.6,
    '低位高强中低开低吸': 3.5,
    '低位高强低吸': 5,
    '低位孕线低吸': 5,
    '低位中强中低开低吸': 5,
    '中强中低开低吸': 5.5,
    '首红断低吸': 6.6,
    '一进二弱转强': 6.6,
    '高位高强追涨': 6.6,
    '启动低吸': 5,
    '低位断板低吸': 5,
    '高强中高开追涨': 6.6,
    '小高开追涨': 6.6,
    '中位小低开低吸': 5,
    '中位中强小低开低吸': 5,
    '强更强': 6.6,
}

strategy_name_to_main_strategy_name = {
    '高强中低开低吸': '低吸-高强中低开低吸',
    '低位高强中低开低吸': '低吸-低位高强中低开低吸',
    '低位高强低吸': '低吸-低位高强低吸',
    '低位孕线低吸': '低吸-低位孕线低吸',
    '低位中强中低开低吸': '低吸-低位中强中低开低吸',
    '中强中低开低吸': '低吸-中强中低开低吸',
    '首红断低吸': '低吸-首红断低吸',
    '一进二弱转强': '接力-一进二弱转强',
    '高位高强追涨': '追涨-高位高强追涨',
    '启动低吸': '低吸-启动低吸',
    '低位断板低吸': '低吸-低位断板低吸',
    '高强中高开追涨': '追涨-高强中高开追涨',
    '小高开追涨': '追涨-小高开追涨',
    '中位小低开低吸': '低吸-中位小低开低吸',
    '中位中强小低开低吸': '低吸-中位中强小低开低吸',
    '强更强': '强更强',
}

strategy_name_to_sub_strategy_name = {
    '高强中低开低吸': '方向前2',
    '低位高强中低开低吸': '方向低频2',
    '低位高强低吸': '中低频2',
    '低位孕线低吸': '回撤小收益大',
    '低位中强中低开低吸': '第一高频',
    '中强中低开低吸': '第二高频',
    '首红断低吸': '第一高频',
    '一进二弱转强': '倒接力31',
    '高位高强追涨': '',
    '启动低吸': '第一高频2',
    '低位断板低吸': '第一高频',
    '高强中高开追涨': '',
    '小高开追涨': '第一',
    '中位小低开低吸': '',
    '中位中强小低开低吸': '第一高频',
    '强更强': '第一',
}


def get_strategy_and_sub_strategy_name(strategy_name, sub_strategy_str):
    new_strategy_name = strategy_name_to_main_strategy_name[strategy_name]
    new_sub_strategy_name = strategy_name_to_sub_strategy_name[strategy_name]

    if '一进二弱转强' in strategy_name:
        sub_strategy_list = ','.split(sub_strategy_str)
        if '倒接力31' in sub_strategy_list or '倒接力3' in sub_strategy_list or '倒接力32' in sub_strategy_list:
            new_sub_strategy_name = '倒接力31'
        elif '倒接力41' in sub_strategy_list or '倒接力4' in sub_strategy_list:
            new_sub_strategy_name = '倒接力4'
        elif '倒接力51' in sub_strategy_list or '倒接力5' in sub_strategy_list:
            new_sub_strategy_name = '倒接力5'
        elif '接力倒接力3' in sub_strategy_list or '接力倒接力31' in sub_strategy_list:
            new_sub_strategy_name = '接力倒接力3'
        elif '接力倒接力4' in sub_strategy_list:
            new_sub_strategy_name = '接力倒接力4'
        else:
            pass

    return new_strategy_name, new_sub_strategy_name


def calculate_seconds_difference(specified_time):
    current_time = datetime.datetime.now().timestamp()
    time_difference =  current_time - (specified_time / 1000)
    return time_difference

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
        if volume < 0:
            return None
        """更新状态并检测信号"""
        # 保存成交量
        self.volume_history.append(volume)
        if len(self.volume_history) > self.volume_window:
            self.volume_history.pop(0)
        
        # 更新MACD
        self.last_macd_dif = self.macd_dif
        self.last_macd_dea = self.macd_dea
        
        # 计算MACD (简化的增量计算)
        if self.macd_dif is None:
            self.macd_dif = 0
            self.macd_dea = 0
            self.ema_fast_macd = price
            self.ema_slow_macd = price
            # self.macd_dif = price
            # self.macd_dea = price
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
            # DIF = EMA(close, fast) - EMA(close, slow)
            # alpha_fast = 2 / (self.macd_fast + 1)
            # alpha_slow = 2 / (self.macd_slow + 1)
            # self.macd_dif = self.macd_dif + alpha_fast * (price - self.macd_dif)
            # self.macd_dif = self.macd_dif - alpha_slow * (price - self.macd_dif)
            
            # # DEA = EMA(DIF, signal)
            # alpha_signal = 2 / (self.macd_signal + 1)
            # self.macd_dea = self.macd_dea + alpha_signal * (self.macd_dif - self.macd_dea)
        
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
            volume_strength = volume / (avg_volume + 1) - 1.0  # 0-1范围
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
    

class MinCostOrderMonitor(object):
    def __init__(self, stock_code, stock_name, strategy_name, params, sub_strategy_str = '', qmt_trader = None):

        self.sub_strategy_str = sub_strategy_str
        self.total_budget = params['budget']
        self.base_budget = params['base_budget']
        self.params = params
        self.order_ids = []
        self.order_id_to_budget = {}
        self.order_id_miss_times = {}
        self.remaining_budget = self.total_budget
        self.left_base_budget = self.base_budget
        self.strategy_name = strategy_name
        self.bq = queue.Queue()
        self.filter = TripleFilter(
            ema_alpha=params['ema_alpha'],
            kalman_q=params['kalman_q'],
            kalman_r=params['kalman_r'],
            sg_window=params['sg_window']
        )
        
        self.detector = SignalDetector(
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

        self.remaining_buy_down_min_pct = params.get('remaining_buy_down_min_pct', 0.02)
        self.max_strategy_down_pct = params.get('max_strategy_down_pct', 15)
        self.base_buy_gap_ticks = params.get('base_buy_gap_ticks', 100)
        self.base_buy_down_min_pct = params.get('base_buy_down_min_pct', 0.005)
        self.base_buy_times = params.get('base_buy_times', 5)
        self.base_max_buy_ticks = params.get('base_max_buy_ticks', 200)
        self.max_buy_ticks = params.get('max_buy_ticks', 400)

        self.stock_code = stock_code
        self.stock_name = stock_name
        if qmt_trader != None:
            self.qmt_trader = qmt_trader

        self.base_price = -1
        self.reference_price = -1

        self.last_base_buy_tick_time = 0
        # 当前价
        self.current_price = 0
        self.limit_up_price = -1
        self.limit_down_price = -1
        self.smooth_price = 0
        self.open_price = 0
        # 昨天收盘价
        self.last_close_price = 0
        # 当前步数
        self.current_tick_steps = -1
        self.pre_volume = -1

        self.max_down_pct = 0

        self.start_monitor()
        self.monitor_orders_running = False
        self.monitor_orders_thread = None
        self.start_monitor_orders()
    

    def start_monitor(self):
        logger.info(f"start min cost order monitor {self.stock_code} {self.stock_name}")
        self.thread = threading.Thread(target=self.monitor)
        self.thread.setDaemon(True)
        self.thread.start()
        return self.thread
    

    def stop_monitor(self):
        logger.info(f"stop monitor {self.stock_code} {self.stock_name}")
        self.thread.join()


    def send_orders(self, data, budget):
        lastPrice = data['lastPrice']
        open = data['open']
        high = data['high']
        low = data['low']
        lastClose = data['lastClose']
        volume = data['volume']
        amount = data['amount']
        pvolume = data['pvolume'] if data['pvolume'] > 0 else 1
        askPrice = data['askPrice']
        bidPrice = data['bidPrice']
        askVol = data['askVol']
        bidVol = data['bidVol']
        if budget <= 0:
            return
        
        # 初始化变量为 None
        ask1_price = None
        ask1_vol = None
        ask2_price = None
        ask2_vol = None
        ask3_price = None
        ask3_vol = None

        # 检查列表长度并赋值
        if len(askPrice) >= 1 and len(askVol) >= 1:
            ask1_price = askPrice[0]
            ask1_vol = askVol[0]
        if len(askPrice) >= 2 and len(askVol) >= 2:
            ask2_price = askPrice[1]
            ask2_vol = askVol[1]
        if len(askPrice) >= 3 and len(askVol) >= 3:
            ask3_price = askPrice[2]
            ask3_vol = askVol[2]

        if ask1_price and ask1_vol:
            ask1_amout = ask1_price * ask1_vol
        if ask2_price and ask2_vol:
            ask2_amout = ask2_price * ask2_vol
        if ask3_price and ask3_vol:
            ask3_amout = ask3_price * ask3_vol
        
        if ask1_price:
            ask1_pct = (ask1_price - lastPrice) / lastPrice
            if ask1_pct > 0.015:
                self.left_base_budget = self.left_base_budget + budget
                return

        total_budgets = budget
        order_volume = total_budgets / lastPrice // 100
        order_volume = int(order_volume)
        if order_volume <= 0:
            logger.error(f'[低吸]买入股票价格太低 - {budget}')
            self.left_base_budget = self.left_base_budget + budget
            return
        order_type = xtconstant.MARKET_PEER_PRICE_FIRST
        if 'SH' in self.stock_code:
            order_type = xtconstant.MARKET_SH_CONVERT_5_CANCEL
        else:
            order_type = xtconstant.MARKET_SZ_CONVERT_5_CANCEL
        order_id = self.qmt_trader.buy_immediate_market_order(self.stock_code, order_volume * 100, order_type = order_type)
        if order_id > 0:
            logger.info(f"[低吸]成功下单购买股票，股票代码: {self.stock_code}, 股票名称: {self.stock_name}, 下单价格: {lastPrice:.2f}, 下单数量: {order_volume * 100}, 订单 ID: {order_id}")

            self.order_ids.append(order_id)
            self.order_id_to_budget[order_id] = budget, order_volume*100



    def start_monitor_orders(self):
        logger.info(f"start min cost orders monitor {self.stock_code} {self.stock_name}")
        if not self.monitor_orders_running:
            self.monitor_orders_running = True
            self.monitor_orders_thread = threading.Thread(target=self._monitor_orders_loop)
            self.monitor_orders_thread.setDaemon(True)
            self.monitor_orders_thread.start()

    def stop_monitor_orders(self):
        if self.monitor_orders_running:
            self.monitor_orders_running = False
            if self.monitor_orders_thread:
                self.monitor_orders_thread.join()

    def _monitor_orders_loop(self):
        while self.monitor_orders_running:
            self._monitor_orders()
            time.sleep(5)

    
    def _monitor_orders(self):
        if not hasattr(self, 'qmt_trader') or self.qmt_trader is None:
            logger.error("qmt_trader 未初始化，无法查询订单状态")
            return
        
        order_id_list = list(self.order_id_to_budget.keys())
        if not order_id_list:
            return
        else:
            logger.info(f"查询到订单继续loop. {self.stock_code} - {self.stock_name} - {order_id_list} - {self.order_ids}")


        order_infos = self.qmt_trader.get_all_orders(filter_order_ids = order_id_list)
        if order_infos:
            logger.info(f"查询到订单信息. {self.stock_code} - {self.stock_name} - {order_infos}")
        else:
            logger.error(f"查询不到订单信息. {self.stock_code} - {self.stock_name} - {order_id_list}")

        for order_id in order_id_list:
            if order_id not in order_infos:
                if order_id in self.order_id_miss_times:
                    self.order_id_miss_times[order_id] = self.order_id_miss_times[order_id] + 1
                    if self.order_id_miss_times[order_id] > 20 and order_id in self.order_id_to_budget:
                        logger.error(f"订单超时未成交 删除记录. {self.stock_code} - {self.stock_name} - {order_id}")
                        if order_id in self.order_id_to_budget:
                            self.left_base_budget = self.left_base_budget + self.order_id_to_budget[order_id][0]

                        del self.order_id_to_budget[order_id]
                else:
                    self.order_id_miss_times[order_id] = 1
        
        for order_id, info in order_infos.items():
            try:
                order_status = info['order_status']
                if order_status == xtconstant.ORDER_SUCCEEDED or order_status == xtconstant.ORDER_PART_SUCC:
                    try:
                        from date_utils import date
                        date_key = date.get_current_date()
                        table_name = 'trade_data'
                        main_strategy_name, sub_strategy_name = get_strategy_and_sub_strategy_name(self.strategy_name, self.sub_strategy_str)


                        with SQLiteManager(r'D:\workspace\TradeX\ezMoney\sqlite_db\strategy_data.db') as manager:
                            if sub_strategy_name:
                                manager.insert_data(table_name, {'date_key': date_key,'order_id': order_id,'strategy_name': main_strategy_name, 'sub_strategy_name': sub_strategy_name, 'buy0_or_sell1': 0,'stock_code': self.stock_code,'stock_name': self.sub_strategy_str, 'order_type': 1, 'order_price': self.base_price, 'order_volume': self.order_id_to_budget[order_id][1], 'trade_price': self.base_price, 'trade_volume': self.order_id_to_budget[order_id][1], 'trade_amount': self.order_id_to_budget[order_id][0], 'left_volume': self.order_id_to_budget[order_id][1]})
                            else:
                                manager.insert_data(table_name, {'date_key': date_key,'order_id': order_id,'strategy_name': main_strategy_name, 'buy0_or_sell1': 0,'stock_code': self.stock_code, 'stock_name': self.sub_strategy_str, 'order_type': 1, 'order_price': self.base_price, 'order_volume': self.order_id_to_budget[order_id][1], 'trade_price': self.base_price, 'trade_volume': self.order_id_to_budget[order_id][1], 'trade_amount': self.order_id_to_budget[order_id][0], 'left_volume': self.order_id_to_budget[order_id][1]})

                    except Exception as e:
                        logger.error(f"插入数据失败 {e}")
                    logger.info(f"订单成交成功. {self.stock_code} - {self.stock_name} - {order_id}")
                    del self.order_id_to_budget[order_id]
                elif order_status == xtconstant.ORDER_JUNK or order_status == xtconstant.ORDER_CANCELED or order_status == xtconstant.ORDER_PART_CANCEL:
                    logger.info(f"订单取消. {self.stock_code} - {self.stock_name} - {order_id}")
                    if order_id in self.order_id_to_budget:
                        self.left_base_budget = self.left_base_budget + self.order_id_to_budget[order_id][0]
                    del self.order_id_to_budget[order_id]
                else:
                    pass
            except Exception as e:
                 logger.error(f"处理订单 {order_id} 时发生错误: {str(e)}")

    # ... 已有代码 ...
    
    def monitor(self):
        while True:
            try:
                data = self.bq.get()
                if data is None:
                    continue
                time = data['time']
                diff = calculate_seconds_difference(time)
                origin_diff = data['diff']
                stock = data['stock']
                assert stock == self.stock_code, f"stock code not match. {stock} {self.stock_code}"
                logger.info(f"[mincost] monitor data. {self.stock_code} - {self.stock_name} - {data} - {time} - {diff} - {origin_diff} - {diff - origin_diff}")
                lastPrice = data['lastPrice']
                open = data['open']
                # high = data['high']
                # low = data['low']
                lastClose = data['lastClose']
                volume = data['volume']
                amount = data['amount']
                # pvolume = data['pvolume'] if data['pvolume'] > 0 else 1
                # askPrice = data['askPrice']
                # bidPrice = data['bidPrice']
                # askVol = data['askVol']
                # bidVol = data['bidVol']
                if self.pre_volume < 0:
                    self.pre_volume = volume
                
                if amount <= 0 or volume <= 0:
                    logger.error(f"amount <= 0. {amount} {time} {self.stock_code} {self.stock_name}")
                    continue
                if lastPrice <= 0:
                    logger.error(f"lastPrice <= 0. {lastPrice} {time} {self.stock_code} {self.stock_name}")
                    continue
                if diff > 10 and self.current_tick_steps < 0:
                    logger.error(f"[mincost] time diff > 10s. {diff} {origin_diff} {diff - origin_diff} {time} {self.stock_code} {self.stock_name} {self.current_tick_steps}")
                    continue
                
                self.current_price = lastPrice
                # 开盘价
                self.open_price = open
                # 昨天收盘价
                self.last_close_price = lastClose
                # 当前步数
                self.current_tick_steps = self.current_tick_steps + 1
                if self.current_tick_steps == 0 or self.base_price < 0:
                    self.base_price = lastPrice
                    self.reference_price = self.base_price
                if self.current_tick_steps > self.max_buy_ticks:
                    logger.error(f"current_tick_steps > 410 break. {self.current_tick_steps} {time} {self.stock_code} {self.stock_name}")
                    break
                self.smooth_price = self.filter.update(lastPrice)
                self.signal = self.detector.update(self.smooth_price, volume - self.pre_volume)

                if self.limit_up_price < 0 or self.limit_down_price < 0:
                    limit_down_price_0, limit_up_price_0 = constants.get_limit_price(self.last_close_price, stock_code=self.stock_code)
                    self.limit_up_price = limit_up_price_0
                    self.limit_down_price = limit_down_price_0
                    self.max_down_pct = (self.base_price - self.limit_down_price) / self.base_price

                if diff > 6:
                    logger.error(f"[mincost] time diff > 6s. {diff} {origin_diff} {time} {self.stock_code} {self.stock_name} {self.current_tick_steps}")
                    self.pre_volume = volume
                    continue
                if self.signal:
                    # 计算价格差异（相对于基准价）
                    price_diff = (self.reference_price - lastPrice) / self.base_price
                    base_buy_budget = 0
                    buy_total_budget = 0
                    if (lastPrice - self.limit_down_price) / self.base_price < 0.01 and self.left_base_budget > 0:
                        base_buy_budget = self.left_base_budget
                        self.left_base_budget = 0
                        self.last_base_buy_tick_time = self.current_tick_steps

                    elif (self.base_price - lastPrice) / self.base_price > 0.01 and self.left_base_budget > 0:
                        down_base_pct = (self.base_price - lastPrice) / self.base_price
                        base_buy_budget = max(1/self.base_buy_times, down_base_pct / self.max_down_pct) * self.base_budget
                        base_buy_budget = min(base_buy_budget, self.left_base_budget)
                        self.left_base_budget = self.left_base_budget - base_buy_budget

                        self.last_base_buy_tick_time = self.current_tick_steps
                        
                    # 只有跌幅超过1%才买入
                    if price_diff >= self.remaining_buy_down_min_pct and self.remaining_budget > 0:
                        buy_pct = price_diff * 100 / self.max_strategy_down_pct
                        buy_amount = min(buy_pct * self.total_budget, self.remaining_budget)
                        
                        if buy_pct > 1/5 or buy_amount > 5000:
                            # 执行买入
                            buy_total_budget = buy_amount
                            self.remaining_budget = max(0, self.remaining_budget - buy_amount)
                            
                            # 更新基准价格为当前买入价
                            self.reference_price = lastPrice
                            
                            # 调试输出
                            if self.params.get('debug', False):
                                logger.info(f"买入点: 价格={lastPrice:.4f}, "
                                        f"金额={buy_amount:.2f}, "
                                        "强度=0.0")
                    if buy_total_budget + base_buy_budget > 0:
                        logger.info(
                            f"📨 发送订单 | 策略 '{self.strategy_name}' | "
                            f"Tick步数: {self.current_tick_steps}/410 | "
                            f"触发原因: {'信号触发+价格偏离' if buy_total_budget > 0 else ''}"
                            f"{'基础预算保护' if base_buy_budget > 0 else ''} | "
                            f"总预算: {self.total_budget:.2f} | "
                            f"剩余预算: {self.remaining_budget:.2f} | "
                            f"基础预算剩余: {self.left_base_budget:.2f} | "
                            f"本次分配: [信号部分={buy_total_budget:.2f}] "
                            f"[基础部分={base_buy_budget:.2f}] | "
                            f"参考价/基价: {self.reference_price:.4f}/{self.base_price:.4f} | "
                            f"当前价: {lastPrice:.4f} | "
                            f"偏离: {price_diff*100:.2f}%"
                        )
                        self.send_orders(data, buy_total_budget + base_buy_budget)

                elif (lastPrice - self.limit_down_price) / self.base_price < 0.01 and self.left_base_budget > 0 and lastPrice <= self.base_price:
                    base_buy_budget = self.left_base_budget
                    logger.info(
                        f"🛡️ 发送订单 | 策略 '{self.strategy_name}' | "
                        f"Tick步数: {self.current_tick_steps}/410 | "
                        f"触发原因: 接近跌停保护 | "
                        f"总预算: {self.total_budget:.2f} | "
                        f"基础预算剩余: {self.left_base_budget:.2f}→0 | "
                        f"本次分配: {base_buy_budget:.2f} | "
                        f"基价/跌停价: {self.base_price:.4f}/{self.limit_down_price:.4f} | "
                        f"当前价: {lastPrice:.4f}"
                    )
                    self.left_base_budget = 0
                    self.last_base_buy_tick_time = self.current_tick_steps
                    self.send_orders(data, base_buy_budget)

                elif lastPrice < self.base_price * (1 - self.base_buy_down_min_pct) and (self.current_tick_steps - self.last_base_buy_tick_time > self.base_buy_gap_ticks or self.last_base_buy_tick_time == 0) and self.left_base_budget > 0:

                    base_buy_budget = min(self.left_base_budget, self.base_budget * 1/self.base_buy_times)
                    logger.info(
                        f"⏱️ 发送订单 | 策略 '{self.strategy_name}' | "
                        f"Tick步数: {self.current_tick_steps}/410 | "
                        f"触发原因: 超时补仓(>{self.last_base_buy_tick_time}+100ticks) | "
                        f"总预算: {self.total_budget:.2f} | "
                        f"基础预算剩余: {self.left_base_budget:.2f}→{self.left_base_budget - base_buy_budget:.2f} | "
                        f"本次分配: {base_buy_budget:.2f} | "
                        f"基价: {self.base_price:.4f} | "
                        f"折价: {(self.base_price - lastPrice)/self.base_price*100:.2f}%"
                    )
                    self.left_base_budget = self.left_base_budget - base_buy_budget
                    self.last_base_buy_tick_time = self.current_tick_steps
                    self.send_orders(data, base_buy_budget)
                elif self.current_tick_steps > self.base_max_buy_ticks and lastPrice < self.base_price * (1 - self.base_buy_down_min_pct) and self.left_base_budget > 0:
                    base_buy_budget = self.left_base_budget
                    logger.info(
                        f"⌛ 发送订单 | 策略 '{self.strategy_name}' | "
                        f"Tick步数: {self.current_tick_steps}/410 | "
                        f"触发原因: 尾盘保护(>200ticks) | "
                        f"总预算: {self.total_budget:.2f} | "
                        f"基础预算剩余: {self.left_base_budget:.2f}→0 | "
                        f"本次分配: {base_buy_budget:.2f} | "
                        f"基价: {self.base_price:.4f} | "
                        f"折价: {(self.base_price - lastPrice)/self.base_price*100:.2f}%"
                    )
                    self.left_base_budget = 0
                    self.last_base_buy_tick_time = self.current_tick_steps
                    self.send_orders(data, base_buy_budget)
                self.pre_volume = volume
            except Exception as e:
                stack_trace = traceback.format_exc()
                logger.error(f"发生异常: {str(e)}\n堆栈信息:\n{stack_trace}")
                logger.error(f"Error processing data: {e}")

    def consume(self, data):
        logger.info(f"{self.stock_code} {self.stock_name} mincost 监控器接收到数据 {data}")
        try:
            self.bq.put_nowait(data)
        except queue.Full:
            logger.error(f"[MinCostOrderMonitor] {self.stock_code} - {self.stock_name} 监控器队列已满，丢弃数据 {data}")
        except Exception as e:
            logger.error(f"[MinCostOrderMonitor] {self.stock_code} - {self.stock_name} 监控器队列其他异常 {e}")
        # self.bq.put(data)
