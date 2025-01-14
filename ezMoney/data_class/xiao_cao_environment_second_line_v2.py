from date_utils.date import *
from http_request import build_http_request
from attr import dataclass
from logger import logger

from functools import partial

@dataclass
class XiaoCaoEnvironmentSecondLineV2:
    code: str
    codeName: str
    vol: int
    amt: int
    preClose: float
    open: float
    high: float
    low: float
    trade: float
    close: float
    pctChange: float
    pctChangeRate: float
    openPctChangeRate: float
    riseRate: float
    tradeTimestamp: int
    tradeDate: str
    tradeStatus: int
    tradeSection: int
    volRatio: float
    turnoverRatio: float
    amplitude: float
    shortLineScore: float
    trendScore: float
    realShortLineScore: float
    realTrendScore: float
    preShortLineScore: float
    preTrendScore: float
    preRealShortLineScore: float
    preRealTrendScore: float
    shortLineScoreChange:float
    trendScoreChange: float
    realShortLineScoreChange: float
    realTrendScoreChange: float
    position: int
    finalPosition: int
    openPosition: int
    realPosition: int
    isHigh: bool
    isMeso: bool
    isLow: bool
    isBottom: bool
    isFall: bool
    isPlummet: bool


states_codes = ['9A0001','9A0002','9A0003','9B0001','9B0002','9B0003','9C0001']

all_env_codes = ['9D0001','9D0002','9D0003','9E0001','9E0002','9E0003','9F0001','9F0002','9F0003','9F0004','9F0005','9F0006','9F0007','9F0008','9F0009','9A0001','9A0002','9A0003','9B0001','9B0002','9B0003','9C0001','9G0024','9G0026','9G0020','9G0002','9G0025','9G0027','9G0021','9G0001','9G0003','9G0004','9G0005','9G0006','9G0007','9G0008','9G0009','9G0010','9G0011','9G0012','9G0013','9G0014','9G0015','9G0016','9G0017','9G0018','9G0019','9G0028','9G0029','9G0030','9G0031','9G0032','9G0033','9G0034','9G0035','9G0036','9G0037','9G0038','9G0039','9G0040','9G0041','9G0042','9G0043','9G0044','9G0045']

def build_xiaocao_environment_second_line_v2_dict(date = get_current_date(), codes = []):
    rslt = build_http_request.xiao_cao_environment_second_line_v2(codes=codes, date = date)
    if rslt == None:
        return {}
    if 'errcode' in rslt and rslt['errcode']!= None:
        logger.error("xiao_cao_environment_second_line_v2 error! errcode: " + rslt['errcode'])
    
    if'result' not in rslt:
        logger.error("xiao_cao_environment_second_line_v2 no result.")
        return {}
    block_list = rslt['result']
    block_dict = {}
    block_name_dict = {}
    for item in block_list:
        if 'code' not in item:
            logger.error("xiao_cao_environment_second_line_v2 no code.")
            continue
        block_dict[item['code']] = XiaoCaoEnvironmentSecondLineV2(**item)
        block_name_dict[item['code']] = item['codeName']
    return block_dict, block_name_dict


build_xiaocao_environment_second_line_v2_dict_simple = partial(build_xiaocao_environment_second_line_v2_dict, codes=states_codes)

build_xiaocao_environment_second_line_v2_dict_all= partial(build_xiaocao_environment_second_line_v2_dict, codes=all_env_codes)
