from decimal import Decimal, ROUND_HALF_UP

# mods_code_to_name_dict = {
#     "9G0001": "红盘起爆",
#     "9G0002": "绿盘低吸",
#     "9G0003": "一进二弱转强",
#     "9G0004": "一进二中弱转强",
#     "9G0005": "中高位弱转强",
#     "9G0006": "中高位中弱转强",
#     "9G0007": "倒接力",
#     "9G0008": "首红断低吸",
#     "9G0009": "中高位连板打板",
#     "9G0010": "一进二打板",
#     "9G0011": "N半23",
#     "9G0012": "N半",
#     "9G0013": "N",
#     "9G0014": "孕线",
#     "9G0015": "红断低吸",
#     "9G0016": "首红断追涨",
#     "9G0017": "绿断低吸",
#     "9G0018": "长影追涨",
#     "9G0019": "小高开追涨",
#     "9G0020": "低位低吸",
#     "9G0021": "低位追涨",
#     "9G0024": "高位低吸",
#     "9G0025": "高位追涨",
#     "9G0026": "中位低吸",
#     "9G0027": "中位追涨",
#     "9G0028": "下跌低吸",
#     "9G0030": "下跌追涨",
#     "9G0031": "超跌追涨",
#     "9G0032": "断低吸",
#     "9G0033": "连断低吸",
#     "9G0034": "首断低吸",
#     "9G0035": "断追涨",
#     "9G0036": "连断追涨",
#     "9G0037": "首断追涨",
#     "9G0038": "首板打板",
#     "9G0039": "红盘起爆前3",
#     "9G0040": "绿盘低吸前3",
#     "9G0041": "高位断板低吸",
#     "9G0042": "中位断板低吸",
#     "9G0043": "低位断板低吸",
#     "9G0046": "最高低吸",
#     "9G0047": "最高追涨",
#     "9G0048": "最高断板低吸",
#     "9G0049": "首绿断低吸",
#     "9G0050": "最高断板追涨",
#     "9G0051": "高位断板追涨",
#     "9G0052": "中位断板追涨",
#     "9G0053": "低位断板追涨",
#     "9G0056": "红断追涨",
#     "9G0057": "绿断追涨",
#     "9G0058": "首绿断追涨",
#     "9G0065": "最高倒接力",
#     "9G0066": "高位倒接力",
#     "9G0067": "中位倒接力",
#     "9G0068": "低位倒接力",
#     "9G0069": "下跌倒接力",
#     "9G0071": "最高弱板倒接力",
#     "9G0072": "高位弱板倒接力",
#     "9G0073": "中位弱板倒接力",
#     "9G0074": "低位弱板倒接力",
#     "9G0077": "最高N字低吸",
#     "9G0078": "高位N字低吸",
#     "9G0079": "中位N字低吸",
#     "9G0080": "低位N字低吸",
#     "9G0081": "下跌N字低吸",
#     "9G0083": "最高孕线低吸",
#     "9G0084": "高位孕线低吸",
#     "9G0085": "中位孕线低吸",
#     "9G0086": "低位孕线低吸",
#     "9G0087": "下跌孕线低吸",
#     "9G0089": "最高小高开起爆",
#     "9G0090": "高位小高开起爆",
#     "9G0091": "中位小高开起爆",
#     "9G0092": "低位小高开起爆",
#     "9G0093": "下跌小高开起爆",
#     "9G0095": "一进二追涨",
#     "9G0096": "二板以上追涨",
#     "9G0099": "放宽低吸前3",
#     "9G0100": "放宽追涨前3",
#     "9G0101": "二进三以上弱转强"
# }

st_stocks = ['002306.SZ']

