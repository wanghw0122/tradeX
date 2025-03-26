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

    def __eq__(self, other):
        if isinstance(other, XiaoCaoEnvironmentSecondLineV2):
            return (
                self.code == other.code and
                self.codeName == other.codeName and
                self.vol == other.vol and
                self.amt == other.amt and
                self.preClose == other.preClose and
                self.open == other.open and
                self.high == other.high and
                self.low == other.low and
                self.trade == other.trade and
                self.close == other.close and
                self.pctChange == other.pctChange and
                self.pctChangeRate == other.pctChangeRate and
                self.openPctChangeRate == other.openPctChangeRate and
                self.riseRate == other.riseRate and
                self.tradeTimestamp == other.tradeTimestamp and
                self.tradeDate == other.tradeDate and
                self.tradeStatus == other.tradeStatus and
                self.tradeSection == other.tradeSection and
                self.volRatio == other.volRatio and
                self.turnoverRatio == other.turnoverRatio and
                self.amplitude == other.amplitude and
                self.shortLineScore == other.shortLineScore and
                self.trendScore == other.trendScore and
                self.realShortLineScore == other.realShortLineScore and
                self.realTrendScore == other.realTrendScore and
                self.preShortLineScore == other.preShortLineScore and
                self.preTrendScore == other.preTrendScore and
                self.preRealShortLineScore == other.preRealShortLineScore and
                self.preRealTrendScore == other.preRealTrendScore and
                self.shortLineScoreChange == other.shortLineScoreChange and
                self.trendScoreChange == other.trendScoreChange and
                self.realShortLineScoreChange == other.realShortLineScoreChange and
                self.realTrendScoreChange == other.realTrendScoreChange and
                self.position == other.position and
                self.finalPosition == other.finalPosition and
                self.openPosition == other.openPosition and
                self.realPosition == other.realPosition and
                self.isHigh == other.isHigh and
                self.isMeso == other.isMeso and
                self.isLow == other.isLow and
                self.isBottom == other.isBottom and
                self.isFall == other.isFall and
                self.isPlummet == other.isPlummet
            )
        return False


states_codes = ['9A0001','9A0002','9A0003','9B0001','9B0002','9B0003','9C0001']

all_env_codes = ['9D0001','9D0002','9D0003','9E0001','9E0002','9E0003','9F0001','9F0002','9F0003','9F0004','9F0005','9F0006','9F0007','9F0008','9F0009','9A0001','9A0002',
                 '9A0003','9B0001','9B0002','9B0003','9C0001','9G0024','9G0026','9G0020','9G0002','9G0025','9G0027','9G0021','9G0001','9G0003','9G0004','9G0005','9G0006',
                 '9G0007','9G0008','9G0009','9G0010','9G0011','9G0012','9G0013','9G0014','9G0015','9G0016','9G0017','9G0018','9G0019','9G0028','9G0029','9G0030','9G0031',
                 '9G0032','9G0033','9G0034','9G0035','9G0036','9G0037','9G0038','9G0039','9G0040','9G0041','9G0042','9G0043','9G0044','9G0045']

# xiaocao_mod = ['9G0024','9G0026','9G0020','9G0025','9G0027','9G0021','9G0001','9G0002','9G0009','9G0010','9G0038','9G0005','9G0006','9G0019','9G0028','9G0030','9G0046','9G0047',
#                '9G0031','9G0032','9G0034','9G0033','9G0035','9G0037','9G0036','9G0095','9G0096','9G0007','9G0012','9G0013','9G0014','9G0039','9G0040','9G0099','9G0100','9G0048',
#                '9G0041','9G0042','9G0043','9G0015','9G0017','9G0008','9G0049','9G0050','9G0051','9G0052','9G0053','9G0056','9G0057','9G0016','9G0058','9G0003','9G0004','9G0101',
#                '9G0065','9G0066','9G0067','9G0068','9G0069','9G0071','9G0072','9G0073','9G0074','9G0077','9G0078','9G0079','9G0080','9G0081','9G0011','9G0083','9G0084','9G0085',
#                '9G0086','9G0087','9G0089','9G0090','9G0091','9G0092','9G0093','9G0018']

