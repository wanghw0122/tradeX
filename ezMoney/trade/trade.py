# coding:utf-8
import time, datetime, traceback, sys
from xtquant import xtdata
from xtquant.xttrader import XtQuantTrader, XtQuantTraderCallback
from xtquant.xttype import StockAccount
from xtquant import xtconstant


# 定义一个类 创建类的实例 作为状态的容器
class _a():
    pass


A = _a()
A.bought_list = []
A.hsa = xtdata.get_stock_list_in_sector('沪深A股')


def interact():
    """执行后进入repl模式"""
    import code
    code.InteractiveConsole(locals=globals()).interact()


xtdata.download_sector_data()



class MyXtQuantTraderCallback(XtQuantTraderCallback):
    def on_disconnected(self):
        """
        连接断开
        :return:
        """
        print(datetime.datetime.now(), '连接断开回调')

    def on_stock_order(self, order):
        """
        委托回报推送
        :param order: XtOrder对象
        :return:
        """
        print(datetime.datetime.now(), '委托回调 投资备注', order.order_remark)

    def on_stock_trade(self, trade):
        """
        成交变动推送
        :param trade: XtTrade对象
        :return:
        """
        print(datetime.datetime.now(), '成交回调', trade.order_remark, f"委托方向(48买 49卖) {trade.offset_flag} 成交价格 {trade.traded_price} 成交数量 {trade.traded_volume}")

    def on_order_error(self, order_error):
        """
        委托失败推送
        :param order_error:XtOrderError 对象
        :return:
        """
        # print("on order_error callback")
        # print(order_error.order_id, order_error.error_id, order_error.error_msg)
        print(f"委托报错回调 {order_error.order_remark} {order_error.error_msg}")

    def on_cancel_error(self, cancel_error):
        """
        撤单失败推送
        :param cancel_error: XtCancelError 对象
        :return:
        """
        print(datetime.datetime.now(), sys._getframe().f_code.co_name)

    def on_order_stock_async_response(self, response):
        """
        异步下单回报推送
        :param response: XtOrderResponse 对象
        :return:
        """
        print(f"异步委托回调 投资备注: {response.order_remark}")

    def on_cancel_order_stock_async_response(self, response):
        """
        :param response: XtCancelOrderResponse 对象
        :return:
        """
        print(datetime.datetime.now(), sys._getframe().f_code.co_name)

    def on_account_status(self, status):
        """
        :param response: XtAccountStatus 对象
        :return:
        """
        print(datetime.datetime.now(), sys._getframe().f_code.co_name)


def create_trader(xt_acc,path, session_id):
    trader = XtQuantTrader(path, session_id,callback=MyXtQuantTraderCallback())
    trader.start()
    connect_result = trader.connect()
    trader.subscribe(xt_acc)
    return trader if connect_result == 0 else None


def try_connect(xt_acc,path):
    session_id_range = [i for i in range(100, 120)]

    import random
    random.shuffle(session_id_range)

    # 遍历尝试session_id列表尝试连接
    for session_id in session_id_range:
        trader = create_trader(xt_acc,path, session_id)
        if trader:
            print('连接成功，session_id:{}', session_id)
            return trader
        else:
            print('连接失败，session_id:{}，继续尝试下一个id', session_id)
            continue

    print('所有id都尝试后仍失败，放弃连接')
    return None


def get_xttrader(xt_acc,path):
    global xt_trader
    if xt_trader is None:
        xt_trader = try_connect(xt_acc,path)
    return xt_trader

if __name__ == '__main__':
    print("start")
    # 指定客户端所在路径, 券商端指定到 userdata_mini文件夹
    # 注意：如果是连接投研端进行交易，文件目录需要指定到f"{安装目录}\userdata"
    path = r'D:\qmt\userdata_mini'
    # 生成session id 整数类型 同时运行的策略不能重复

    xt_trader = None
    session_id = int(time.time())
    # 开启主动请求接口的专用线程 开启后在on_stock_xxx回调函数里调用XtQuantTrader.query_xxx函数不会卡住回调线程，但是查询和推送的数据在时序上会变得不确定
    # 详见: http://docs.thinktrader.net/vip/pages/ee0e9b/#开启主动请求接口的专用线程
    # xt_trader.set_relaxed_response_order_enabled(True)

    # 创建资金账号为 800068 的证券账号对象 股票账号为STOCK 信用CREDIT 期货FUTURE
    acc = StockAccount('8886660057', 'STOCK')


    xt_trader = get_xttrader(acc, path=path)

    if not xt_trader:
        raise Exception('交易接口连接失败')
    
    #取账号信息
    account_info = xt_trader.query_stock_asset(acc)
    #取可用资金
    available_cash = account_info.m_dCash

    print(acc.account_id, '可用资金', available_cash)
    #查账号持仓
    positions = xt_trader.query_stock_positions(acc)
    #取各品种 总持仓 可用持仓
    position_total_dict = {i.stock_code : i.m_nVolume for i in positions}
    position_available_dict = {i.stock_code : i.m_nCanUseVolume for i in positions}
    print(acc.account_id, '持仓字典', position_total_dict)
    print(acc.account_id, '可用持仓字典', position_available_dict)

    #买入 浦发银行 最新价 两万元
    stock = '600000.SH'
    target_amount = 2000
    full_tick = xtdata.get_full_tick([stock])
    print(f"{stock} 全推行情： {full_tick}")
    current_price = full_tick[stock]['lastPrice']
    #买入金额 取目标金额 与 可用金额中较小的
    buy_amount = min(target_amount, available_cash)
    #买入数量 取整为100的整数倍
    buy_vol = int(buy_amount / current_price / 100) * 100
    print(f"当前可用资金 {available_cash} 目标买入金额 {target_amount} 买入股数 {buy_vol}股")
    async_seq = xt_trader.order_stock_async(acc, stock, xtconstant.STOCK_BUY, buy_vol, xtconstant.FIX_PRICE, current_price,
                                            'strategy_name', stock)

    #卖出 500股
    stock = '513130.SH'
    #目标数量
    target_vol = 500
    #可用数量
    available_vol = position_available_dict[stock] if stock in position_available_dict else 0
    #卖出量取目标量与可用量中较小的
    sell_vol = min(target_vol, available_vol)
    print(f"{stock} 目标卖出量 {target_vol} 可用数量 {available_vol} 卖出 {sell_vol}股")
    if sell_vol > 0:
        async_seq = xt_trader.order_stock_async(acc, stock, xtconstant.STOCK_SELL, sell_vol, xtconstant.LATEST_PRICE,
                                                -1,
                                                'strategy_name', stock)
    print(f"下单完成 等待回调")
    


