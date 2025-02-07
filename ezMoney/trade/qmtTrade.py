import pprint
import re
import time, datetime, traceback, sys
from numpy import true_divide
from xtquant import xttrader
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant
from multiprocessing import Manager

from logger import logger, order_logger



class MyXtQuantTraderCallback(XtQuantTraderCallback):

    def __init__(self):
        self.qmt = None

    def set_qmt(self, qmt):
        self.qmt = qmt
    def on_disconnected(self):
        """
        连接断开
        :return:
        """
        order_logger.error("连接断开回调")
        logger.error("连接断开回调")

    def on_stock_order(self, order):
        """
        委托回报推送
        :param order: XtOrder对象
        :return:
        """
        order_id = order.order_id
        logger.info(f"委托回调 投资备注 {order.order_remark}")

    def on_stock_trade(self, trade):
        """
        成交变动推送
        :param trade: XtTrade对象
        :return:
        """
        order_id = trade.order_id
        if order_id in self.qmt.orders_dict:
            (stock_code, price, volume, order_type, order_remark, time_stemp) = self.qmt.orders_dict[order_id]
            traded_amount = trade.traded_amount
            traded_volume = trade.traded_volume
            trade_order_remark = trade.order_remark
            trade_stock_code = trade.stock_code
            trade_order_type = trade.order_type
            traded_price = trade.traded_price
            traded_time = trade.traded_time

            if traded_volume > 0:
                order_logger.info(f"成交回调后实际：订单号 {order_id} 投资备注 {trade_order_remark} 股票代码 {trade_stock_code} 委托方向 {trade_order_type} 成交价格 {traded_price} 成交数量 {traded_volume} 成交金额 {traded_amount} 成交时间 {traded_time}")
                order_logger.info(f"成交前订单申报：订单号 {order_id} 投资备注 {order_remark} 股票代码 {stock_code} 委托类型 {order_type} 委托价格 {price} 委托数量 {volume}  委托时间 {time_stemp} 价格差异 {traded_price - price} 滑点比例 {(traded_price - price) / price} 数量差异 {traded_volume - volume}")
        logger.info(f"成交回调: {trade.order_remark}, {trade.stock_code} 委托方向(48买 49卖) {trade.offset_flag} 成交价格 {trade.traded_price} 成交数量 {trade.traded_volume}")

    def on_order_error(self, order_error):
        """
        委托失败推送
        :param order_error:XtOrderError 对象
        :return:
        """
        order_id = order_error.order_id
        order_logger.error(f"委托报错回调 {order_error.order_remark} {order_error.error_msg}")
        logger.error(f"委托报错回调 {order_error.order_remark} {order_error.error_msg}")

    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送
        :param cancel_error: XtCancelError 对象
        :return:
        """
        order_logger.error(f"撤单报错回调 {cancel_error.order_id} {cancel_error.error_msg}")
        logger.error(f"撤单报错回调 {cancel_error.order_id} {cancel_error.error_msg}")

    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送
        :param response: XtOrderResponse 对象
        :return:
        """
        order_id = response.order_id
        seq = response.seq
        (stock_code, price, volume, order_type, order_remark) = self.qmt.seq_ids_dict[seq]
        if order_id < 0:
            order_logger.error(f"异步委托失败，股票代码: {stock_code}, 委托价格: {price}, 委托数量: {volume}")
            logger.error(f"异步委托失败，股票代码: {stock_code}, 委托价格: {price}, 委托数量: {volume}")
        else:
            order_logger.info(f"异步委托成功，股票代码: {stock_code}, 委托价格: {price}, 委托数量: {volume}")
            logger.info(f"异步委托成功，股票代码: {stock_code}, 委托价格: {price}, 委托数量: {volume}")
            self.qmt.orders.append(order_id)
            self.qmt.orders_dict[order_id] = (stock_code, price, volume, order_type, order_remark, time.time())
        logger.info(f"异步委托回调 投资备注: {response.order_remark}")


    def on_cancel_order_stock_async_response(self, response):
        """
        :param response: XtCancelOrderResponse 对象
        :return:
        """
        order_logger.info(sys._getframe().f_code.co_name)
        logger.info(sys._getframe().f_code.co_name)

    def on_account_status(self, status):
        """
        :param response: XtAccountStatus 对象
        :return:
        """
        order_logger.info(sys._getframe().f_code.co_name)
        logger.info(sys._getframe().f_code.co_name)


# def create_trader(xt_acc,path, session_id):
#     trader = XtQuantTrader(path, session_id,callback=MyXtQuantTraderCallback())
#     trader.start()
#     connect_result = trader.connect()
#     trader.subscribe(xt_acc)
#     return trader if connect_result == 0 else None


