from dataclasses import dataclass
from functools import lru_cache
import logging
from typing import List
import json

from date_utils.date import *
from matplotlib import category
from http_request import build_http_request
from logger import logger
import dataclasses

@dataclass
class BlockRank:
    tradeDate: str
    blockCode: str
    dataType: int
    industryType: int
    num: float
    directionNum: float
    numChange: float
    prePctChangeRate: float
    isTrack: bool
    isPpp: bool

@dataclass
class CategoryRank:
    tradeDate: str
    categoryCode: str
    categoryType: int
    num: float
    directionNum: float
    numChange: float
    prePctChangeRate: float
    isTrack: bool
    isPpp: bool
    name: str
    stockType: str
    industryType: str
    blockRankList: List[BlockRank]

def object_hook(d):
    if 'blockRankList' not in d:
        d['blockRankList'] = []
    return CategoryRank(**d)



def build_category_rank_dict(date = get_current_date()):
    rslt = build_http_request.block_category_rank(date = date)
    categoryDict = {}
    if rslt == None:
        return categoryDict
    if 'result' not in rslt:
        logger.error("block_category_rank no result.")
        return categoryDict
    if 'localCategoryRankList' in rslt['result']:
        localCategoryRankList = rslt['result']['localCategoryRankList']

    for item in localCategoryRankList:
        curItem = CategoryRank(**item)
        categoryDict[curItem.categoryCode] = curItem
    return categoryDict


def build_category_rank_list(date = get_current_date()):
    rslt = build_http_request.block_category_rank(date = date)
    categoryRankList = []
    if rslt == None:
        return categoryRankList
    if 'localCategoryRankList' in rslt['result']:
        localCategoryRankList = rslt['result']['localCategoryRankList']

    for item in localCategoryRankList:
        curItem = CategoryRank(**item)
        categoryRankList.append(curItem)
    return categoryRankList


# @lru_cache(maxsize=10000)
# def build_category_rank_sort_list(date = get_current_date()):
#     rslt = build_http_request.block_category_rank(date = date)
#     categoryRankList = []
#     if rslt == None:
#         return categoryRankList
#     if 'localCategoryRankList' in rslt['result']:
#         localCategoryRankList = rslt['result']['localCategoryRankList']
#     if localCategoryRankList == None:
#         return categoryRankList
#     # for item in localCategoryRankList:
#     #     curItem = CategoryRank(**item)
#     #     categoryRankList.append(curItem)
#     for item in localCategoryRankList:
#         # 过滤掉不在 CategoryRank 类属性中的字段
#         filtered_item = {k: v for k, v in item.items() if k in CategoryRank.__dataclass_fields__}
#         curItem = CategoryRank(**filtered_item)
#         categoryRankList.append(curItem)

#     categoryRankList.sort(key=lambda x: x.num, reverse=True)
#     return categoryRankList

@lru_cache(maxsize=10000)
def build_category_rank_sort_list(date = get_current_date()):
    rslt = build_http_request.block_category_rank(date = date)
    categoryRankList = []
    if rslt == None:
        return categoryRankList
    if 'localCategoryRankList' in rslt['result']:
        localCategoryRankList = rslt['result']['localCategoryRankList']
    if localCategoryRankList == None:
        return categoryRankList
    
    # 获取所有必需字段（没有默认值的字段）
    required_fields = [field.name for field in dataclasses.fields(CategoryRank) 
                      if field.default == dataclasses.MISSING and field.default_factory == dataclasses.MISSING]
    
    # 定义默认值映射
    type_defaults = {
        int: 0,
        str: '',
        float: 0.0,
        bool: False
    }
    
    for item in localCategoryRankList:
        # 过滤掉不在 CategoryRank 类属性中的字段
        filtered_item = {k: v for k, v in item.items() if k in CategoryRank.__dataclass_fields__}
        
        # 为缺失的必需字段提供默认值
        for field_name in required_fields:
            if field_name not in filtered_item:
                # 获取字段类型并设置相应的默认值
                field_type = CategoryRank.__dataclass_fields__[field_name].type
                filtered_item[field_name] = type_defaults.get(field_type, None)
        
        # 确保一定能创建对象
        curItem = CategoryRank(**filtered_item)
        categoryRankList.append(curItem)
    
    categoryRankList.sort(key=lambda x: x.num, reverse=True)
    return categoryRankList


def build_block_rank_list(date = get_current_date()):
    category_rank_list =  build_category_rank_list(date)
    block_rank_list = []
    rslt = []
    for item in category_rank_list:
        if item == None:
            continue
        if item.blockRankList == None:
            continue
        block_rank_list.extend(item.blockRankList)
    for item in block_rank_list:
        if item == None:
            continue
        filtered_item = {k: v for k, v in item.items() if k in BlockRank.__dataclass_fields__}
        block = BlockRank(**filtered_item)
        rslt.append(block)
    return rslt


def build_block_rank_dict(date = get_current_date()):
    block_rank_list =  build_block_rank_list(date)
    block_rank_dict = {}
    for item in block_rank_list:
        block_rank_dict[item.blockCode] = item
    return block_rank_dict


def build_block_rank_sort_list(date = get_current_date()):
    block_rank_list =  build_block_rank_list(date)
    block_rank_list.sort(key=lambda x: x.num, reverse=True)
    return block_rank_list


def build_block_rank_to_category_rank_dict(date = get_current_date()):
    category_rank_list = build_category_rank_sort_list(date)
    rslt = {}
    for item in category_rank_list:
        if item.blockRankList != None:
            for block in item.blockRankList:
                if 'blockCode' in block:
                    if block['blockCode'] in rslt:
                        logger.error("blockCode already exists. blockCode: " + block['blockCode'] + " categoryCode: " + item.categoryCode + " categoryName: " + item.name)
                    rslt[block['blockCode']] = item.categoryCode
    return rslt
    