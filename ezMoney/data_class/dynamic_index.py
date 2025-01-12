
from typing import List
from attr import dataclass
from date_utils.date import *
from http_request import build_http_request
import logging

logger = logging.getLogger("my_logger")

@dataclass
class BlockDynamicIndex:
    blockCode: str
    score: float
    scoreChangePre: float
    scoreChange: float
    dataType: int
    industryType: int
    score: float
    isTrack: bool
    isPpp: bool

@dataclass
class BlockEnvironmentIndex:
    categoryCode: str
    score: float
    scoreChangePre: float
    scoreChange: float
    dataType: int
    isTrack: bool
    isPpp: bool
    blockDynamicIndexList: List[BlockDynamicIndex]



def build_block_environment_index_dict(date = get_current_date(), indexType = 0):
    rslt = build_http_request.dynamic_index(date = date, indexType = indexType)
    if rslt == None:
        return {}
    if 'errcode' in rslt and rslt['errcode']!= None:
        logger.error("block_environment_index error! errcode: " + rslt['errcode'])

    if'result' not in rslt:
        logger.error("block_environment_index no result.")
        return {}
    block_list = rslt['result']
    block_dict = {}
    for item in block_list:
        if 'categoryCode' not in item:
            logger.error("block_environment_index no categoryCode.")
            continue
        block_dict[item['categoryCode']] = BlockEnvironmentIndex(**item)
    return block_dict


def build_block_environment_index_list(date = get_current_date(), indexType = 0):
    rslt = build_http_request.dynamic_index(date = date, indexType = indexType)
    if rslt == None:
        return []
    if 'errcode' in rslt and rslt['errcode']!= None:
        logger.error("block_environment_index error! errcode: " + rslt['errcode'])

    if'result' not in rslt:
        logger.error("block_environment_index no result.")
        return []
    block_list = rslt['result']
    block_dict = []
    for item in block_list:
        if 'categoryCode' not in item:
            logger.error("block_environment_index no categoryCode.")
            continue
        block_dict.append(BlockEnvironmentIndex(**item))
    return block_dict



