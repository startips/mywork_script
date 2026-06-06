#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
device_client.py - 设备连接模块（SSH/Telnet）

提供设备登录、命令执行、数据接收功能。
"""

import re
import socket
import time
import paramiko
from telnetlib import Telnet


class deviceControl:  # 交换机登陆模块
    def __init__(self, ip, username, password, port=22):
        self.password = password
        self.username = username
        self.ip = ip
        self.port = port
        self.ssh = None
        self.ssh_shell = None
        self.tn = None
        self.t = None
        self.chan = None

    def connectDevice(self):  # 适用于连接路由，交换机。登录成功返回True
        max_retries = 2  # 连接超时最多重试2次（瞬断/忙碌场景），其他错误直接放弃
        times = 0
        while times < max_retries:
            try:
                self.ssh = paramiko.SSHClient()
                self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                self.ssh.connect(self.ip, self.port, self.username, self.password,
                                 timeout=5,  # TCP连接超时
                                 auth_timeout=5,  # 验证超时
                                 channel_timeout=5,  # 通道超时
                                 banner_timeout=5)  # 标题栏超时
                self.ssh_shell = self.ssh.invoke_shell()  # 使用invoke是为了可以执行多条命令
                self.ssh_shell.settimeout(2)  # tunnel超时
                return True
            except socket.timeout:
                # TCP连接超时：可能瞬断，允许重试
                times += 1
                try:
                    self.ssh.close()
                except OSError:
                    pass
                if times < max_retries:
                    time.sleep(2)
                continue
            except (paramiko.AuthenticationException, paramiko.SSHException, OSError, EOFError):
                # 认证失败/SSH异常/连接拒绝：重试无意义，直接放弃
                try:
                    self.ssh.close()
                except OSError:
                    pass
                break
        self.close()  # 关闭会话
        return False

    def sendCmd(self, cmd):  # 发送命令(PS:加上了回车符)，返回发送的字节数
        _cmd = cmd
        status = self.ssh_shell.send(_cmd + '\n')
        return status

    def recData(self):  # 接受返回数据
        dataAll = []  # 使用列表收集数据，避免O(n²)字符串拼接
        par = re.compile(r'---- More ----')
        while True:
            data_parts = []
            while True:  # 取一次数据，收到空就跳出
                try:
                    rec = self.ssh_shell.recv(65536)  # 64KB缓冲区，减少recv次数
                    if not rec:
                        break
                    data_parts.append(rec.decode('utf-8'))
                except (socket.timeout, EOFError):  # 超时或通道关闭即认为本次数据收完
                    break
            data = ''.join(data_parts)
            if not data:  # 获取的数据为空则跳出循环
                break
            endMark = par.search(data)
            if endMark:
                self.ssh_shell.send(' ')
            dataAll.append(data)
        return deleteUnknownStr(''.join(dataAll))

    def close(self):  # 关闭session
        if self.ssh_shell is not None:
            try:
                self.ssh_shell.close()
            except OSError:
                pass
        if self.ssh is not None:
            try:
                self.ssh.close()
            except OSError:
                pass

    def connectLinux(self):  # 适用于连接F5/netscaler设备
        try:
            self.t = paramiko.Transport(sock=(self.ip, 22))
            self.t.connect(username=self.username, password=self.password)
            self.chan = self.t.open_session(timeout=5)
            self.chan.settimeout(0.5)  # 设置session超时
            self.chan.invoke_shell()
            return True
        except (paramiko.SSHException, OSError, EOFError):
            self.close()
            return False

    def sendCmdLinux(self, cmd):  # 适用于F5/netscaler设备发送命令（PS:自带回车符），返回运行结果
        cmd += '\n'  # 命令加上回车符
        result_parts = []
        self.chan.send(cmd)  # 发送要执行的命令
        idle_count = 0
        while idle_count < 5:  # 回显很长的命令可能执行较久，通过轮询获取回显信息
            time.sleep(0.5)
            if self.chan.recv_ready():
                try:
                    ret = self.chan.recv(10240)
                    result_parts.append(ret.decode('utf-8'))
                    idle_count = 0  # 收到数据则重置计数
                except socket.timeout:
                    idle_count += 1
            else:
                idle_count += 1
        return ''.join(result_parts)

    def telnetConnect(self):
        times = 0
        while times < 2:  # 最多重试2次（SSH已失败，Telnet重试过多浪费时间）
            try:
                self.tn = Telnet(self.ip, port=23, timeout=5)  # 连接超时5秒
                break
            except (OSError, EOFError):
                times += 1
        else:
            self.telnetClose()
            return False
        # 输入登录用户名
        self.tn.read_until(b'Username:', timeout=10)
        self.tn.write(self.username.encode('ascii') + b'\n')
        # 输入登录密码
        self.tn.read_until(b'Password:', timeout=10)
        self.tn.write(self.password.encode('ascii') + b'\n')
        times = 0
        while times < 4:
            time.sleep(0.5)
            loginInfo = self.tn.read_very_eager()
            if loginInfo.endswith(b'>'):  # 判断是否登录成功
                return True
            else:
                times += 1
        self.telnetClose()
        return False

    def telnetSendReturn(self, cmd):  # 发送命令并获取数据
        try:
            self.tn.write(cmd.encode('ascii') + b'\n')
        except (OSError, EOFError):
            return ''
        data_parts = []
        times = 0
        while times < 5:
            time.sleep(0.5)
            try:
                rec = self.tn.read_very_eager().decode('utf-8')
            except (UnicodeDecodeError, OSError):
                times += 1
                continue
            data_parts.append(rec)
            if '---- More ----' in rec:
                self.tn.write(b' ')
                times = 0  # 收到 More 提示后重置计数，继续等待后续数据
            else:
                times += 1
        data = deleteUnknownStr(''.join(data_parts))
        return data

    def telnetClose(self):  # 关闭连接
        if self.tn is not None:
            try:
                self.tn.close()
            except OSError:
                pass


class deviceControl_auto(deviceControl):  # 继承deviceControl的简洁登录 SSH TELNET合并
    def __init__(self, ip, username, password, port=22):  # 继承构造方法
        super().__init__(ip, username, password, port)

    def sendCmd_auto(self, cmd_list: list):  # 使用Telnet SSH 执行多条命令返回结果
        cmd_local = list(dict.fromkeys(cmd_list))  # 去重复list
        result = {}  # 命令返回的结果
        ssh_login = self.connectDevice()  # 使用父类SSH登录
        if ssh_login:
            try:
                self.recData()  # 欢迎数据获取
                for cmd in cmd_local:
                    self.sendCmd(cmd)
                    result[cmd] = self.recData()
                result['loginWay'] = 'SSH'
            finally:
                self.close()  # 关闭会话
        else:
            telnet_login = self.telnetConnect()
            if telnet_login:
                try:
                    for cmd in cmd_local:
                        result[cmd] = self.telnetSendReturn(cmd)
                    result['loginWay'] = 'TELNET'
                finally:
                    self.telnetClose()
            else:
                raise RuntimeError(f'SSH&TELNET CONNECT ERROR: {self.ip}')
        return result


def deleteUnknownStr(line_p):  # 删除垃圾字符，转义序列字符
    # 1. 正则移除所有 ANSI CSI 序列（如 ESC[?25l 隐藏光标、ESC[1;24r 滚动区域等）
    line_p = re.sub(r'\x1b\[[0-9;?]*[a-zA-Z@]', '', line_p)
    # 2. 正则移除两字符 ESC 序列（如 ESC7 保存光标、ESC8 恢复光标等）
    line_p = re.sub(r'\x1b[^[\x1b]', '', line_p)
    # 3. 逐字符过滤不可打印字符 + 处理退格，使用列表拼接避免O(n²)开销
    result = []
    for ch in line_p:
        ac = ord(ch)
        if (32 <= ac < 127) or ac in (9, 10):  # 可打印字符 + \t + \n
            result.append(ch)
        elif ac == 8 and result:  # backspace 删除前一个字符
            result.pop()
        # \r(13) 直接跳过，不保留
    # 4. 移除 More 提示
    line = ''.join(result)
    line = re.sub(r'\s{2}---- More ----\s+', '', line)
    return line
