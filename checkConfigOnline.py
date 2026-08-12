#!/usr/bin/python3
# -*- coding: utf-8 -*-
import logging
import os
import sys
from interface import deviceControl_auto, ping_check, revData_error, readTxtGrouped
import re

logger = logging.getLogger(__name__)

# 基础路径（兼容 PyInstaller 打包）
if getattr(sys, 'frozen', False):
    _base_dir = os.path.dirname(sys.executable)
else:
    _base_dir = os.path.dirname(os.path.abspath(__file__))


def infoDeal(data):  # 数据处理 返回list
    logger.info('开始处理配置数据...')
    result = []
    groups = readTxtGrouped(os.path.join(_base_dir, 'read', 'keyWords.txt'))
    logger.info(f'成功加载 {len(groups)} 个检查分组')
    revInfo = revData_error(data['dis current-configuration'])  # 判断是否有命令执行错误
    if revInfo == 'NULL':
        for group in groups:
            issues = []
            for kw in group['keywords']:
                configStr = re.search(r'%s' % kw['pattern'], data['dis current-configuration'], re.IGNORECASE)
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
        logger.error(f'命令执行报错: {revInfo}')
        result.append(revInfo)
    logger.info(f'配置数据处理完成，返回 {len(result)} 项结果')
    return result


def deviceCheck(arg=None):  # 配置检查
    if arg is None:
        arg = []
    device_ip = arg[2]
    device_user = arg[0]
    device_pass = arg[1]
    des_local = arg[3]
    logger.info(f'开始检查设备: {device_ip} ({des_local})')
    conn = deviceControl_auto(device_ip, device_user, device_pass)  # 登陆
    cmd = ['dis current-configuration']  # 命令
    result = [device_ip, des_local]
    pingDelay = ping_check(device_ip)[0]  # ping检测
    result.append(pingDelay)
    try:  # 登录检查
        resData = conn.sendCmd_auto(cmd)
        logger.info(f'{device_ip} 登陆成功, 登录方式: {resData["loginWay"]}')
        result.append(resData['loginWay'])  # 登录方式
        try:  # 处理数据检查
            result.extend(infoDeal(resData))
            logger.info(f'{device_ip} 数据处理成功')
        except Exception as e:
            result.append(f'数据处理失败 {e}')
            logger.error(f'{device_ip} 数据处理失败: {e}', exc_info=True)
    except Exception as e:
        logger.error(f'{device_ip} 登陆失败: {e}', exc_info=True)
        result.append('login fail')
    logger.info(f'设备 {device_ip} 检查完成')
    return result


if __name__ == '__main__':
    infoDeal({'dis current-configuration': '123'})
    # c = {}
    # print(type(c.get('i')))
