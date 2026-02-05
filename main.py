#!/usr/bin/python3
# -*- coding: utf-8 -*-
import getpass
import re
from interface import excel, logg, autoThreadingPool, init, set_value, get_value, readTxt
import platform, time
from alive_progress import alive_bar
import os


# import encodings.idna  # 解决python3.9 LookupError: unknown encoding: idna socket.gethostbyname(destination)
# pyinstaller打包后出错 python3.10已解决这个bug

def funcAction(user, passwd, fileName, logName, func, worker=30):  # 主模块
    global Rlock_local, logger, bar  # 锁，日志，进度条
    with alive_bar(title='Progress', bar='filling', spinner='waves2', unknown='wait', manual=True) as bar:  # 进度条
        init()  # 初始化全局变量
        set_value('logger', logg(logName, 'log/%s' % logName))
        set_value('bar', bar)
        file = fileName  # 读取文件名
        file_dir = 'read/%s' % file
        read = excel(file_dir)
        logger = get_value('logger')
        bar = get_value('bar')
        logger.get_log().info('当前运行环境:%s %s %s' % (platform.system(), platform.version(), platform.machine()))
        bar(0.05)
        try:
            read_info = read.excel_read()
            logger.get_log().info('读取 \'%s\' 成功,数量:%d' % (file, len(read_info)))
        except Exception as e:
            logger.get_log().error('读取 \'%s\' 失败:%s' % (file, e))
            bar(1)
            return
        bar(0.06)
        username = user
        password = passwd
        bar(0.07)
        for readCell in read_info:
            readCell.insert(0, password)
            readCell.insert(0, username)
        bar(0.1)
        logger.get_log().info('%s 载入线程...' % func.__name__)
        my_poll = autoThreadingPool(int(worker))
        result = my_poll(func, read_info)
        logger.get_log().info('线程结束,准备写入本地...')
        bar(1)
        return result


def funcAction1(data, logName, func, worker=30):  # 主模块
    global Rlock_local, logger, bar  # 锁，日志，进度条
    with alive_bar(title='Progress', bar='filling', spinner='waves2', unknown='wait', manual=True) as bar:  # 进度条
        init()  # 初始化全局变量
        set_value('logger', logg(logName, 'log/%s' % logName))
        set_value('bar', bar)
        logger = get_value('logger')
        bar = get_value('bar')
        logger.get_log().info('当前运行环境:%s %s %s' % (platform.system(), platform.version(), platform.machine()))
        bar(0.1)
        logger.get_log().info('%s 载入线程...' % func.__name__)
        my_poll = autoThreadingPool(int(worker))
        result = my_poll(func, data)
        logger.get_log().info('线程结束,准备写入本地...')
        bar(1)
        return result


def oringinDataFormat():  # 原始数据分类
    file_dir = 'read/config'
    all_items = [item for item in os.listdir(file_dir) if not item.startswith('.')]  # 去掉.开头的文件
    read_info = []  # 结果
    for item in all_items:
        name = item.replace('.txt', '').replace('.log', '')
        returnStr = returntype(name)
        returnStr.update({'name': name, 'filename': item})
        read_info.append(returnStr)
    return read_info


