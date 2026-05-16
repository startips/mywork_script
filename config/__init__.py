#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
config 包：集中管理配置检查项定义和设备类型配置表
将 returntype() 中 14 份重复的 33 项 dict 合并为数据驱动结构
"""
from .check_items import CHECK_ITEM_NAMES, DEVICE_TYPE_CONFIGS, DEVICE_TYPE_PATTERNS, _make_check_option

__all__ = ['CHECK_ITEM_NAMES', 'DEVICE_TYPE_CONFIGS', 'DEVICE_TYPE_PATTERNS', '_make_check_option']
