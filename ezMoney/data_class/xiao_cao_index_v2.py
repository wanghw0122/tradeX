from typing import List
from attr import dataclass
from date_utils.date import *
from logger import logger

@dataclass
class XiaoCaoIndexResult:
    code: str
    codeName: str
    trade: float
    tradeTimestamp: str
    pctChangeRate: float
    openPctChangeRate: float
    entityPctChangeRate: float
    ylimitupdays: int
    limitupdays: int
    jsjl: float
    xcjw: float
    jssb: float
    cjs: float
    relaxJssb: float
    relaxCjs: float
    directionCjs: float
    dwcjs: float
    lastDayLimitUpTime: float
    firstLimitUpDays: int
    isGestationLine: bool
    isBrokenPlate: bool
    isSmallHighOpen: bool
    isWeak: bool
    isLongShadow: bool
    isUpBroken: bool
    isFirstUpBroken: bool
    isDownBroken: bool
    isFirstDownBroken: bool
    isHalf: bool
    isBottom: bool
    isPreSt: bool
    isMedium: bool
    isHigh: bool
    isMeso: bool
    isLow: bool
    isFall: bool
    isPlummet: bool
    blockCodeList: List[str]
    industryBlockCodeList: List[str]
    blockCategoryCodeList: List[str]
    position: float
    finalPosition: float
    openPosition: float
    realPosition: float
    envCode: str
    realJssb: float
    realCjs: float
    jsjlTest: float
    jssbTest: float
    cjsTest: float
    isHighest: bool
    ybreakLimitUpDays: int
    isDownLongShadow: bool