mods_code_to_name_dict = {
    '9G0092': '低位小高开起爆',
    '9G0091': '中位小高开起爆',
    '9G0090': '高位小高开起爆',
    '9G0096': '二板以上追涨',
    '9G0095': '一进二追涨',
    '9G0093': '下跌小高开起爆',
    '9G0133': '低强小低开低吸',
    '9G0012': 'N半',
    '9G0099': '放宽低吸前3',
    '9G0011': 'N半23',
    '9G0132': '中强大低开低吸',
    '9G0131': '中强中低开低吸',
    '9G0010': '一进二打板',
    '9G0130': '中强小低开低吸',
    '9G0137': '高强中高开追涨',
    '9G0016': '首红断追涨',
    '9G0015': '红断低吸',
    '9G0136': '高强小高开追涨',
    '9G0014': '孕线',
    '9G0135': '低强大低开低吸',
    '9G0013': 'N',
    '9G0134': '低强中低开低吸',
    '9G0019': '小高开追涨',
    '9G0018': '长影追涨',
    '9G0139': '中强小高开追涨',
    '9G0017': '绿断低吸',
    '9G0138': '高强大高开追涨',
    '9G0140': '中强中高开追涨',
    '9G0144': '低强大高开追涨',
    '9G0143': '低强中高开追涨',
    '9G0142': '低强小高开追涨',
    '9G0021': '低位追涨',
    '9G0020': '低位低吸',
    '9G0141': '中强大高开追涨',
    '9G0027': '中位追涨',
    '9G0148': '高位中强小低开低吸',
    '9G0147': '高位高强大低开低吸',
    '9G0026': '中位低吸',
    '9G0146': '高位高强中低开低吸',
    '9G0025': '高位追涨',
    '9G0145': '高位高强小低开低吸',
    '9G0024': '高位低吸',
    '9G0029': '超跌低吸',
    '9G0149': '高位中强中低开低吸',
    '9G0028': '下跌低吸',
    '9G0191': '低位高强中高开追涨',
    '9G0190': '低位高强小高开追涨',
    '9G0195': '低位中强大高开追涨',
    '9G0074': '低位弱板倒接力',
    '9G0194': '低位中强中高开追涨',
    '9G0073': '中位弱板倒接力',
    '9G0072': '高位弱板倒接力',
    '9G0193': '低位中强小高开追涨',
    '9G0192': '低位高强大高开追涨',
    '9G0071': '最高弱板倒接力',
    '9G0078': '高位N字低吸',
    '9G0111': '高位低强追涨',
    '9G0110': '高位中强追涨',
    '9G0198': '低位低强大高开追涨',
    '9G0077': '最高N字低吸',
    '9G0197': '低位低强中高开追涨',
    '9G0196': '低位低强小高开追涨',
    '9G0115': '低位高强追涨',
    '9G0114': '中位低强追涨',
    '9G0113': '中位中强追涨',
    '9G0079': '中位N字低吸',
    '9G0112': '中位高强追涨',
    '9G0119': '高位中强低吸',
    '9G0118': '高位高强低吸',
    '9G0117': '低位低强追涨',
    '9G0116': '低位中强追涨',
    '9G0081': '下跌N字低吸',
    '9G0080': '低位N字低吸',
    '9G0085': '中位孕线低吸',
    '9G0084': '高位孕线低吸',
    '9G0083': '最高孕线低吸',
    '9G0122': '中位中强低吸',
    '9G0001': '红盘起爆',
    '9G0089': '最高小高开起爆',
    '9G0121': '中位高强低吸',
    '9G0120': '高位低强低吸',
    '9G0087': '下跌孕线低吸',
    '9G0086': '低位孕线低吸',
    '9G0126': '低位低强低吸',
    '9G0005': '中高位弱转强',
    '9G0125': '低位中强低吸',
    '9G0004': '一进二中弱转强',
    '9G0124': '低位高强低吸',
    '9G0003': '一进二弱转强',
    '9G0002': '绿盘低吸',
    '9G0123': '中位低强低吸',
    '9G0009': '中高位连板打板',
    '9G0008': '首红断低吸',
    '9G0129': '高强大低开低吸',
    '9G0007': '倒接力',
    '9G0128': '高强中低开低吸',
    '9G0127': '高强小低开低吸',
    '9G0006': '中高位中弱转强',
    '9G0052': '中位断板追涨',
    '9G0173': '高位高强中高开追涨',
    '9G0172': '高位高强小高开追涨',
    '9G0051': '高位断板追涨',
    '9G0050': '最高断板追涨',
    '9G0171': '低位低强大低开低吸',
    '9G0170': '低位低强中低开低吸',
    '9G0056': '红断追涨',
    '9G0177': '高位中强大高开追涨',
    '9G0176': '高位中强中高开追涨',
    '9G0175': '高位中强小高开追涨',
    '9G0174': '高位高强大高开追涨',
    '9G0053': '低位断板追涨',
    '9G0179': '高位低强中高开追涨',
    '9G0058': '首绿断追涨',
    '9G0057': '绿断追涨',
    '9G0178': '高位低强小高开追涨',
    '9G0180': '高位低强大高开追涨',
    '9G0184': '中位中强小高开追涨',
    '9G0183': '中位高强大高开追涨',
    '9G0182': '中位高强中高开追涨',
    '9G0181': '中位高强小高开追涨',
    '9G0100': '放宽追涨前3',
    '9G0188': '中位低强中高开追涨',
    '9G0067': '中位倒接力',
    '9G0187': '中位低强小高开追涨',
    '9G0066': '高位倒接力',
    '9G0186': '中位中强大高开追涨',
    '9G0065': '最高倒接力',
    '9G0185': '中位中强中高开追涨',
    '9G0104': '高强追涨',
    '9G0103': '高强低吸',
    '9G0069': '下跌倒接力',
    '9G0189': '中位低强大高开追涨',
    '9G0101': '二进三以上弱转强',
    '9G0068': '低位倒接力',
    '9G0108': '低强追涨',
    '9G0107': '低强低吸',
    '9G0106': '中强追涨',
    '9G0105': '中强低吸',
    '9G0109': '高位高强追涨',
    '9G0030': '下跌追涨',
    '9G0151': '高位低强小低开低吸',
    '9G0150': '高位中强大低开低吸',
    '9G0034': '首断低吸',
    '9G0155': '中位高强中低开低吸',
    '9G0154': '中位高强小低开低吸',
    '9G0033': '连断低吸',
    '9G0153': '高位低强大低开低吸',
    '9G0032': '断低吸',
    '9G0152': '高位低强中低开低吸',
    '9G0031': '超跌追涨',
    '9G0038': '首板打板',
    '9G0159': '中位中强大低开低吸',
    '9G0037': '首断追涨',
    '9G0158': '中位中强中低开低吸',
    '9G0036': '连断追涨',
    '9G0157': '中位中强小低开低吸',
    '9G0035': '断追涨',
    '9G0156': '中位高强大低开低吸',
    '9G0039': '红盘起爆前3',
    '9G0162': '中位低强大低开低吸',
    '9G0041': '高位断板低吸',
    '9G0161': '中位低强中低开低吸',
    '9G0040': '绿盘低吸前3',
    '9G0160': '中位低强小低开低吸',
    '9G0166': '低位中强小低开低吸',
    '9G0165': '低位高强大低开低吸',
    '9G0043': '低位断板低吸',
    '9G0164': '低位高强中低开低吸',
    '9G0042': '中位断板低吸',
    '9G0163': '低位高强小低开低吸',
    '9G0049': '首绿断低吸',
    '9G0169': '低位低强小低开低吸',
    '9G0048': '最高断板低吸',
    '9G0168': '低位中强大低开低吸',
    '9G0047': '最高追涨',
    '9G0167': '低位中强中低开低吸',
    '9G0046': '最高低吸'
}