def returntype(name):  # 确定设备类型以及检查项
    if re.search(r'-S_(A|B|C|D)', name, flags=re.I):
        return {'type': 'Spine', 'checkOption': {'版本': 1,
                                                 '补丁': 1,
                                                 '多余文件检查': 1,
                                                 '硬件状态检查': 1,
                                                 '未关闭端口': 1,
                                                 'bgp邻居状态': 1,
                                                 'feature-software状态': 1,
                                                 '失败命令配置检查': 1,
                                                 'pki配置': 1,
                                                 '关闭FTP配置': 1,
                                                 'mlag状态': 0,
                                                 'mlag配置': 0,
                                                 '大路由配置': 1,
                                                 'NTP配置': 1,
                                                 '全局vlan配置': 0,
                                                 'mac飘移配置': 0,
                                                 'STP配置': 0,
                                                 'arp冲突配置': 0,
                                                 'telnet关闭配置': 1,
                                                 'vpn实例配置': 1,
                                                 'aaa配置': 1,
                                                 'BGP配置': 1,
                                                 'snmp配置': 1,
                                                 'LLDP配置': 1,
                                                 'ssh配置': 1,
                                                 'cmd权限配置': 1,
                                                 'user-interface配置': 1,
                                                 'hash配置': 1,
                                                 '带外接口配置': 1,
                                                 'loopback配置': 1,
                                                 'peerlink配置': 0,
                                                 'DAD配置': 0,
                                                 'monitor-link配置': 0,
                                                 }}
    elif re.search(r'-LF\d+_(A|B|C|D)', name, flags=re.I):
        return {'type': 'Leaf', 'checkOption': {'版本': 1,
                                                '补丁': 1,
                                                '多余文件检查': 1,
                                                '硬件状态检查': 1,
                                                '未关闭端口': 1,
                                                'bgp邻居状态': 1,
                                                'feature-software状态': 1,
                                                '失败命令配置检查': 1,
                                                'pki配置': 1,
                                                '关闭FTP配置': 1,
                                                'mlag状态': 1,
                                                'mlag配置': 1,
                                                '大路由配置': 1,
                                                'NTP配置': 1,
                                                '全局vlan配置': 1,
                                                'mac飘移配置': 1,
                                                'STP配置': 1,
                                                'arp冲突配置': 1,
                                                'telnet关闭配置': 1,
                                                'vpn实例配置': 1,
                                                'aaa配置': 1,
                                                'BGP配置': 1,
                                                'snmp配置': 1,
                                                'LLDP配置': 1,
                                                'ssh配置': 1,
                                                'cmd权限配置': 1,
                                                'user-interface配置': 1,
                                                'hash配置': 0,
                                                '带外接口配置': 1,
                                                'loopback配置': 0,
                                                'peerlink配置': 1,
                                                'DAD配置': 1,
                                                'monitor-link配置': 1,
                                                }}
    elif re.search(r'-SLF\d+_(A|B|C|D)', name, flags=re.I):
        return {'type': 'Slf', 'checkOption': {'版本': 1,
                                               '补丁': 1,
                                               '多余文件检查': 1,
                                               '硬件状态检查': 1,
                                               '未关闭端口': 1,
                                               'bgp邻居状态': 1,
                                               'feature-software状态': 1,
                                               '失败命令配置检查': 1,
                                               'pki配置': 1,
                                               '关闭FTP配置': 1,
                                               'mlag状态': 1,
                                               'mlag配置': 1,
                                               '大路由配置': 1,
                                               'NTP配置': 1,
                                               '全局vlan配置': 1,
                                               'mac飘移配置': 1,
                                               'STP配置': 1,
                                               'arp冲突配置': 1,
                                               'telnet关闭配置': 1,
                                               'vpn实例配置': 1,
                                               'aaa配置': 1,
                                               'BGP配置': 0,
                                               'snmp配置': 1,
                                               'LLDP配置': 1,
                                               'ssh配置': 1,
                                               'cmd权限配置': 1,
                                               'user-interface配置': 1,
                                               'hash配置': 1,
                                               '带外接口配置': 1,
                                               'loopback配置': 1,
                                               'peerlink配置': 1,
                                               'DAD配置': 1,
                                               'monitor-link配置': 1,
                                               }}
    elif re.search(r'-LA\d+_(A|B|C|D)', name, flags=re.I):
        return {'type': 'La', 'checkOption': {'版本': 1,
                                              '补丁': 1,
                                              '多余文件检查': 1,
                                              '硬件状态检查': 1,
                                              '未关闭端口': 1,
                                              'bgp邻居状态': 1,
                                              'feature-software状态': 1,
                                              '失败命令配置检查': 1,
                                              'pki配置': 1,
                                              '关闭FTP配置': 1,
                                              'mlag状态': 1,
                                              'mlag配置': 1,
                                              '大路由配置': 1,
                                              'NTP配置': 1,
                                              '全局vlan配置': 1,
                                              'mac飘移配置': 1,
                                              'STP配置': 1,
                                              'arp冲突配置': 1,
                                              'telnet关闭配置': 1,
                                              'vpn实例配置': 1,
                                              'aaa配置': 1,
                                              'BGP配置': 0,
                                              'snmp配置': 1,
                                              'LLDP配置': 1,
                                              'ssh配置': 1,
                                              'cmd权限配置': 1,
                                              'user-interface配置': 1,
                                              'hash配置': 0,
                                              '带外接口配置': 1,
                                              'loopback配置': 0,
                                              'peerlink配置': 0,
                                              'DAD配置': 0,
                                              'monitor-link配置': 1,
                                              }}
    elif re.search(r'-PL_(A|B|C|D)', name, flags=re.I):
        return {'type': 'Pl', 'checkOption': {'版本': 1,
                                              '补丁': 1,
                                              '多余文件检查': 1,
                                              '硬件状态检查': 1,
                                              '未关闭端口': 1,
                                              'bgp邻居状态': 1,
                                              'feature-software状态': 1,
                                              '失败命令配置检查': 1,
                                              'pki配置': 1,
                                              '关闭FTP配置': 1,
                                              'mlag状态': 0,
                                              'mlag配置': 0,
                                              '大路由配置': 1,
                                              'NTP配置': 1,
                                              '全局vlan配置': 0,
                                              'mac飘移配置': 0,
                                              'STP配置': 0,
                                              'arp冲突配置': 1,
                                              'telnet关闭配置': 1,
                                              'vpn实例配置': 1,
                                              'aaa配置': 1,
                                              'BGP配置': 0,
                                              'snmp配置': 1,
                                              'LLDP配置': 1,
                                              'ssh配置': 1,
                                              'cmd权限配置': 1,
                                              'user-interface配置': 1,
                                              'hash配置': 1,
                                              '带外接口配置': 1,
                                              'loopback配置': 0,
                                              'peerlink配置': 0,
                                              'DAD配置': 0,
                                              'monitor-link配置': 0,
                                              }}
    elif re.search(r'-PODLC_(A|B|C|D)', name, flags=re.I):
        return {'type': 'Podlc', 'checkOption': {'版本': 1,
                                                 '补丁': 1,
                                                 '多余文件检查': 1,
                                                 '硬件状态检查': 1,
                                                 '未关闭端口': 1,
                                                 'bgp邻居状态': 1,
                                                 'feature-software状态': 1,
                                                 '失败命令配置检查': 1,
                                                 'pki配置': 1,
                                                 '关闭FTP配置': 1,
                                                 'mlag状态': 0,
                                                 'mlag配置': 0,
                                                 '大路由配置': 1,
                                                 'NTP配置': 1,
                                                 '全局vlan配置': 0,
                                                 'mac飘移配置': 0,
                                                 'STP配置': 0,
                                                 'arp冲突配置': 0,
                                                 'telnet关闭配置': 1,
                                                 'vpn实例配置': 1,
                                                 'aaa配置': 1,
                                                 'BGP配置': 0,
                                                 'snmp配置': 1,
                                                 'LLDP配置': 1,
                                                 'ssh配置': 1,
                                                 'cmd权限配置': 1,
                                                 'user-interface配置': 1,
                                                 'hash配置': 1,
                                                 '带外接口配置': 1,
                                                 'loopback配置': 0,
                                                 'peerlink配置': 0,
                                                 'DAD配置': 0,
                                                 'monitor-link配置': 0,
                                                 }}
    elif re.search(r'-GWLC_(A|B|C|D)', name, flags=re.I):
        return {'type': 'Gwlc', 'checkOption': {'版本': 1,
                                                '补丁': 1,
                                                '多余文件检查': 1,
                                                '硬件状态检查': 1,
                                                '未关闭端口': 1,
                                                'bgp邻居状态': 1,
                                                'feature-software状态': 1,
                                                '失败命令配置检查': 1,
                                                'pki配置': 1,
                                                '关闭FTP配置': 1,
                                                'mlag状态': 0,
                                                'mlag配置': 0,
                                                '大路由配置': 1,
                                                'NTP配置': 1,
                                                '全局vlan配置': 0,
                                                'mac飘移配置': 0,
                                                'STP配置': 0,
                                                'arp冲突配置': 0,
                                                'telnet关闭配置': 1,
                                                'vpn实例配置': 1,
                                                'aaa配置': 1,
                                                'BGP配置': 0,
                                                'snmp配置': 1,
                                                'LLDP配置': 1,
                                                'ssh配置': 1,
                                                'cmd权限配置': 1,
                                                'user-interface配置': 1,
                                                'hash配置': 1,
                                                '带外接口配置': 1,
                                                'loopback配置': 0,
                                                'peerlink配置': 0,
                                                'DAD配置': 0,
                                                'monitor-link配置': 0,
                                                }}
    elif re.search(r'-AGG_(A|B|C|D)', name, flags=re.I):
        return {'type': 'Agg', 'checkOption': {'版本': 1,
                                               '补丁': 1,
                                               '多余文件检查': 1,
                                               '硬件状态检查': 1,
                                               '未关闭端口': 1,
                                               'bgp邻居状态': 1,
                                               'feature-software状态': 1,
                                               '失败命令配置检查': 1,
                                               'pki配置': 1,
                                               '关闭FTP配置': 1,
                                               'mlag状态': 0,
                                               'mlag配置': 0,
                                               '大路由配置': 1,
                                               'NTP配置': 1,
                                               '全局vlan配置': 0,
                                               'mac飘移配置': 0,
                                               'STP配置': 0,
                                               'arp冲突配置': 1,
                                               'telnet关闭配置': 1,
                                               'vpn实例配置': 1,
                                               'aaa配置': 1,
                                               'BGP配置': 0,
                                               'snmp配置': 1,
                                               'LLDP配置': 1,
                                               'ssh配置': 1,
                                               'cmd权限配置': 1,
                                               'user-interface配置': 1,
                                               'hash配置': 1,
                                               '带外接口配置': 1,
                                               'loopback配置': 0,
                                               'peerlink配置': 0,
                                               'DAD配置': 0,
                                               'monitor-link配置': 0,
                                               }}
    elif re.search(r'-NFVL\d*_(A|B|C|D)', name, flags=re.I):
        return {'type': 'Nfvl', 'checkOption': {'版本': 1,
                                                '补丁': 1,
                                                '多余文件检查': 1,
                                                '硬件状态检查': 1,
                                                '未关闭端口': 1,
                                                'bgp邻居状态': 1,
                                                'feature-software状态': 1,
                                                '失败命令配置检查': 1,
                                                'pki配置': 1,
                                                '关闭FTP配置': 1,
                                                'mlag状态': 0,
                                                'mlag配置': 0,
                                                '大路由配置': 1,
                                                'NTP配置': 1,
                                                '全局vlan配置': 1,
                                                'mac飘移配置': 1,
                                                'STP配置': 0,
                                                'arp冲突配置': 1,
                                                'telnet关闭配置': 1,
                                                'vpn实例配置': 1,
                                                'aaa配置': 1,
                                                'BGP配置': 0,
                                                'snmp配置': 1,
                                                'LLDP配置': 1,
                                                'ssh配置': 1,
                                                'cmd权限配置': 1,
                                                'user-interface配置': 1,
                                                'hash配置': 1,
                                                '带外接口配置': 1,
                                                'loopback配置': 0,
                                                'peerlink配置': 0,
                                                'DAD配置': 0,
                                                'monitor-link配置': 0,
                                                }}
    elif re.search(r'-NFVW\d*_(A|B|C|D)', name, flags=re.I):
        return {'type': 'Nfvw', 'checkOption': {'版本': 1,
                                                '补丁': 1,
                                                '多余文件检查': 1,
                                                '硬件状态检查': 1,
                                                '未关闭端口': 1,
                                                'bgp邻居状态': 1,
                                                'feature-software状态': 1,
                                                '失败命令配置检查': 1,
                                                'pki配置': 1,
                                                '关闭FTP配置': 1,
                                                'mlag状态': 0,
                                                'mlag配置': 0,
                                                '大路由配置': 1,
                                                'NTP配置': 1,
                                                '全局vlan配置': 1,
                                                'mac飘移配置': 1,
                                                'STP配置': 0,
                                                'arp冲突配置': 1,
                                                'telnet关闭配置': 1,
                                                'vpn实例配置': 1,
                                                'aaa配置': 1,
                                                'BGP配置': 0,
                                                'snmp配置': 1,
                                                'LLDP配置': 1,
                                                'ssh配置': 1,
                                                'cmd权限配置': 1,
                                                'user-interface配置': 1,
                                                'hash配置': 1,
                                                '带外接口配置': 1,
                                                'loopback配置': 0,
                                                'peerlink配置': 0,
                                                'DAD配置': 0,
                                                'monitor-link配置': 0,
                                                }}
    elif re.search(r'-WC_(A|B|C|D)', name, flags=re.I):
        return {'type': 'Wc', 'checkOption': {'版本': 1,
                                              '补丁': 1,
                                              '多余文件检查': 1,
                                              '硬件状态检查': 1,
                                              '未关闭端口': 1,
                                              'bgp邻居状态': 1,
                                              'feature-software状态': 1,
                                              '失败命令配置检查': 1,
                                              'pki配置': 1,
                                              '关闭FTP配置': 1,
                                              'mlag状态': 0,
                                              'mlag配置': 0,
                                              '大路由配置': 1,
                                              'NTP配置': 1,
                                              '全局vlan配置': 0,
                                              'mac飘移配置': 0,
                                              'STP配置': 0,
                                              'arp冲突配置': 1,
                                              'telnet关闭配置': 1,
                                              'vpn实例配置': 1,
                                              'aaa配置': 1,
                                              'BGP配置': 0,
                                              'snmp配置': 1,
                                              'LLDP配置': 1,
                                              'ssh配置': 1,
                                              'cmd权限配置': 1,
                                              'user-interface配置': 1,
                                              'hash配置': 1,
                                              '带外接口配置': 1,
                                              'loopback配置': 0,
                                              'peerlink配置': 0,
                                              'DAD配置': 0,
                                              'monitor-link配置': 0,
                                              }}
    elif re.search(r'-FW\d*_(A|B|C|D)', name, flags=re.I):
        return {'type': 'Fw', 'checkOption': {'版本': 1,
                                              '补丁': 1,
                                              '多余文件检查': 1,
                                              '硬件状态检查': 1,
                                              '未关闭端口': 1,
                                              'bgp邻居状态': 0,
                                              'feature-software状态': 0,
                                              '失败命令配置检查': 1,
                                              'pki配置': 1,
                                              '关闭FTP配置': 1,
                                              'mlag状态': 0,
                                              'mlag配置': 0,
                                              '大路由配置': 0,
                                              'NTP配置': 1,
                                              '全局vlan配置': 0,
                                              'mac飘移配置': 1,
                                              'STP配置': 0,
                                              'arp冲突配置': 0,
                                              'telnet关闭配置': 1,
                                              'vpn实例配置': 1,
                                              'aaa配置': 1,
                                              'BGP配置': 0,
                                              'snmp配置': 1,
                                              'LLDP配置': 1,
                                              'ssh配置': 1,
                                              'cmd权限配置': 1,
                                              'user-interface配置': 1,
                                              'hash配置': 0,
                                              '带外接口配置': 1,
                                              'loopback配置': 0,
                                              'peerlink配置': 0,
                                              'DAD配置': 0,
                                              'monitor-link配置': 0,
                                              }}
    elif re.search(r'-SS_(A|B|C|D)', name, flags=re.I):
        return {'type': 'S0', 'checkOption': {'版本': 1,
                                              '补丁': 1,
                                              '多余文件检查': 1,
                                              '硬件状态检查': 1,
                                              '未关闭端口': 1,
                                              'bgp邻居状态': 1,
                                              'feature-software状态': 1,
                                              '失败命令配置检查': 1,
                                              'pki配置': 1,
                                              '关闭FTP配置': 1,
                                              'mlag状态': 0,
                                              'mlag配置': 0,
                                              '大路由配置': 1,
                                              'NTP配置': 1,
                                              '全局vlan配置': 0,
                                              'mac飘移配置': 0,
                                              'STP配置': 0,
                                              'arp冲突配置': 0,
                                              'telnet关闭配置': 1,
                                              'vpn实例配置': 1,
                                              'aaa配置': 1,
                                              'BGP配置': 0,
                                              'snmp配置': 1,
                                              'LLDP配置': 1,
                                              'ssh配置': 1,
                                              'cmd权限配置': 1,
                                              'user-interface配置': 1,
                                              'hash配置': 0,
                                              '带外接口配置': 1,
                                              'loopback配置': 1,
                                              'peerlink配置': 0,
                                              'DAD配置': 0,
                                              'monitor-link配置': 0,
                                              }}
    else:
        return {'type': 'Other', 'checkOption': {'版本': 1,
                                                 '补丁': 1,
                                                 '多余文件检查': 1,
                                                 '硬件状态检查': 1,
                                                 '未关闭端口': 1,
                                                 'bgp邻居状态': 1,
                                                 'feature-software状态': 1,
                                                 '失败命令配置检查': 1,
                                                 'pki配置': 1,
                                                 '关闭FTP配置': 1,
                                                 'mlag状态': 1,
                                                 'mlag配置': 1,
                                                 '大路由配置': 1,
                                                 'NTP配置': 1,
                                                 '全局vlan配置': 1,
                                                 'mac飘移配置': 1,
                                                 'STP配置': 1,
                                                 'arp冲突配置': 1,
                                                 'telnet关闭配置': 1,
                                                 'vpn实例配置': 1,
                                                 'aaa配置': 1,
                                                 'BGP配置': 1,
                                                 'snmp配置': 1,
                                                 'LLDP配置': 1,
                                                 'ssh配置': 1,
                                                 'cmd权限配置': 1,
                                                 'user-interface配置': 1,
                                                 'hash配置': 1,
                                                 '带外接口配置': 1,
                                                 'loopback配置': 1,
                                                 'peerlink配置': 1,
                                                 'DAD配置': 1,
                                                 'monitor-link配置': 1,
                                                 }}