xiaocao_mod = [
    '9G0001', '9G0002', '9G0005', '9G0006', '9G0019', '9G0020', '9G0021', '9G0024', '9G0025', '9G0026',
    '9G0027', '9G0028', '9G0029', '9G0030', '9G0009', '9G0010', '9G0038', '9G0046', '9G0047', '9G0031',
    '9G0032', '9G0034', '9G0033', '9G0035', '9G0037', '9G0036', '9G0095', '9G0096', '9G0007', '9G0012',
    '9G0013', '9G0014', '9G0039', '9G0040', '9G0099', '9G0100', '9G0048', '9G0041', '9G0042', '9G0043',
    '9G0015', '9G0017', '9G0008', '9G0049', '9G0050', '9G0051', '9G0052', '9G0053', '9G0056', '9G0057',
    '9G0016', '9G0058', '9G0003', '9G0004', '9G0101', '9G0065', '9G0066', '9G0067', '9G0068', '9G0069',
    '9G0071', '9G0072', '9G0073', '9G0074', '9G0077', '9G0078', '9G0079', '9G0080', '9G0081', '9G0011',
    '9G0083', '9G0084', '9G0085', '9G0086', '9G0087', '9G0089', '9G0090', '9G0091', '9G0092', '9G0093',
    '9G0018', '9G0103', '9G0104', '9G0105', '9G0106', '9G0107', '9G0108', '9G0109', '9G0110', '9G0111',
    '9G0112', '9G0113', '9G0114', '9G0115', '9G0116', '9G0117', '9G0118', '9G0119', '9G0120', '9G0121',
    '9G0122', '9G0123', '9G0124', '9G0125', '9G0126', '9G0127', '9G0128', '9G0129', '9G0130', '9G0131',
    '9G0132', '9G0133', '9G0134', '9G0135', '9G0136', '9G0137', '9G0138', '9G0139', '9G0140', '9G0141',
    '9G0142', '9G0143', '9G0144', '9G0145', '9G0146', '9G0147', '9G0148', '9G0149', '9G0150', '9G0151',
    '9G0152', '9G0153', '9G0154', '9G0155', '9G0156', '9G0157', '9G0158', '9G0159', '9G0160', '9G0161',
    '9G0162', '9G0163', '9G0164', '9G0165', '9G0166', '9G0167', '9G0168', '9G0169', '9G0170', '9G0171',
    '9G0172', '9G0173', '9G0174', '9G0175', '9G0176', '9G0177', '9G0178', '9G0179', '9G0180', '9G0181',
    '9G0182', '9G0183', '9G0184', '9G0185', '9G0186', '9G0187', '9G0188', '9G0189', '9G0190', '9G0191',
    '9G0192', '9G0193', '9G0194', '9G0195', '9G0196', '9G0197', '9G0198'
]

def build_xiaocao_environment_second_line_v2_dict(date = get_current_date(), codes = []):
    rslt = build_http_request.xiao_cao_environment_second_line_v2(codes=codes, date = date)
    if rslt == None:
        return {}
    if ('errcode' in rslt and rslt['errcode']!= None) or ('ok' in rslt and not rslt['ok']):
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
build_xiaocao_environment_second_line_v2_dict_simple.__name__ = 'build_xiaocao_environment_second_line_v2_dict_simple'

build_xiaocao_environment_second_line_v2_dict_all= partial(build_xiaocao_environment_second_line_v2_dict, codes=all_env_codes)
build_xiaocao_environment_second_line_v2_dict_all.__name__ = 'build_xiaocao_environment_second_line_v2_dict_all'


build_xiaocao_mod_dict_all= partial(build_xiaocao_environment_second_line_v2_dict, codes=xiaocao_mod)
build_xiaocao_mod_dict_all.__name__ = 'build_xiaocao_mod_dict_all'