mods_name_to_code_dict = {v: k for k, v in mods_code_to_name_dict.items()}

all_codes = list(mods_code_to_name_dict.keys())

all_names = list(mods_code_to_name_dict.values())


# 0: 
# MONITOR_TRADE_TYPE = 0

# 止盈
STOP_PROFIT_TRADE_TYPE = 1
# 止损
STOP_LOSS_TRADE_TYPE = 2
# 最后一个交易日
LAST_TRADE_DAY_TRADE_TYPE = 3
# 盈利
PROFIT_TRADE_TYPE = 4
# 涨停
LIMIT_UP_TRADE_TYPE = 5
# 跌停
LIMIT_DOWN_TRADE_TYPE = 6

class OpenStatus:
    # 低开
    DOWN_OPEN = 0
    # 平开
    FLAT_OPEN = 1
    # 高开
    UP_OPEN = 2

class OpenTradeDirection:
    # 高走
    UP = 0
    # 低走
    DOWN = 1


class StockStatus:
    UNKNOWN = -1
    # 冷启动
    COLD_START = 0
    # 均线下
    AVG_DOWN = 1
    # 均线上
    AVG_UP = 2
    # 低走均线下
    LOW_AVG_DOWN = 3
    # 高走均线上
    HIGH_AVG_UP = 4

    #低开低走
    DOWN_LOW_AVG_DOWN = 5
    #低开高走
    DOWN_HIGH_AVG_UP = 6
    #高开低走
    UP_LOW_AVG_DOWN = 7
    #高开高走
    UP_HIGH_AVG_UP = 8

    # 观测均线下
    OBSERVE_AVG_DOWN = 5


