#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
logger.py - 日志模块

提供文件日志 + 控制台日志功能。
"""

import time
import logging


class logg:  # 日志模块
    def __init__(self, loggername, filename):
        # 创建一个logger
        self.logger = logging.getLogger(loggername)
        self.logger.setLevel(logging.DEBUG)

        # 创建一个handler，用于写入日志文件
        timeNow = time.strftime('%Y-%m-%d_%H%M%S', time.localtime(time.time()))
        filename_local = filename
        logname = '%s_%s.log' % (filename_local, timeNow)  # 日志名+日期= 存盘的文件名
        fh = logging.FileHandler(logname, encoding='utf-8')  # 指定utf-8格式编码，避免输出的日志文本乱码
        fh.setLevel(logging.DEBUG)

        # 创建一个handler，用于将日志输出到控制台
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)

        # 定义handler的输出格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s:%(message)s',
                                      datefmt='%Y-%m-%d %H:%M:%S')
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        # 给logger添加handler
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)

    def get_log(self):
        # 回调logger实例
        return self.logger
