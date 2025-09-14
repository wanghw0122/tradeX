
from scipy.signal import savgol_filter
import sys
sys.path.append(r"D:\workspace\TradeX\ezMoney")
from common import constants
import traceback


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
    

class MinCostOrderMonitor:
    def __init__(self, stock_code, stock_name, strategy_name, params, sub_strategy_str=''):
        self.sub_strategy_str = sub_strategy_str
        self.total_budget = params['budget']
        self.base_budget = params['base_budget']
        self.params = params
        self.strategy_name = strategy_name
        self.stock_code = stock_code
        self.stock_name = stock_name
        
        # 初始化滤波器和信号检测器
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

        self.remaining_buy_down_min_pct = params.get('remaining_buy_down_min_pct', 0.005)
        self.max_strategy_down_pct = params.get('max_strategy_down_pct', 6.6)
        self.base_buy_gap_ticks = params.get('base_buy_gap_ticks', 100)
        self.base_buy_down_min_pct = params.get('base_buy_down_min_pct', 0.005)
        self.base_buy_times = params.get('base_buy_times', 5)
        self.base_max_buy_ticks = params.get('base_max_buy_ticks', 200)

        self.max_buy_ticks = params.get('max_buy_ticks', 400)

        # 状态变量
        self.base_price = -1
        self.reference_price = -1
        self.last_base_buy_tick_time = 0
        self.current_price = 0
        self.limit_up_price = -1
        self.limit_down_price = -1
        self.smooth_price = 0
        self.open_price = 0
        self.last_close_price = 0
        self.current_tick_steps = -1
        self.pre_volume = -1
        self.max_down_pct = 0
        
        # 预算管理
        self.remaining_budget = self.total_budget
        self.left_base_budget = self.base_budget
        
        # 存储买入信号
        self.buy_signals = []

    def run_backtest(self, history_data):
        """运行回测并返回所有买入信号点
        Args:
            history_data: list of dict, 历史数据列表，每个元素包含:
                time: 时间戳(毫秒)
                lastPrice: 最新价
                open: 开盘价
                lastClose: 昨收价
                volume: 当前成交量
                pvolume: 前成交量(可为空)
                high: 最高价
                low: 最低价
                amount: 成交额
                askPrice: 卖价列表
                bidPrice: 买价列表
                askVol: 卖量列表
                bidVol: 买量列表
                
        Returns:
            list: 买入信号点列表，每个元素为字典:
                time: 时间戳(毫秒)
                price: 买入价格
                amount: 买入金额
                volume: 买入数量(股数)
                reason: 触发原因
                base_price: 基准价格
                current_step: 当前tick步数
        """        
        for data in history_data:
            try:
                time = data['time']
                lastPrice = data['lastPrice']
                open_price = data['open']
                lastClose = data['lastClose']
                volume = data['volume']
                amount = data['amount']
                askPrice = data['askPrice']
                bidPrice = data['bidPrice']
                askVol = data['askVol']
                bidVol = data['bidVol']

                # 初始化成交量
                if self.pre_volume < 0:
                    self.pre_volume = volume
                    
                # 更新状态
                self.current_price = lastPrice
                self.open_price = open_price
                if self.last_close_price == 0:
                    self.last_close_price = lastClose
                self.current_tick_steps += 1
                
                # 初始化基准价
                if self.current_tick_steps == 0 or self.base_price < 0:
                    self.base_price = lastPrice
                    self.reference_price = self.base_price
                    
                # 处理涨跌停价
                if self.limit_up_price < 0 or self.limit_down_price < 0:
                    limit_down_price_0, limit_up_price_0 = constants.get_limit_price(self.last_close_price, stock_code=self.stock_code)
                    self.limit_up_price = limit_up_price_0
                    self.limit_down_price = limit_down_price_0
                    self.max_down_pct = (self.base_price - self.limit_down_price) / self.base_price
                
                # 更新滤波器和信号检测
                self.smooth_price = self.filter.update(lastPrice)
                volume_diff = volume - self.pre_volume if volume > self.pre_volume else 0
                self.signal = self.detector.update(self.smooth_price, volume_diff)
                
                # 信号处理逻辑
                buy_reason = None
                buy_amount = 0
                base_buy_budget = 0
                buy_total_budget = 0

                sell1 = askPrice[0] if askPrice else 0
                if sell1 == 0 and abs(self.limit_up_price - lastPrice) <= 0.01:
                    continue
                if sell1 <= 0:
                    logger.error(f"sell1 price is {sell1} {self.limit_up_price} {lastPrice} {self.current_tick_steps} {self.stock_code}")
                    continue
                
                if self.signal:
                    # 计算价格差异（相对于基准价）
                    price_diff = (self.reference_price - lastPrice) / self.base_price
                    
                    # 基础预算保护逻辑
                    if (lastPrice - self.limit_down_price) / self.base_price < 0.01 and self.left_base_budget > 0:
                        # 接近跌停保护
                        base_buy_budget = self.left_base_budget
                        self.left_base_budget = 0
                        self.last_base_buy_tick_time = self.current_tick_steps
                        buy_reason = "信号触发+接近跌停保护"
                    
                    elif (self.base_price - lastPrice) / self.base_price > 0.01 and self.left_base_budget > 0:
                        # 价格低于基准价超过1%时的保护
                        down_base_pct = (self.base_price - lastPrice) / self.base_price
                        base_buy_budget = max(1/self.base_buy_times, down_base_pct / self.max_down_pct) * self.base_budget
                        base_buy_budget = min(base_buy_budget, self.left_base_budget)
                        self.left_base_budget -= base_buy_budget
                        self.last_base_buy_tick_time = self.current_tick_steps
                        buy_reason = "信号触发+价格偏离保护"
                    
                    # 价格偏离买入逻辑
                    if price_diff >= self.remaining_buy_down_min_pct and self.remaining_budget > 0:
                        max_down = self.max_strategy_down_pct
                        buy_pct = price_diff * 100 / max_down
                        buy_amount = min(buy_pct * self.total_budget, self.remaining_budget)
                        
                        # 检查买入条件
                        if buy_pct > 1/5 or buy_amount > 500:
                            buy_total_budget = buy_amount
                            self.remaining_budget = max(0, self.remaining_budget - buy_amount)
                            self.reference_price = sell1
                            
                            # 如果还没有原因，设置为价格偏离
                            if not buy_reason:
                                buy_reason = "信号触发+价格偏离"
                
                # 没有信号时的基础预算保护逻辑
                else:
                    # 接近跌停保护
                    if (lastPrice - self.limit_down_price) / self.base_price < 0.01 and self.left_base_budget > 0 and lastPrice <= self.base_price:
                        base_buy_budget = self.left_base_budget
                        self.left_base_budget = 0
                        self.last_base_buy_tick_time = self.current_tick_steps
                        buy_reason = "接近跌停保护"
                    
                    # 超时补仓
                    elif (lastPrice < self.base_price * (1 - self.base_buy_down_min_pct) and 
                        (self.current_tick_steps - self.last_base_buy_tick_time > self.base_buy_gap_ticks or 
                        self.last_base_buy_tick_time == 0) and 
                        self.left_base_budget > 0):
                        base_buy_budget = min(self.left_base_budget, self.base_budget * 1/self.base_buy_times)
                        self.left_base_budget -= base_buy_budget
                        self.last_base_buy_tick_time = self.current_tick_steps
                        buy_reason = "超时补仓"
                    
                    # 尾盘保护
                    elif (self.current_tick_steps > self.base_max_buy_ticks and 
                        lastPrice < self.base_price * (1 - self.base_buy_down_min_pct) and 
                        self.left_base_budget > 0):
                        base_buy_budget = self.left_base_budget
                        self.left_base_budget = 0
                        self.last_base_buy_tick_time = self.current_tick_steps
                        buy_reason = "尾盘保护"
                
                # 记录买入信号
                total_buy_budget = buy_total_budget + base_buy_budget
                if total_buy_budget > 0:
                    if buy_total_budget > 0:
                        is_base_buy = False
                    else:
                        is_base_buy = True
                    # 计算买入数量 (整百股)
                    volume = int(total_buy_budget / sell1 / 100) * 100
                    if volume > 0:
                        self.buy_signals.append({
                            'time': time,
                            'price': lastPrice,
                            'sell1': sell1,
                            'amount': total_buy_budget,
                            'volume': volume,
                            'reason': buy_reason,
                            'base_price': self.base_price,
                            'current_step': self.current_tick_steps,
                            'stock_code': self.stock_code,
                            'strategy_name': self.strategy_name,
                            'signal_type': 'technical' if self.signal else 'protective',
                            'is_base_buy': is_base_buy
                        })
                
                self.pre_volume = volume
                
                # 达到最大tick数停止
                if self.current_tick_steps > self.max_buy_ticks:
                    break
                    
            except Exception as e:
                print(f"Error processing data at {data.get('time', 'unknown')}: {str(e)}")
                traceback.print_exc()
        
        return self.buy_signals