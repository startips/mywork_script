#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import os
import sys
import re
from interface import readTxtGrouped, revData_error

logger = logging.getLogger(__name__)

# 基础路径（兼容 PyInstaller 打包）
if getattr(sys, 'frozen', False):
    _base_dir = os.path.dirname(sys.executable)
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))


def infoDeal(config_text):
    """处理离线配置数据，按分组匹配并返回检查结果列表"""
    logger.info('开始处理离线配置数据...')
    result = []
    groups = readTxtGrouped(os.path.join(_base_dir, 'read', 'keyWords.txt'))
    logger.info(f'成功加载 {len(groups)} 个检查分组')

    revInfo = revData_error(config_text)
    if revInfo == 'NULL':
        for group in groups:
            issues = []
            for kw in group['keywords']:
                configStr = re.search(r'%s' % kw['pattern'], config_text, re.IGNORECASE)
                if configStr:
                    if kw['flag'] == '0':
                        issues.append(f"多余'{kw['category']}':{kw['pattern']}")
                        logger.warning(f'发现多余配置: 分组={group["name"]}, 关键字={kw["pattern"]}')
                else:
                    if kw['flag'] == '1':
                        issues.append(f"缺少'{kw['category']}':{kw['pattern']}")
                        logger.warning(f'发现缺少配置: 分组={group["name"]}, 关键字={kw["pattern"]}')
            if issues:
                result.append('\n'.join(issues))
            else:
                result.append('无不合规项')
    else:
        logger.error(f'配置文件报错: {revInfo}')
        result.append(revInfo)

    logger.info(f'配置数据处理完成，返回 {len(result)} 项结果')
    return result


def deviceCheck(arg=None):
    """离线设备配置检查入口"""
    if arg is None:
        arg = {}
    device_name = arg.get('name', 'Unknown')
    filename = arg.get('filename', '')
    logger.info(f'开始检查离线配置文件: {filename} (设备名: {device_name})')
    result = [device_name]
    file_path = os.path.join(_base_dir, 'read', 'config', filename)
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            fileTxt = f.read()
        try:
            result.extend(infoDeal(fileTxt))
            logger.info(f'{device_name} 数据处理成功')
        except Exception as e:
            result.append(f'数据处理失败 {e}')
            logger.error(f'{device_name} 数据处理失败: {e}', exc_info=True)
    except Exception as e:
        logger.error(f'{device_name} 读取文件失败: {e}', exc_info=True)
        result.append(f'读取文件失败 {e}')
    logger.info(f'离线设备 {device_name} 检查完成')
    return result


if __name__ == '__main__':
    infoDeal('test content')