def writeToExcel(filename, title, data):  # 写入数据到excel
    filename_local = 'data/%s' % filename
    title_local = title
    data_local = data
    write_info = excel(filename_local)
    try:
        write_info.excel_write(title_local, data_local)
        basename = write_info.save_file()
        logger.get_log().info('文件 %s 写入完成,保存至data目录下' % basename)
    except Exception as e:
        logger.get_log().error('文件写入失败,%s' % e)


def writeToTXT(data):  # 写入数据到TXT
    data_local = data
    timeNow = time.strftime('%Y%m%d%H%M%S', time.localtime(time.time()))
    try:
        for data_unit in data_local:
            with open('data/%s_%s_%s.log' % (data_unit[0], data_unit[1], timeNow), 'w') as f:
                f.write(data_unit[2])
    except Exception as e:
        logger.get_log().error('文件写入失败,%s %s' % (e, Exception))
        return
    logger.get_log().info('文件写入完成,保存至data目录下')


def platform_select():  # 判断当前运行环境
    username = ''
    password = ''
    worker = os.cpu_count()
    platformStr = platform.system()
    if 'Windows' in platformStr:
        from interface import passwdinput
        username = input('用户:')
        password = passwdinput('密码:')
    elif 'Linux' in platformStr:
        import sys
        username, password = sys.argv[1], sys.argv[2]
    elif 'Darwin' in platformStr:
        username = input('用户:')
        password = getpass.getpass('password:')
    else:
        print(platformStr, platform.version(), platform.machine())
        print('当前运行环境不支持')
    return username, password, worker


