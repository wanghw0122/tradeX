from typing import List, Optional
from date_utils.date import *

from dataclasses import dataclass

@dataclass
class XiaoCaoIndexResult:
    code: Optional[str] = ""
    codeName: Optional[str] = ""
    trade: Optional[float] = 0.0
    tradeTimestamp: Optional[str] = ""
    pctChangeRate: Optional[float] = 0.0
    openPctChangeRate: Optional[float] = 0.0
    entityPctChangeRate: Optional[float] = 0.0
    ylimitupdays: Optional[int] = 0
    limitupdays: Optional[int] = 0
    jsjl: Optional[float] = 0.0
    xcjw: Optional[float] = 0.0
    jssb: Optional[float] = 0.0
    cjs: Optional[float] = 0.0
    relaxJssb: Optional[float] = 0.0
    relaxCjs: Optional[float] = 0.0
    directionCjs: Optional[float] = 0.0
    dwcjs: Optional[float] = 0.0
    lastDayLimitUpTime: Optional[float] = 0.0
    firstLimitUpDays: Optional[int] = 0
    isGestationLine: Optional[bool] = False
    isBrokenPlate: Optional[bool] = False
    isSmallHighOpen: Optional[bool] = False
    isMiddleHighOpen: Optional[bool] = False
    isLargeHighOpen: Optional[bool] = False
    isSmallLowOpen: Optional[bool] = False
    isMiddleLowOpen: Optional[bool] = False
    isLargeLowOpen: Optional[bool] = False
    isWeak: Optional[bool] = False
    isLongShadow: Optional[bool] = False
    isUpBroken: Optional[bool] = False
    isFirstUpBroken: Optional[bool] = False
    isDownBroken: Optional[bool] = False
    isFirstDownBroken: Optional[bool] = False
    isHalf: Optional[bool] = False
    isBottom: Optional[bool] = False
    isPreSt: Optional[bool] = False
    isMedium: Optional[bool] = False
    isHigh: Optional[bool] = False
    isMeso: Optional[bool] = False
    isLow: Optional[bool] = False
    isFall: Optional[bool] = False
    isPlummet: Optional[bool] = False
    blockCodeList: Optional[List[str]] = None
    industryBlockCodeList: Optional[List[str]] = None
    blockCategoryCodeList: Optional[List[str]] = None
    position: Optional[float] = 0.0
    finalPosition: Optional[float] = 0.0
    openPosition: Optional[float] = 0.0
    realPosition: Optional[float] = 0.0
    envCode: Optional[str] = ""
    realJssb: Optional[float] = 0.0
    realCjs: Optional[float] = 0.0
    jsjlTest: Optional[float] = 0.0
    jssbTest: Optional[float] = 0.0
    cjsTest: Optional[float] = 0.0
    isHighest: Optional[bool] = False
    ybreakLimitUpDays: Optional[int] = 0
    isDownLongShadow: Optional[bool] = False
    xcjwV2: Optional[float] = 0.0
    jssbV2: Optional[float] = 0.0
    cjsV2: Optional[float] = 0.0
    isStrengthHigh: Optional[bool] = False
    isStrengthMiddle: Optional[bool] = False
    isStrengthLow: Optional[bool] = False
    isStrengthIncrease: Optional[bool] = False
    isStrengthReduct: Optional[bool] = False
    shortLineScore: Optional[float] = 0.0
    shortLineScoreChange: Optional[float] = 0.0
    jsjlBlock: Optional[float] = 0.0
    jssbBlock: Optional[float] = 0.0
    cjsBlock: Optional[float] = 0.0
    directionCjsV2: Optional[float] = 0.0
    circulationMarketValue: Optional[float] = 0.0
    cgyk: Optional[str] = ""
    htyk: Optional[str] = ""
    cgykValue: Optional[float] = 0.0
    htykValue: Optional[float] = 0.0
    strongLimitUpDays: Optional[int] = 0
    trendGroup: Optional[bool] = False
    trendBack: Optional[bool] = False
    trendStart: Optional[bool] = False
    trendGroup10: Optional[bool] = False
    limitupGene: Optional[bool] = False
    mainStart: Optional[bool] = False
    mainFrequent: Optional[bool] = False









