#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
interface 包 - 网络设备配置检查工具核心模块

显式导入各子模块的公开 API，保持向后兼容。
"""

# 设备连接
from .device_client import deviceControl, deviceControl_auto, deleteUnknownStr

# Excel 读写
from .excel_handler import excel

# 日志
from .log_config import setup_logging

# 线程池
from .thread_pool import autoThreadingPool

# 文件工具
from .file_utils import readTxt, readTxtGrouped, readCsv, makeDir

# 网络工具
from .bitFunctions import ping_check, passwdinput, revData_error

__all__ = [
    # 设备连接
    'deviceControl', 'deviceControl_auto', 'deleteUnknownStr',
    # Excel
    'excel',
    # 日志
    'setup_logging',
    # 线程池
    'autoThreadingPool',
    # 文件工具
    'readTxt', 'readTxtGrouped', 'readCsv', 'makeDir',
    # 网络工具
    'ping_check', 'passwdinput', 'revData_error',
]