def start_action():  # windows功能入口
    print('release:v1.9.3')
    print(
        '程序功能如下：\n'
        '1.登陆配置检查（根据keyWords.txt里的关键字）\n'
        '2.采集配置文件检查\n'
        '3.下发配置\n')
    while True:
        if 'Linux' in platform.system():
            import sys
            functionSelect = sys.argv[3]
        else:
            functionSelect = input('请选择执行的功能(输入数字):')
        if functionSelect == '1':
            fileName = 'devices_ip.xlsx'
            title = ['IP', 'Description', 'PingStatus(ms)', 'accessMode']  # 保存的sheet标题
            readInfo = readTxt('read/keyWords.txt')  # 读取匹配关键字用作title
            for i in readInfo:  # 更新title
                if i.split(',')[1] not in title:
                    title.append(i.split(',')[1])
            savename = 'checkConfig'
            print('1).确认IP等信息已填入read\devices_ip.xlsx\n'
                  '2).确认检查关键字已填入read\keyWords.txt\n'
                  '3).输入账户,密码')
            from checkConfig import deviceCheck
            username, password, worker = platform_select()
            data = funcAction(username, password, fileName, savename, deviceCheck, worker)
            writeToExcel(savename, title, data)
            break
        if functionSelect == '2':  # 配置比对
            title = ['IP',
                     '设备类型',
                     '版本',
                     '补丁',
                     '多余文件检查',
                     '硬件状态检查',
                     '未关闭端口',
                     'bgp邻居状态',
                     'feature-software状态',
                     '失败命令配置检查',
                     'pki配置',
                     '关闭FTP配置',
                     'mlag状态',
                     'mlag配置',
                     '大路由配置',
                     'NTP配置',
                     '全局vlan配置',
                     'mac飘移配置',
                     'STP配置',
                     'arp冲突配置',
                     'telnet关闭配置',
                     'vpn实例配置',
                     'aaa配置',
                     'BGP配置',
                     'snmp配置',
                     'LLDP配置',
                     'ssh配置',
                     'cmd权限配置',
                     'user-interface配置',
                     'hash配置',
                     '带外接口配置',
                     'loopback配置',
                     'peerlink配置',
                     'DAD配置',
                     'monitor-link配置']  # 保存的sheet标题
            savename = 'compareResult'
            from cfgCheck import deviceCheck
            data = funcAction1(oringinDataFormat(), savename, deviceCheck, 10)
            writeToExcel(savename, title, data)
            break
        if functionSelect == '3':
            fileName = 'devices_ip.xlsx'
            title = ['IP', 'Description', 'PingStatus(ms)', 'accessMode', 'result']  # 保存的sheet标题
            savename = 'sendCmd'
            print('1).确认IP等信息已填入read\devices_ip.xlsx\n'
                  '3).输入账户,密码')
            from sendCmd import deviceSend
            username, password, worker = platform_select()
            data = funcAction(username, password, fileName, savename, deviceSend, worker)
            writeToExcel(savename, title, data)
            break
        else:
            print('输入错误请重新输入')


if __name__ == '__main__':
    start_action()
    # oringinDataFormat()
# 打包命令pyinstaller -F -i images\favicon.ico .\main.py -n win_x64_main  --collect-all grapheme --clean
