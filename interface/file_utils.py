#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
file_utils.py - 文件读取工具模块

提供 TXT/CSV 读取、目录创建功能。
"""

import os
import csv


def readTxt(filename):  # 读取TXT 返回list 忽略#号
    readReturn = []
    with open(filename, 'r', encoding='utf-8') as openfiles:
        readInfo = openfiles.readlines()
    for read_row in readInfo:  # #号行忽略
        readTemp = read_row.strip().startswith('#')
        if readTemp:
            continue
        else:
            readReturn.append(read_row.strip().strip('\n\r'))
    return readReturn


def readCsv(filename):  # 读取CSV文件返回list
    result = []
    with open(filename, mode="r") as f:
        reader = csv.reader(f)
        next(reader)
        for row in reader:
            result.append(row)
    return result


def makeDir(dirName):  # 在当前目录创建文件夹
    path = os.getcwd()  # 获取当前路径
    dir = os.listdir(path)  # 获取当前路径所有文件名
    if dirName not in dir:  # 判断本地是否已经有此文件有则不创建。
        os.mkdir(dirName)
