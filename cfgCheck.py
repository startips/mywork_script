#!/usr/bin/python3
# -*- coding: utf-8 -*-
from unicodedata import name

from interface import get_value, readTxt
import re


def deviceCheck(arg):  # 检查
    logger = get_value('logger')
    data_local = arg
    result = [data_local['name'], data_local['type']]
    try:  # 读取文件内容
        with open('read/config/%s' % data_local['filename'], 'r', encoding='utf-8') as f:
            fileTxt = f.read()
    except Exception as e:
        logger.get_log().error('%s 读取文件失败 %s' % (data_local['name'], e))
        result.append('read file fail')
        return result
    result.extend(checkOptions(fileTxt, data_local))  # 检查内容，检查项
    logger.get_log().info('%s 所有项检查完成' % data_local['name'])
    return result


def checkOptions(fileTxt, checkItems):  # 具体检查项
    logger = get_value('logger')
    checkResult = []  # 检查结果
    for checkItem, value in checkItems['checkOption'].items():  # 遍历检查项
        logger.get_log().info(f'{checkItems["name"]}的检查项\"{checkItem}\"设置为\"{value}\",开始检查')
        match checkItem:
            case '版本':
                if value == 1:
                    # 执行版本检查逻辑
                    matchVerinfo = re.findall(r'Version \S+ \(\S+ (\S+)\)', fileTxt)
                    if matchVerinfo:
                        verinfo = matchVerinfo[0]
                    else:
                        verinfo = '未匹配到'
                    checkResult.append(verinfo)
                else:
                    logger.get_log().info('%s 开始检查' % checkItems['name'])
                    checkResult.append('不涉及')

            case '补丁':
                if value == 1:
                    # 执行补丁检查逻辑
                    matchPatInfo = re.findall(r'Patch Package Version \:(\S+)', fileTxt)
                    if matchPatInfo:
                        patInfo = matchPatInfo[0]
                    else:
                        patInfo = '未匹配到'
                    checkResult.append(patInfo)
                else:
                    checkResult.append('不涉及')

            case '多余文件检查':
                if value == 1:
                    # 多余文件检查逻辑
                    verCount = len(re.findall(r'\d+\s+\S+\s+\S+\s+\S+\s\d+\s\d+\s\d+\:\d+\:\d+\s+\S+\.cc', fileTxt,
                                              re.IGNORECASE))  # 统计文件数量
                    patCount = len(re.findall(r'\d+\s+\S+\s+\S+\s+\S+\s\d+\s\d+\s\d+\:\d+\:\d+\s+\S+\.pat', fileTxt,
                                              re.IGNORECASE))
                    cfgCount = len(re.findall(r'\d+\s+\S+\s+\S+\s+\S+\s\d+\s\d+\s\d+\:\d+\:\d+\s+\S+\.cfg', fileTxt,
                                              re.IGNORECASE))
                    if verCount == 1 and patCount == 1 and cfgCount <= 1:
                        allCount = '通过'
                    elif verCount == 0 and patCount == 0 and cfgCount == 0:
                        allCount = '未匹配到'
                    else:
                        allCount = 'cc:%d,pat:%d,cfg:%d' % (verCount, patCount, cfgCount)
                    checkResult.append(allCount)
                else:
                    checkResult.append('不涉及')

            case '硬件状态检查':
                if value == 1:
                    # 执行硬件状态检查逻辑
                    deviceInfo = re.search(r'Device status:[\s\S]*?<', fileTxt, re.IGNORECASE)  # 硬件状态信息
                    if deviceInfo:
                        statusStr = ['Offline', 'Unregistered', 'Abnormal']
                        checkDeviceRes = '通过'
                        for str in statusStr:
                            if str in deviceInfo.group():
                                checkDeviceRes = '未通过'
                    else:
                        checkDeviceRes = '未匹配到'
                    checkResult.append(checkDeviceRes)
                else:
                    checkResult.append('不涉及')

            case '未关闭端口':
                if value == 1:
                    # 执行未关闭端口检查逻辑
                    matchDownPortInfo = re.findall(
                        r'(?:100|25)GE\d+\/\d+\/\d+\s+(down|down\(ed\)|down\(b\))(?:\s+\S+){5}', fileTxt,
                        re.IGNORECASE)  # 匹配未关闭端口
                    if matchDownPortInfo:
                        checkResult.append(len(matchDownPortInfo))
                    else:
                        checkResult.append('通过')
                else:
                    checkResult.append('不涉及')

            case 'bgp邻居状态':
                if value == 1:
                    # 执行bgp邻居状态检查逻辑
                    bgpInfo = re.search(r'BGP local router ID[\s\S]*?<', fileTxt, re.IGNORECASE)  # bgp状态信息
                    if bgpInfo:
                        bgpNum = re.findall(r'Total number of peers\s+\:\s+(\d+)', bgpInfo.group(), re.IGNORECASE)[0]
                        normalBgpNum = len(
                            re.findall(r'\d+\.\d+\.\d+\.\d+(:?\s+\d+){5}\s\d{2}\:\d{2}\:\d{2}\s+Established',
                                       bgpInfo.group(),
                                       re.IGNORECASE))
                        checkResult.append('邻居数量:%s,正常邻居数量:%d' % (bgpNum, normalBgpNum))
                    else:
                        checkResult.append('未匹配到')
                else:
                    checkResult.append('不涉及')

            case 'feature-software状态':
                if value == 1:
                    # 执行feature-software状态检查逻辑
                    matchVerinfo = re.findall(r'Version \S+ \(\S+ (\S+)\)', fileTxt)
                    if matchVerinfo:
                        if 'V300' in matchVerinfo[0]:  # 判断V300版本
                            matchFertureInfo = re.findall(
                                '(:?PKG_PNF|AIFABRIC|TELEMETRY|WEAKEA)\s+\S+\.cc\s+active\s+\S+\s+\d{4}-\d{2}-\d{2}\s+\d{2}\:\d{2}\:\d{2}',
                                fileTxt, re.IGNORECASE)
                            if len(matchFertureInfo) >= 4:
                                checkResult.append('通过')
                            else:
                                checkResult.append('未通过')
                        else:
                            checkResult.append('不涉及')
                    else:
                        checkResult.append('未匹配到')
                else:
                    checkResult.append('不涉及')

            case '失败命令配置检查':
                if value == 1:
                    # 执行失败命令配置检查逻辑
                    matchRecover = re.findall('The number of failed commands is (\d+)', fileTxt, re.IGNORECASE)
                    if matchRecover:
                        if matchRecover[0] == '0':
                            checkResult.append('通过')
                        else:
                            checkResult.append(matchRecover[0])
                    else:
                        checkResult.append('未匹配到')
                else:
                    checkResult.append('不涉及')

            case 'pki配置':
                if value == 1:
                    # pki配置检查逻辑
                    if genCheckOtion('pki realm default', fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case '关闭FTP配置':
                if value == 1:
                    # 关闭FTP配置检查逻辑
                    if genCheckOtion(
                            'undo ftp server source all-interface\s*\n\s*undo ftp ipv6 server source all-interface',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'mlag状态':
                if value == 1:
                    # 执行mlag状态检查逻辑
                    if genCheckOtion(
                            'Heart beat state\s+\:\s+OK\s*\n\s*Node [12][\s\S]*?State\s+\:\s+(:?Backup|Master)[\s\S]*?Node [12][\s\S]*?State\s+\:\s+(:?Backup|Master)',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'mlag配置':
                if value == 1:
                    # 执行mlag配置检查逻辑
                    if genCheckOtion(
                            'dfs-group 1\n\s+authentication-mode hmac-sha256 password \S+\n\s+dual-active detection source ip \S+ vpn-instance DAD peer \S+\s*\n\s+m-lag up-delay 90\s*\n\s+priority 1[25]0',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case '大路由配置':
                if value == 1:
                    if genCheckOtion(
                            'system resource large-route',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'NTP配置':
                if value == 1:
                    # 执行NTP配置检查逻辑
                    if genCheckOtion(
                            'ntp server source-interface all disable\s*\n\s*ntp ipv6 server source-interface all disable',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case '全局vlan配置':
                if value == 1:
                    # 执行全局vlan配置检查逻辑
                    if genCheckOtion(
                            'vlan batch',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'mac飘移配置':
                if value == 1:
                    # 执行mac飘移配置检查逻辑
                    if genCheckOtion(
                            'mac-address flapping detection security-level low\s*\n\s*mac-address flapping periodical trap enable',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'STP配置':
                if value == 1:
                    # 执行STP配置检查逻辑
                    if genCheckOtion(
                            'stp bridge-address \d{4}-\d{4}-\d{4}\s*\n\s*stp mode rstp\s*\n\s*stp v-stp enable\s*\n\s*stp instance 0 root primary\s*\n\s*stp bpdu-protection\s*\n\s*stp tc-protection',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'arp冲突配置':
                if value == 1:
                    # 执行arp冲突配置检查逻辑
                    if genCheckOtion(
                            'arp ip-conflict-detect enable',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'telnet关闭配置':
                if value == 1:
                    # 执行telnet关闭配置检查逻辑
                    if genCheckOtion(
                            'telnet server disable\s*\n\s*telnet ipv6 server disable\s*\n\s*undo telnet server-source all-interface\s*\n\s*undo telnet ipv6 server-source all-interface',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'vpn实例配置':
                if value == 1:
                    # 执行vpn实例配置检查逻辑
                    matchOob = re.search(r'ip vpn-instance OOB\s*\n\s*ipv4-family\s*\n\s*route-distinguisher 200:1',
                                         fileTxt,
                                         re.IGNORECASE)
                    matchDad = re.search(r'ip vpn-instance DAD\s*\n\s*ipv4-family', fileTxt, re.IGNORECASE)
                    if checkItems['type'] in ['Leaf']:  # leaf必须包含2个实例
                        if matchOob and matchDad:
                            checkResult.append('通过')
                        else:
                            checkResult.append('未通过')
                    else:  # 其他只需要oob实例
                        if matchOob:
                            checkResult.append('通过')
                        else:
                            checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'aaa配置':
                if value == 1:
                    # 执行aaa配置检查逻辑
                    if genCheckOtion(
                            'aaa\s*\n\s*authentication-scheme default\s*\n\s*authentication-mode local\s*\n\s*authorization-scheme default\s*\n\s*authorization-mode local\s*\n\s*accounting-scheme default\s*\n\s*accounting-mode none\s*\n\s*local-aaa-user password policy administrator\s*\n\s*password history record number 0\s*\n\s*password alert before-expire 0\s*\n\s*undo password alert original\s*\n\s*password expire 0\s*\n\s*domain default\s*\n\s*authentication-scheme default\s*\n\s*accounting-scheme default\s*\n\s*domain default_admin\s*\n\s*authentication-scheme default\s*\n\s*accounting-scheme default\s*\n\s*local-aaa-user user-name complexity-check disable\s*\n\s*(?:local-user (?:admin|nmsuser) password irreversible-cipher \S+\s*\n\s*local-user (?:admin|nmsuser) password-force-change disable\s*\n\s*local-user (?:admin|nmsuser) privilege level [13]\s*\n\s*local-user (?:admin|nmsuser) service-type terminal ssh\s*\n\s*){2}',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'BGP配置':
                if value == 1:
                    # 执行BGP配置检查逻辑
                    matchSpineBgp = re.search(
                        r'bgp\s+\d+\n\s+router-id\s+\S+\n timer keepalive 30 hold 90\n advertise lowest-priority all-address-family peer-up delay 120\n private-4-byte-as disable\n group \S+ external\n peer \S+ as-number \d+[\s\S]*? group \S+ external\n peer \S+ as-number \d+[\s\S]*?ipv4-family unicast\n  network \d+.\d+.\d+.\d+ \d+.\d+.\d+.\d+[\s\S]*?maximum load-balancing 32\n  peer \S+ enable\n  peer \S+ route-policy \S+ export\n  peer \S+ advertise-community\n  peer \S+ route-update-interval 0[\s\S]*?peer \S+ enable\n  peer \S+ advertise-community\n  peer \S+ route-update-interval 0[\s\S]*?route-policy \S+ permit node 10\n apply as-path \d+ overwrite',
                        fileTxt,
                        re.IGNORECASE)
                    matchLeafBgp = re.search(
                        r'bgp\s+\d+\n\s+router-id\s+\S+\n timer keepalive 30 hold 90\n advertise lowest-priority all-address-family peer-up delay 120\n private-4-byte-as disable[\s\S]*?group \S+ external\n peer \S+ as-number \S+[\s\S]*?ipv4-family unicast[\s\S]*?maximum load-balancing 32[\s\S]*?peer \S+ enable\n\s+peer \S+ advertise-community\n\s+peer \S+ route-update-interval 0',
                        fileTxt, re.IGNORECASE)
                    if checkItems['type'] in ['Leaf']:  # leafBGP
                        if matchLeafBgp:
                            checkResult.append('通过')
                        else:
                            checkResult.append('未通过')
                    else:  # 其他BGP
                        if matchSpineBgp:
                            checkResult.append('通过')
                        else:
                            checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'snmp配置':
                if value == 1:
                    # 执行snmp配置检查逻辑
                    if genCheckOtion(
                            'snmp-agent\nsnmp-agent local-engineid \S+\nsnmp-agent community read cipher.*?mib-view iso-view.*?\n#\nsnmp-agent sys-info location.*?\nsnmp-agent sys-info version v2c v3\nsnmp-agent community complexity-check disable\n#\nsnmp-agent usm-user password complexity-check disable\nsnmp-agent mib-view included iso-view iso\n#\nsnmp-agent blacklist ip-block disable\n#\nsnmp-agent protocol source-status all-interface\nundo snmp-agent protocol source-status ipv6 all-interface\n#\nundo snmp-agent proxy protocol source-status all-interface\nundo snmp-agent proxy protocol source-status ipv6 all-interface',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'LLDP配置':
                if value == 1:
                    # 执行LLDP配置检查逻辑
                    if genCheckOtion('lldp enable', fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'ssh配置':
                if value == 1:
                    # 执行ssh配置检查逻辑
                    if genCheckOtion(
                            'stelnet server enable\nssh server rsa-key min-length 3072\nssh server-source all-interface\nundo ssh ipv6 server-source all-interface\nssh authorization-type default aaa\n#\nssh server cipher aes256_gcm aes128_gcm aes256_ctr aes192_ctr aes128_ctr aes256_cbc aes192_cbc aes128_cbc arcfour256 arcfour128 3des_cbc blowfish_cbc des_cbc\nssh server hmac sha2_512 sha2_256_96 sha2_256 sha1 sha1_96 md5 md5_96\nssh server key-exchange dh_group_exchange_sha256 dh_group_exchange_sha1 dh_group14_sha1 dh_group1_sha1 ecdh_sha2_nistp256 ecdh_sha2_nistp384 ecdh_sha2_nistp521 sm2_kep dh_group16_sha512 curve25519_sha256\n#\nssh server publickey dsa ecc rsa rsa_sha2_256 rsa_sha2_512\n#\nssh server dh-exchange min-len 2048\n#\nssh client publickey ecc rsa_sha2_256 rsa_sha2_512\n#\nssh client cipher aes256_gcm aes128_gcm aes256_ctr aes192_ctr aes128_ctr\nssh client hmac sha2_512 sha2_256\nssh client key-exchange dh_group_exchange_sha256 dh_group16_sha512',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'cmd权限配置':
                if value == 1:
                    # 执行cmd权限配置检查逻辑
                    if genCheckOtion(
                            'command-privilege level 1 view shell dir\ncommand-privilege level 1 view global display\ncommand-privilege level 1 view shell save\ncommand-privilege level 1 view shell screen-length',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'user-interface配置':
                if value == 1:
                    # 执行user-interface配置检查逻辑
                    if genCheckOtion(
                            'user-interface maximum-vty 21\n#\nuser-interface con 0\n authentication-mode password\n set authentication password cipher \S+\n idle-timeout 10 0\n#\nuser-interface vty 0 20\n authentication-mode aaa\n user privilege level 3\n protocol inbound ssh',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'hash配置':
                if value == 1:
                    # 执行hash配置检查逻辑
                    if genCheckOtion('load-balance ecmp\s*\n\s*hashmode underlay 2', fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case '带外接口配置':
                if value == 1:
                    # 执行带外接口配置检查逻辑
                    if genCheckOtion(
                            'interface MEth\S+\s*\n\s*description Out-Of-OOB\s*\n\s*ip binding vpn-instance OOB\s*\n\s*ip address \d+\.\d+\.\d+\.\d+ 255.255.255.0',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'loopback配置':
                if value == 1:
                    # 执行loopback配置检查逻辑
                    if genCheckOtion(
                            'interface LoopBack1\s*\n\s*description \S+\s*\n\s*ip address \d+\.\d+\.\d+\.\d+ 255.255.255.255',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'peerlink配置':
                if value == 1:
                    # 执行peerlink配置检查逻辑
                    matchPeerlinkEth = re.search(
                        r'interface Eth-Trunk100\s*\n\s*description To_\S+_Eth-Trunk100\s*\n\s*mode lacp-static\s*\n\s*peer-link 1',
                        fileTxt,
                        re.IGNORECASE)
                    matchPeerlinkPort = re.findall(
                        r'interface 100GE1/0/[37]\s*\n\s*description To_\S+_100GE1/0/[37]\s*\n\s*eth-trunk 100',
                        fileTxt,
                        re.IGNORECASE)
                    if matchPeerlinkEth and len(matchPeerlinkPort) == 2:
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'DAD配置':
                if value == 1:
                    # 执行DAD配置检查逻辑
                    matchDadEth = re.search(
                        r'interface Eth-Trunk101\s*\n\s*undo portswitch\s*\n\s*description To_\S+_Eth-Trunk101\s*\n\s*ip binding vpn-instance DAD\s*\n\s*ip address \d+\.\d+\.\d+\.\d+ 255.255.255.252\s*\n\s*mode lacp-static\s*\n\s*m-lag unpaired-port reserved',
                        fileTxt,
                        re.IGNORECASE)
                    matchDadPort = re.findall(
                        r'interface 25GE1/0/4[678]\s*\n\s*description To_\S+_25GE1/0/4[678]\s*\n\s*eth-trunk 101',
                        fileTxt,
                        re.IGNORECASE)
                    if matchDadEth and len(matchDadPort) == 2:
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case 'monitor-link配置':
                if value == 1:
                    # 执行monitor-link配置检查逻辑
                    if genCheckOtion(
                            'monitor-link group 1\s*\n\s*port 100GE1/0/1 uplink\s*\n\s*port 100GE1/0/2 uplink\s*\n\s*port 100GE1/0/5 uplink\s*\n\s*port 100GE1/0/6 uplink\s*\n\s*port 25GE1/0/1 downlink 1\s*\n\s*port 25GE1/0/2 downlink 2\s*\n\s*port 25GE1/0/3 downlink 3\s*\n\s*port 25GE1/0/4 downlink 4\s*\n\s*port 25GE1/0/5 downlink 5\s*\n\s*port 25GE1/0/6 downlink 6\s*\n\s*port 25GE1/0/7 downlink 7\s*\n\s*port 25GE1/0/8 downlink 8\s*\n\s*port 25GE1/0/9 downlink 9\s*\n\s*port 25GE1/0/10 downlink 10\s*\n\s*port 25GE1/0/11 downlink 11\s*\n\s*port 25GE1/0/12 downlink 12\s*\n\s*port 25GE1/0/13 downlink 13\s*\n\s*port 25GE1/0/14 downlink 14\s*\n\s*port 25GE1/0/15 downlink 15\s*\n\s*port 25GE1/0/16 downlink 16\s*\n\s*port 25GE1/0/17 downlink 17\s*\n\s*port 25GE1/0/18 downlink 18\s*\n\s*port 25GE1/0/19 downlink 19\s*\n\s*port 25GE1/0/20 downlink 20\s*\n\s*port 25GE1/0/21 downlink 21\s*\n\s*port 25GE1/0/22 downlink 22\s*\n\s*port 25GE1/0/23 downlink 23\s*\n\s*port 25GE1/0/24 downlink 24\s*\n\s*port 25GE1/0/25 downlink 25\s*\n\s*port 25GE1/0/26 downlink 26\s*\n\s*port 25GE1/0/27 downlink 27\s*\n\s*port 25GE1/0/28 downlink 28\s*\n\s*port 25GE1/0/29 downlink 29\s*\n\s*port 25GE1/0/30 downlink 30\s*\n\s*port 25GE1/0/31 downlink 31\s*\n\s*port 25GE1/0/32 downlink 32\s*\n\s*port 25GE1/0/33 downlink 33\s*\n\s*port 25GE1/0/34 downlink 34\s*\n\s*port 25GE1/0/35 downlink 35\s*\n\s*port 25GE1/0/36 downlink 36\s*\n\s*port 25GE1/0/37 downlink 37\s*\n\s*port 25GE1/0/38 downlink 38\s*\n\s*port 25GE1/0/39 downlink 39\s*\n\s*port 25GE1/0/40 downlink 40\s*\n\s*port 25GE1/0/41 downlink 41\s*\n\s*port 25GE1/0/42 downlink 42\s*\n\s*port 25GE1/0/43 downlink 43\s*\n\s*port 25GE1/0/44 downlink 44\s*\n\s*port 25GE1/0/45 downlink 45\s*\n\s*port 25GE1/0/4[68] downlink 4[68]\s*\n\s*timer recover-time 40',
                            fileTxt):
                        checkResult.append('通过')
                    else:
                        checkResult.append('未通过')
                else:
                    checkResult.append('不涉及')

            case _:
                checkResult.append(f'未知配置项: {checkItem}')
        logger.get_log().info(f'{checkItems["name"]}的检查项\"{checkItem}\"设置为\"{value}\",检查完成')
    return checkResult


def genCheckOtion(reinfo, fileTxt):
    return re.search(r'%s' % reinfo, fileTxt, re.IGNORECASE)


if __name__ == '__main__':
    pass
