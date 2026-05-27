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
    """
    根据设备名称匹配设备类型，返回对应的检查项配置。

    从 config.check_items 模块读取设备类型匹配规则和配置表，

    参数：
        name: 设备文件名（不含后缀），如 'SZPX06R1H01U19-DCN-DC1_FB22-S_A'

    返回：
        dict，格式为 {'type': 'Spine', 'checkOption': {33个检查项的0/1字典}}
    """
    from interface import DEVICE_TYPE_CONFIGS, DEVICE_TYPE_PATTERNS
    for pattern, type_name in DEVICE_TYPE_PATTERNS:
        if re.search(pattern, name, flags=re.I):
            return {'type': type_name, 'checkOption': DEVICE_TYPE_CONFIGS[type_name].copy()}
    # 未匹配时兜底返回 Other 类型
    return {'type': 'Other', 'checkOption': DEVICE_TYPE_CONFIGS['Other'].copy()}


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
    print('release:v1.10.2')
    print(
        '程序功能如下：\n'
        '1.在线配置检查（根据keyWords.txt里的关键字）\n'
        '2.采集配置文件状态检查\n'
        '3.下发配置\n'
        '4.配置下发验证比对（预期 vs 采集）')
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
        if functionSelect == '2':  # 配置检查+状态采集
            from interface import CHECK_ITEM_NAMES
            title = (['设备名', '设备类型', 'sysname', '管理IP', '型号']
                     + list(CHECK_ITEM_NAMES))  # 从配置表动态生成列头
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
        if functionSelect == '4':
            print('启动配置下发验证比对...\n'
                  '  预期配置: read/config_intended/*.cfg\n'
                  '  采集配置: read/config/*.log\n'
                  '  规则文件: read/compare_rules_v2.yaml\n'
                  '  报告输出: data/compareResult_<时间戳>.md')
            from compare_configs import main as compare_main
            compare_main()
            break
        else:
            print('输入错误请重新输入')


if __name__ == '__main__':
    start_action()
    # oringinDataFormat()
# 打包命令pyinstaller -F -i images\favicon.ico .\main.py -n win_x64_main --collect-all grapheme --add-data "read\check_items.yaml;read" --add-data "read\compare_rules_v2.yaml;read" --clean