class LimitUpStockStatus:
    # 未知
    UNKNOWN = 0
    # 涨停
    LIMIT_UP = 1
    # 跌停
    LIMIT_DOWN = 2
    # 未涨停
    UNLIMITED = 3
    # 平滑涨停
    SMOOTH_LIMIT_UP = 4
    # 平滑跌停
    SMOOTH_LIMIT_DOWN = 5
    # 触涨停
    TOUCH_LIMIT_UP = 6
    # 触跌停
    TOUCH_LIMIT_DOWN = 7
    # 封涨停
    CLOSE_LIMIT_UP = 8

class LimitUpHitType:
    # 涨停板
    LIMIT_UP = 0
    # 上午板
    AM_TIME = 1
    # 下午板
    PM_TIME = 2
    # 确定板，只要上板就买入
    SURE_TIME = 3
    # 排板
    SORT = 4
    # 回封板
    BACK_OPEN = 5
    # 缩量板
    SMALL_VOLUME = 6
    # 换手板
    CHANGE_HAND = 7
    # 10点前板
    BEFORE_10 = 8
    # 10点半前板
    BEFORE_10_30 = 9
    # 已触停板
    TOUCH_STOP = 10


class RowIdStatus:
    # 未下单
    UNPROCESSED = 0
    # 已下单
    PLACED = 1
    # 部分成功
    PARTIALLY_BOUGHT = 2
    # 已买入
    BOUGHT = 3
    # 已取消
    CANCELLED = 4

def get_row_id_status(input_num):
    if input_num == 0:
        return RowIdStatus.UNPROCESSED
    elif input_num == 1:
        return RowIdStatus.PLACED
    elif input_num == 2:
        return RowIdStatus.BOUGHT
    return RowIdStatus.UNPROCESSED


db_path= r'D:\workspace\TradeX\ezMoney\sqlite_db\strategy_data.db'


def get_limit_price(price, stock_code = ''):
    if stock_code and stock_code in st_stocks:
        limit_down_price = float(Decimal(str(price * 0.95)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
        limit_up_price = float(Decimal(str(price * 1.05)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
    else:
        limit_down_price = float(Decimal(str(price * 0.9)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
        limit_up_price = float(Decimal(str(price * 1.1)).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP))
    return limit_down_price, limit_up_price



def modify_string_slice(input_str, index, new_value):
    """
    使用切片修改指定位置的字符值

    :param input_str: 输入的字符串
    :param index: 要修改的位置索引
    :param new_value: 新的值，只能是 '0' 或 '1'
    :return: 修改后的字符串
    """
    if new_value not in ['0', '1']:
        raise ValueError("新值必须是 '0' 或 '1'")
    if index < 0 or index >= len(input_str):
        raise IndexError("索引超出范围")
    
    return input_str[:index] + new_value + input_str[index + 1:]


def match_binary_string(binary_str, pattern_strs):
    """
    根据输入的 11 位二进制字符串和待匹配字符串，检查是否所有匹配位置在二进制字符串中都为 1。

    :param binary_str: 11 位的二进制字符串，每个位置为 0 或 1
    :param pattern_str: 待匹配的字符串，每个位置为 0 - 9 或 a - z
    :return: 若所有匹配位置在二进制字符串中都为 1 则返回 True，否则返回 False
    """
    if len(binary_str) != 11:
        raise ValueError("二进制字符串长度必须为 11")
    
    def match_string(binary_str, pattern_str):
        for char in pattern_str:
            try:
                if char.isdigit():
                    index = int(char)
                else:
                    index = ord(char) - ord('a') + 10
                if index < 0 or index >= 11 or binary_str[index] != '1':
                    return False
            except Exception:
                return False
        return True
            
    for pattern_str in pattern_strs:
        if match_string(binary_str, pattern_str):
            return True
    return False

if __name__ == "__main__":
    # print(get_row_id_status(0))
    # print(type(get_row_id_status(0)))
    print(match_binary_string("00010100111", ['13a','35']))