# def try_connect(xt_acc,path):
#     session_id_range = [i for i in range(100, 120)]

#     import random
#     random.shuffle(session_id_range)

#     # 遍历尝试session_id列表尝试连接
#     for session_id in session_id_range:
#         trader = create_trader(xt_acc,path, session_id)
#         if trader:
#             print('连接成功，session_id:{}', session_id)
#             return trader
#         else:
#             print('连接失败，session_id:{}，继续尝试下一个id', session_id)
#             continue

#     print('所有id都尝试后仍失败，放弃连接')
#     return None


# def get_xttrader(xt_acc,path):
#     xt_trader = try_connect(xt_acc,path)
#     return xt_trader

class QMTTrader:
    def __init__(self, path, acc_id):
        logger.info('初始化QMTTrader')
        self.acc = StockAccount(acc_id, 'STOCK')
        self.callback = MyXtQuantTraderCallback()
        # self.callback.qmt = self
        self.trader = self.get_xttrader(path)
        if not self.trader:
            logger.error('QMT未启动，交易接口连接失败, 退出执行.')
            raise Exception('QMT交易接口连接失败')
        else:
            logger.info('QMT交易接口连接成功')
        self.all_stocks = {}
        self.build_all_stocks()

    def init_order_context(self):
        manager = Manager()
        self.orders = manager.list()
        self.seq_ids_dict = manager.dict()
        self.orders_dict = manager.dict()

    def build_all_stocks(self):
        all_stocks = xtdata.get_stock_list_in_sector('沪深A股')
        for stock in all_stocks:
            if stock.startswith('60') or stock.startswith('00'):
                code = stock.split('.')[0]
                self.all_stocks[code] = stock
        logger.info(f"构建全市场股票字典完毕。 共{len(self.all_stocks)}个")
    
    def get_xttrader(self, path):
        session_id_range = [i for i in range(100, 120)]
        import random
        random.shuffle(session_id_range)

        # 遍历尝试session_id列表尝试连接
        for session_id in session_id_range:
            trader = XtQuantTrader(path, session_id,callback=self.callback)
            trader.start()
            connect_result = trader.connect()
            if trader and connect_result == 0:
                logger.info(f'连接成功，session_id:{session_id}')
                trader.subscribe(self.acc) 
                return trader
            else:
                logger.info(f'连接失败，session_id:{session_id}，继续尝试下一个id')
                continue
        logger.info('所有id都尝试后仍失败，放弃连接')
        return None

    def buy(self, stock_code, price, volume, order_type=xtconstant.FIX_PRICE, order_remark='', sync = True, orders_dict = None, orders = None):
        """
        买入股票

        :param account: 资金账号
        :param stock_code: 股票代码
        :param price: 买入价格
        :param volume: 买入数量
        :param order_type: 委托类型，默认为固定价格委托
        :param order_remark: 委托备注，默认为空
        :return: 委托ID
        """
        if sync:
            if order_type == xtconstant.FIX_PRICE:
                order_id = self.trader.order_stock(self.acc, stock_code, xtconstant.STOCK_BUY, volume, order_type, price, order_remark)
            else:
                order_id = self.trader.order_stock(self.acc, stock_code, xtconstant.STOCK_BUY, volume, order_type, 0, order_remark)
            if order_id < 0:
                logger.error(f"委托失败，股票代码: {stock_code}, 委托价格: {price}, 委托类型: {order_type}, 委托数量: {volume}, 委托ID: {order_id}")
                order_logger.error(f"委托失败，股票代码: {stock_code}, 委托价格: {price}, 委托类型: {order_type}, 委托数量: {volume}, 委托ID: {order_id}")
            else:
                logger.info(f"委托成功，股票代码: {stock_code}, 委托价格: {price}, 委托类型: {order_type}, 委托数量: {volume}, 委托ID: {order_id}")
                order_logger.info(f"委托成功，股票代码: {stock_code}, 委托价格: {price}, 委托类型: {order_type}, 委托数量: {volume}, 委托ID: {order_id}")
                if orders_dict != None:
                    orders_dict[order_id] = (stock_code, price, volume, order_type, order_remark, time.time())
                if orders != None:
                    orders.append(order_id)
            return order_id
        else:
            seq_id = self.trader.order_stock_async(self.acc, stock_code, xtconstant.STOCK_BUY, volume, order_type, price, order_remark)
            self.seq_ids_dict[seq_id] = (stock_code, price, volume, order_type, order_remark)
            return seq_id


    def buy_quickly(self, stock_code, cash, min_vol = -1, max_vol = -1, max_cash = -1, order_type=xtconstant.FIX_PRICE, order_remark='', sync = True, price_type = 0, orders_dict = None, orders = None):

        if max_cash > 0:
            cash = min(cash, max_cash)
        if stock_code in self.all_stocks:
            stock_code = self.all_stocks[stock_code]
        full_tick = xtdata.get_full_tick([stock_code])
        (account_id, account_cash, account_frozen_cash, account_market_value, account_total_asset) = self.get_account_info()
        
        if not full_tick or len(full_tick) == 0:
            logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            return
        elif stock_code not in full_tick:
            logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            return
        elif 'lastPrice' not in full_tick[stock_code]:
            logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            return
        elif 'askPrice' not in full_tick[stock_code]:
            logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            order_logger.error(f"获取全推行情失败 {stock_code}, 全推行情： {full_tick}")
            return
        else:
            logger.info(f"{stock_code} 全推行情： {full_tick}")
        
        current_price = full_tick[stock_code]['lastPrice']
        ask_price = full_tick[stock_code]['askPrice']
        bid_price = current_price
        price1 = ask_price[0]
        price2 = ask_price[1]
        price3 = ask_price[2]

        if price_type == 0:
            bid_price = current_price
        elif price_type == 1 and price1 > 0 and price1 > current_price:
            bid_price = price1
        elif price_type == 2 and price2 > 0 and price2 > current_price:
            bid_price = price2
        elif price_type == 3 and price3 > 0 and price3 > current_price:
            bid_price = price3
        else:
            bid_price = current_price

        if bid_price <= 0:
            logger.error(f"price error.： {full_tick}")
            return

        #买入金额 取目标金额 与 可用金额中较小的
        buy_amount = min(account_cash, cash)
        #买入数量 取整为100的整数倍
        buy_vol = int(buy_amount / bid_price / 100) * 100
        if max_vol > 0:
            buy_vol = min(buy_vol, max_vol)
        if min_vol > 0:
            buy_vol = max(buy_vol, min_vol)
        if buy_vol == 0:
            logger.error(f"当前可用资金 {account_cash} 目标买入金额 {cash} 买入股数 {buy_vol}股")
            return
        logger.info(f"当前可用资金 {account_cash} 目标买入金额 {cash} 买入股数 {buy_vol}股")
        id = self.buy(stock_code, bid_price, buy_vol, order_type, order_remark, sync, orders_dict=orders_dict, orders=orders)
        order_logger.info(f"下单买入股票 {stock_code} 买入股数 {buy_vol} 买入金额 {buy_amount} 买入价格 {bid_price} 买入一价 {price1} 买入二价 {price2} 买入三价{price3} 委托ID {id}")
        return id

    def sell(self, stock_code, price, volume, order_type=xtconstant.FIX_PRICE, order_remark=''):
        """
        卖出股票

        :param account: 资金账号
        :param stock_code: 股票代码
        :param price: 卖出价格
        :param volume: 卖出数量
        :param order_type: 委托类型，默认为固定价格委托
        :param order_remark: 委托备注，默认为空
        :return: 委托ID
        """
        return self.trader.order_stock_async(self.acc, stock_code, xtconstant.STOCK_SELL, volume, order_type, price, order_remark)

    def cancel_order(self, order_id, sync = True):
        """
        撤单

        :param account: 资金账号
        :param order_id: 委托ID
        :return: 撤单结果
        """
        if sync:
            return self.trader.cancel_order_stock(self.acc, order_id)
        return self.trader.cancel_order_stock_async(self.acc, order_id)

    def get_account_info(self):
        """
        获取账户信息

        :return: 账户信息
        """
        account_info = self.trader.query_stock_asset(self.acc)
        account_info_tuple = (account_info.account_id, account_info.cash, account_info.frozen_cash, account_info.market_value, account_info.total_asset)
        logger.info(f"账户ID: {account_info_tuple[0]}, 可用资金: {account_info_tuple[1]}, 冻结资金: {account_info_tuple[2]}, 市值: {account_info_tuple[3]}, 总资产: {account_info_tuple[4]}")
        return account_info_tuple


    def get_position_info(self):
        """
        获取持仓信息

        :param account: 资金账号
        :return: 持仓信息
        """
        return self.trader.query_stock_positions(self.acc)
    

    def get_tradable_stocks(self):
        """
        获取可交易股票数据

        :param account: 资金账号
        :return: 可交易股票数据列表，每个元素为一个字典，包含股票代码和可卖出数量
        """
        tradable_stocks = []

        # 获取账户持仓信息
        positions = self.get_position_info()

        for position in positions:
            stock_code = position.stock_code
            available_qty = position.can_use_volume
            quantity = position.volume

            logger.info(f"股票代码: {stock_code}, 可卖出数量: {available_qty}, 持仓数量: {quantity}")

            tradable_stocks.append({
                'stock_code': stock_code,
                'available_qty': available_qty,
                'quantity': quantity
            })

        return tradable_stocks
    
    def sell_all_holdings(self, order_remark=''):
        """
        卖出所有持仓股票

        :param account: 资金账号
        :return: 卖出结果
        """
        now = datetime.datetime.now()
        # if now.hour > 0:
        #     logger.error(f"当前时间 {now} 非0点时间，无法自动卖出")
        #     return
        logger.info(f"开始卖出所有持仓股票")

        hold_positions = self.get_tradable_stocks()
        sell_results = []

        for position in hold_positions:
            stock_code = position['stock_code']
            quantity = position['available_qty']
            limit_down_price = self.calculate_limit_down_price(stock_code)

            logger.info(f"准备挂单卖出 股票代码: {stock_code}, 可卖出数量: {quantity}, 卖出跌停价: {limit_down_price}")
            if limit_down_price:
                sell_result = self.sell(stock_code, limit_down_price, quantity)
                sell_results.append({
                    'stock_code': stock_code,
                    'quantity': quantity,
                    'sell_price': limit_down_price,
                    'sell_result': sell_result
                })
                self.seq_ids_dict[sell_result] = (stock_code, limit_down_price, quantity, xtconstant.FIX_PRICE, order_remark)
            else:
                logger.error(f"股票 {stock_code} 的跌停价计算错误，无法卖出")
        return sell_results
    
    def calculate_limit_down_price(self, stock_code):
        """
        计算第二天跌停价

        :param stock_code: 股票代码
        :return: 第二天跌停价，如果计算失败则返回 None
        """
        try:
            full_tick = xtdata.get_full_tick([stock_code])
            if full_tick and 'lastPrice' in full_tick[stock_code]:
                last_price = full_tick[stock_code]['lastPrice']
                print(f"last_price {last_price}")
                from decimal import Decimal, ROUND_HALF_UP
                limit_down_price = Decimal(str(last_price * 0.9)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)
                return limit_down_price
            else:
                logger.error(f"无法获取股票 {stock_code} 的最新价")
                return None
        except Exception as e:
            logger.error(f"计算股票 {stock_code} 的跌停价时发生错误: {e}")
            return None

    
    def set_running(self):
        self.trader.run_forever()
    
    def cancel_active_orders(self):
        """
        撤单所有未成交且可撤单的股票

        :param account: 资金账号
        :return: 撤单结果
        """
        cancel_results = []
        active_orders = self.get_all_orders(cancelable_only  = True)
        for order in active_orders:
            order_id = order['order_id']
            cancel_result = self.cancel_order(order_id, sync=True)
            cancel_results.append({
                'order_id': order_id,
                'cancel_result': cancel_result
            })

        return cancel_results
    

    def get_all_orders(self, cancelable_only = False):
        """
        获取当前委托、未成交且可撤单的股票

        :param account: 资金账号
        :return: 满足条件的委托信息列表，每个元素为一个字典，包含股票代码、委托数量、委托价格等信息
        """
        active_orders = []

        # 获取账户委托信息
        orders = self.trader.query_stock_orders(self.acc, cancelable_only=cancelable_only)

        for order in orders:
            active_orders.append({
                'stock_code': order.stock_code,
                'order_id': order.order_id,
                'order_volume': order.order_volume,
                'order_type': order.order_type,
                'price': order.price,
                'order_status': order.order_status,
                'strategy_name': order.strategy_name,
                'traded_volume': order.traded_volume,
                'status_msg': order.status_msg
            })

        return active_orders



# 使用示例
if __name__ == '__main__':
    path = r'D:\qmt\userdata_mini'  # QMT客户端路径
    
    acc_id = '8886660057'

    # 创建QMTTrader实例
    qmt_trader = QMTTrader(path, acc_id)

    print("download")
    xtdata.download_history_data('000785.SZ', '1d', start_time='', end_time='20250114')

    # 买入股票
    order_id = qmt_trader.buy_quickly('000785.SZ', 1000, sync=False)
    print(f"买入委托ID: {order_id}")

    

    # # 卖出股票
    # order_id = qmt_trader.sell('600000.SH', 11.0, 50)
    # print(f"卖出委托ID: {order_id}")

    # # 撤单
    # cancel_result = qmt_trader.cancel_order(order_id)
    # print(f"撤单结果: {cancel_result}")

    # 获取账户信息
    # account_info = qmt_trader.get_account_info()
    # print(f"账户信息: {account_info}")

    # get_tradable_stocks = qmt_trader.get_tradable_stocks()
    # print(f"股票数据: {get_tradable_stocks}")

    qmt_trader.set_running()
