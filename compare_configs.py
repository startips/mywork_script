#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
compare_configs.py — 配置下发验证比对工具 v2

功能：
    将预期配置（config_intended/*.cfg）与设备实际采集配置（config/*.log）
    进行差异分析，找出漏配和多配。结果输出 Markdown 报告到 data/ 目录。

使用方式：
    python compare_configs.py

流程：
    1. 加载规则 → 2. 匹配设备 → 3. 正则提取段落 → 4. 忽略过滤
    → 5. 密码归一化 → 6. 集合差集对比 → 7. 输出报告
"""

import os
import re
import ipaddress
from datetime import datetime
import yaml
import logging
from interface.log_config import setup_logging

logger = logging.getLogger(__name__)

# ============================================================
# 路径常量
# ============================================================
INTENDED_DIR = 'read/config_intended'
COLLECTED_DIR = 'read/config'
RULES_PATH = 'read/compare_rules_v2.yaml'
OUTPUT_DIR = 'data'


# ============================================================
# 工具函数
# ============================================================

def _read_file(path):
    """读取文件内容，失败返回 None"""
    try:
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    except Exception:
        logger.debug('文件读取失败: %s', path)
        return None


# ============================================================
# 1. 加载规则
# ============================================================

def load_rules(rules_path):
    """加载 YAML 规则文件，失败返回空规则"""
    logger.info('加载规则文件: %s', rules_path)
    content = _read_file(rules_path)
    if not content:
        print(f'[警告] 规则文件 {rules_path} 读取失败')
        return {'sections': [], 'ignore': {'global': [], 'sections': []}}
    logger.info('规则文件加载成功')
    return yaml.safe_load(content) or {'sections': [], 'ignore': {'global': [], 'sections': []}}


# ============================================================
# 2. 设备配对
# ============================================================

def _dev_name_from_cfg(filename):
    """从 .cfg 文件名提取设备名"""
    return filename.replace('.cfg', '')


def _dev_name_from_log(filename, cfg_names):
    """
    从采集文件名提取设备名，两级匹配。

    文件名格式通常为「管理IP_设备名.log」或「设备名.txt」。
    1. 先用去掉后缀的完整文件名匹配 cfg 名
    2. 匹配不到则用正则去掉「IP地址_」前缀后再匹配
    """
    name = re.sub(r'\.(log|txt)$', '', filename)
    # 第一级：完整文件名匹配
    if name in cfg_names:
        return name
    # 第二级：去掉 IP 前缀（匹配 x.x.x.x_ 格式）
    m = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}_(.+)', name)
    if m and m.group(1) in cfg_names:
        return m.group(1)
    # 都匹配不到，返回去掉 IP 前缀的结果（后续配对会归入 only_collected）
    return m.group(1) if m else name


def match_devices(intended_dir, collected_dir):
    """将 config_intended/*.cfg 与 config/*.log 按设备名配对"""
    logger.info('开始设备配对: 预期目录=%s, 采集目录=%s', intended_dir, collected_dir)
    # 先扫预期目录，建立 cfg 名集合
    intended_files = {}
    if os.path.isdir(intended_dir):
        for f in os.listdir(intended_dir):
            if f.endswith('.cfg') and not f.startswith('.'):
                intended_files[_dev_name_from_cfg(f)] = os.path.join(intended_dir, f)

    cfg_names = set(intended_files.keys())
    logger.debug('预期目录扫描到 %d 个cfg文件', len(intended_files))

    # 扫采集目录，用两级匹配提取设备名
    collected_files = {}
    if os.path.isdir(collected_dir):
        for f in os.listdir(collected_dir):
            if f.endswith(('.log', '.txt')) and not f.startswith('.'):
                dev_name = _dev_name_from_log(f, cfg_names)
                collected_files[dev_name] = os.path.join(collected_dir, f)

    logger.debug('采集目录扫描到 %d 个文件', len(collected_files))

    # 取并集，分类
    all_devices = set(intended_files.keys()) | set(collected_files.keys())
    matched, only_intended, only_collected = [], [], []

    # 按设备名字典序遍历，保证多次运行报告顺序稳定一致（便于跨报告逐行对比）。
    # set 的遍历顺序受 PYTHONHASHSEED 影响（默认每次随机），不排序会导致报告设备顺序每次不同。
    for dev_name in sorted(all_devices):
        cfg = intended_files.get(dev_name)
        log = collected_files.get(dev_name)
        if cfg and log:
            matched.append((dev_name, cfg, log))
        elif cfg:
            only_intended.append(cfg)
        else:
            only_collected.append(log)

    logger.info('设备配对完成: 匹配 %d 台, 仅预期 %d 台, 仅采集 %d 台', len(matched), len(only_intended), len(only_collected))
    return matched, only_intended, only_collected


# ============================================================
# 3. 采集日志中提取配置段 + 型号版本
# ============================================================

def extract_collected_config(text):
    """从采集日志中提取 display current-configuration 输出段"""
    m = re.search(r'display current-configuration([\s\S]*?return)', text, re.IGNORECASE)
    if not m:
        logger.debug('未从采集日志中提取到 display current-configuration 配置段')
    return m.group(1).strip() if m else None


def extract_model_version(log_text):
    """从 display version 输出中提取型号和版本号"""
    model = version = None
    ver_section = re.search(
        r'display version[^\n]*\n(.*?)(?=\n\s*<|\Z)',
        log_text, re.IGNORECASE | re.DOTALL
    )
    if ver_section:
        vt = ver_section.group(0)
        mm = re.search(r'HUAWEI\s+(\S+)\s+(?:Routing Switch\s+)?uptime is', vt, re.IGNORECASE)
        if mm:
            model = mm.group(1)
        vm = re.search(r'Version\s+\S+\s+\(\S+\s+(V?\d+R\d+C\d+(?:SPC\d+)?)\)', vt, re.IGNORECASE)
        if vm:
            version = vm.group(1)
    logger.debug('提取型号版本: model=%s, version=%s', model, version)
    return model, version


# ============================================================
# 4. 正则提取段落 → 结构化配置
# ============================================================

def _split_sub_blocks(block_text, split_by):
    """
    将段落文本按 split_by 正则拆分子段。

    例如 interface 块可能含 GE0/0/1 ~ GE0/0/48，
    按 '^interface ' 拆成每个接口一个子段。

    返回: [(子段头, [子命令行]), ...]
    """
    lines = [l.strip() for l in block_text.strip().split('\n')]
    # 去掉末尾的 # 行
    if lines and lines[-1] == '#':
        lines = lines[:-1]

    sub_blocks = []
    cur_header = None
    cur_body = []

    for line in lines:
        if not line:
            continue
        if re.match(split_by, line, re.IGNORECASE):
            if cur_header is not None:
                sub_blocks.append((cur_header, cur_body))
            cur_header = line
            cur_body = []
        else:
            cur_body.append(line)

    if cur_header is not None:
        sub_blocks.append((cur_header, cur_body))

    return sub_blocks


def parse_config(text, sections_def):
    """
    用 sections_def 中每条的正则从全文提取段落，剩余归全局。

    参数：
        text: 配置全文
        sections_def: YAML 中 sections 列表

    返回：
        {
            'global': ['行1', '行2', ...],
            'sections': {
                '端口配置': {
                    'interface GE0/0/1': ['shutdown', 'port link-type access'],
                    ...
                },
                ...
            }
        }
    """
    if not sections_def:
        # 没有定义段落，全部归全局
        logger.debug('无段落定义, 全部归全局')
        return {
            'global': [l.strip() for l in text.split('\n') if l.strip()],
            'sections': {},
        }

    # 收集所有正则匹配的 (start, end, section_def, match_text)
    all_matches = []
    for sec in sections_def:
        for m in re.finditer(sec['regex'], text, re.IGNORECASE | re.DOTALL):
            all_matches.append((m.start(), m.end(), sec))

    # 按位置排序
    all_matches.sort(key=lambda x: x[0])

    # 提取段落 → 拆分子段
    sections = {}
    matched_ranges = []

    for start, end, sec in all_matches:
        matched_ranges.append((start, end))
        block_text = text[start:end]
        sub_blocks = _split_sub_blocks(block_text, sec['split_by'])

        name = sec['name']
        if name not in sections:
            sections[name] = {}
        for sub_h, sub_b in sub_blocks:
            sections[name][sub_h] = sub_b

    # 提取全局行（不在任何匹配区间内的文本）
    matched_ranges.sort()
    merged = []
    for s, e in matched_ranges:
        if merged and s <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], e))
        else:
            merged.append((s, e))

    remaining_parts = []
    prev = 0
    for s, e in merged:
        remaining_parts.append(text[prev:s])
        prev = e
    remaining_parts.append(text[prev:])

    global_text = ''.join(remaining_parts)
    global_lines = [l.strip() for l in global_text.split('\n') if l.strip()]

    logger.debug('配置解析完成: 全局行 %d, 段落 %d 个', len(global_lines), len(sections))
    return {'global': global_lines, 'sections': sections}


# ============================================================
# 5. 忽略过滤 + 密码归一化
# ============================================================

def _match_any(line, patterns):
    """行是否匹配任意一个正则（re.search，ignore_case）"""
    for pat in patterns:
        if pat.search(line):
            return True
    return False


def _match_model_version(rule, model, version):
    """
    判断规则是否匹配当前设备的型号/版本。

    规则通过 models 字段指定型号+版本条件：
    - 列表内每对 model+version 是 AND 关系
    - 列表项之间是 OR 关系
    - 无 models 字段 → 匹配所有设备
    - entry 中只写 model 不写 version → 只匹配型号
    - entry 中只写 version 不写 model → 只匹配版本

    YAML 示例：
        - pattern: 'xxx'
          models:
            - model: 'CE6881'
              version: 'V200R024'
            - model: 'S5731'
              version: 'V200R023'
    """
    if not isinstance(rule, dict):
        return True  # 纯字符串规则，无条件

    models_list = rule.get('models')
    if not models_list:
        return True  # 无 models 字段，匹配所有设备

    for entry in models_list:
        if not isinstance(entry, dict):
            continue
        rm = entry.get('model')
        rv = entry.get('version')
        if rm is not None and (model is None or rm not in model):
            continue  # model 不匹配，试下一个
        if rv is not None and (version is None or rv not in version):
            continue  # version 不匹配，试下一个
        return True  # 当前 entry 命中
    return False  # 所有 entry 都没命中


def _compile_global_ignores(global_rules, model, version):
    """
    从全局忽略规则中过滤出匹配当前设备的，编译为正则列表。
    规则可以是 str 或 dict{pattern, model?, version?}。
    """
    patterns = []
    for rule in (global_rules or []):
        if not _match_model_version(rule, model, version):
            continue
        p = rule if isinstance(rule, str) else rule.get('pattern', '')
        if p:
            patterns.append(re.compile(p, re.IGNORECASE))
    return patterns


def _compile_section_ignores(section_rules, model, version):
    """
    从段落忽略规则中过滤匹配当前设备的，返回 [(compiled_header, [compiled_line]), ...]。
    """
    compiled = []
    for rule in (section_rules or []):
        if not isinstance(rule, dict):
            continue
        if not _match_model_version(rule, model, version):
            continue
        hp = rule.get('header_pattern', '')
        lps = rule.get('lines', [])
        if hp and lps:
            compiled.append((
                re.compile(hp, re.IGNORECASE),
                [re.compile(lp, re.IGNORECASE) for lp in lps],
            ))
    return compiled


def apply_ignore(config_data, ignore_rules, model=None, version=None):
    """
    对解析后的配置应用忽略规则（统一，两侧相同）。

    全局行：匹配 global 正则的直接丢弃
    段落行：先匹配 header_pattern，再匹配 lines 的直接丢弃
    """
    logger.debug('开始应用忽略规则: model=%s, version=%s', model, version)
    global_ignores = _compile_global_ignores(
        ignore_rules.get('global', []), model, version)
    section_ignores = _compile_section_ignores(
        ignore_rules.get('sections', []), model, version)

    result = {'global': [], 'sections': {}}

    # 过滤全局行
    for line in config_data.get('global', []):
        if not _match_any(line, global_ignores):
            result['global'].append(line)

    # 过滤段落行
    for cat_name, sub_dict in config_data.get('sections', {}).items():
        result['sections'][cat_name] = {}
        for header, body_lines in sub_dict.items():
            kept = []
            for line in body_lines:
                # 检查段落级忽略
                skip = False
                for ch, cl in section_ignores:
                    if ch.match(header) and _match_any(line, cl):
                        skip = True
                        break
                if not skip:
                    kept.append(line)
            result['sections'][cat_name][header] = kept

    logger.debug('忽略规则应用完成: 全局行 %d, 段落分类 %d', len(result['global']), len(result['sections']))
    return result


def normalize_passwords(config_data):
    """
    将密码密文归一化为占位符，避免加密结果差异导致误报。

    Huawei 每次 display 加密结果可能不同，但配置功能相同。
    """

    def _norm(line):
        # password irreversible-cipher <密文>
        line = re.sub(r'(password\s+irreversible-cipher\s+)\S+', r'\1<密文>', line)
        # snmp-agent community read cipher <密文>
        line = re.sub(r'(snmp-agent\s+community\s+read\s+cipher\s+)\S+\s+mib-view\s+iso-view(?:\s+alias\s+\S+)?',
                      r'\1<密文>', line)
        # set authentication password cipher <密文>set authentication password cipher
        line = re.sub(r'(set\s+authentication\s+password\s+cipher\s+)\S+', r'\1<密文>', line)
        # mlag
        line = re.sub(r'(authentication-mode hmac-sha256 password\s+)\S+', r'\1<密文>', line)
        return line

    result = {'global': [], 'sections': {}}
    for line in config_data.get('global', []):
        result['global'].append(_norm(line))
    for cat, sub in config_data.get('sections', {}).items():
        result['sections'][cat] = {}
        for h, lines in sub.items():
            result['sections'][cat][h] = [_norm(l) for l in lines]
    logger.debug('密码归一化完成: 全局行 %d, 段落分类 %d', len(result['global']), len(result['sections']))
    return result


# ============================================================
# 6. SSH 密码套件比较（无序集合）
# ============================================================

# IPv6 地址匹配正则：至少含两个冒号，可带 /prefix
# 用 [0-9a-fA-F]{0,4} 允许空段以匹配 :: 形式
_IPV6_RE = re.compile(
    r'(?<![0-9a-fA-F:])'                      # 前面不能紧跟十六进制或冒号（避免误匹配子串）
    r'([0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{0,4}){2,7})'
    r'(/\d{1,3})?'                           # 可选前缀
)


def _norm_ipv6_in_line(line):
    """将行内出现的 IPv6 地址归一化为压缩形式（compressed）。

    解决预期配置与采集配置 IPv6 写法差异导致的误报：
    - 前导零：0B05 vs B05、::0006 vs ::6
    - 大小写：已被 _ci_diff 的 lowercase 处理，这里不关心

    归一化示例：
        2405:1fc0:0B05:3129::0006/126  →  2405:1fc0:b05:3129::6/126
        2405:1FC0:10:2900:FFFF:FFFF:FFFF:FFFD/64 → 2405:1fc0:10:2900:ffff:ffff:ffff:fffd/64

    实现策略：用 finditer 找所有候选 token（连续十六进制+冒号串，
    至少含两个冒号），逐个尝试用 ipaddress.IPv6Address 解析。
    解析成功才替换，失败原样保留，避免部分匹配导致畸形拼接。
    """
    tokens = re.findall(r'[0-9a-fA-F]{1,4}(?::[0-9a-fA-F]{0,4})+', line)
    for tok in tokens:
        try:
            addr = ipaddress.IPv6Address(tok)
        except ValueError:
            continue   # 非法 IPv6，跳过
        # 行内定位该 token（连同可能的 /prefix），用压缩形式替换
        pattern = re.compile(r'(?<![0-9a-fA-F:])' + re.escape(tok) + r'(/\d{1,3})?')
        line = pattern.sub(
            lambda m: f'{addr.compressed}{m.group(1) or ""}',
            line, count=1
        )
    return line


def normalize_ipv6(config_data):
    """对配置数据中所有行的 IPv6 地址做压缩归一化（两侧相同规则）。"""
    result = {'global': [], 'sections': {}}
    for line in config_data.get('global', []):
        result['global'].append(_norm_ipv6_in_line(line))
    for cat, sub in config_data.get('sections', {}).items():
        result['sections'][cat] = {}
        for h, lines in sub.items():
            result['sections'][cat][h] = [_norm_ipv6_in_line(l) for l in lines]
    logger.debug('IPv6 归一化完成: 全局行 %d, 段落分类 %d',
                 len(result['global']), len(result['sections']))
    return result


def _parse_ssh_cipher_line(line):
    """提取 SSH cipher/hmac 行的套件集合"""
    m = re.match(
        r'(ssh\s+(?:server|client)\s+(?:cipher|hmac|key-exchange|publickey)\s+)(.*)',
        line, re.IGNORECASE
    )
    return set(m.group(2).split()) if m else None


def _ssh_cipher_diff(i_lines, a_lines):
    """SSH 密码套件无序集合比较"""
    logger.debug('开始SSH密码套件比较')
    i_sets = {l: s for l in i_lines if (s := _parse_ssh_cipher_line(l))}
    a_sets = {l: s for l in a_lines if (s := _parse_ssh_cipher_line(l))}

    missing, extra = [], []
    a_remaining = dict(a_sets)

    for i_line, i_set in i_sets.items():
        m = re.match(r'(ssh\s+\S+\s+\S+)', i_line, re.IGNORECASE)
        cmd_i = m.group(1).lower() if m else ''
        matched = False
        for a_line, a_set in list(a_remaining.items()):
            m = re.match(r'(ssh\s+\S+\s+\S+)', a_line, re.IGNORECASE)
            cmd_a = m.group(1).lower() if m else ''
            if cmd_i == cmd_a:
                matched = True
                ms = i_set - a_set
                es = a_set - i_set
                if ms:
                    missing.append(f'{cmd_i} 缺失: {" ".join(sorted(ms))}')
                if es:
                    extra.append(f'{cmd_a} 多余: {" ".join(sorted(es))}')
                del a_remaining[a_line]
                break
        if not matched:
            missing.append(f'{i_line}  (整行缺失)')

    for a_line in a_remaining:
        extra.append(f'{a_line}  (整行多余)')

    return missing, extra


# ============================================================
# 7. 对比
# ============================================================

def _ci_diff(expected, actual):
    """
    忽略大小写的集合差集，保留原始大小写用于报告。

    返回: (missing列表, extra列表)
    """
    exp_map = {l.lower(): l for l in expected}
    act_map = {l.lower(): l for l in actual}
    missing = sorted(exp_map[k] for k in set(exp_map) - set(act_map))
    extra = sorted(act_map[k] for k in set(act_map) - set(exp_map))
    return missing, extra


def compare_configs(intended, actual, model=None, version=None):
    """
    对比预期和实际配置，逐段做集合差集。

    返回: {'model': ..., 'version': ..., 'diffs': {分类: {missing/extra: [...]}}}
    """
    logger.debug('开始配置对比: model=%s, version=%s', model, version)
    result = {
        'model': model,
        'version': version,
        'diffs': {},
    }

    all_cats = set(intended.get('sections', {}).keys()) | set(actual.get('sections', {}).keys())

    for cat in sorted(all_cats):
        cat_diffs = {}

        # --- 段落比较（标题忽略大小写） ---
        i_sub = intended.get('sections', {}).get(cat, {})
        a_sub = actual.get('sections', {}).get(cat, {})

        # 建立 lowercase header → 原始 header 的映射
        i_header_map = {h.lower(): h for h in i_sub}
        a_header_map = {h.lower(): h for h in a_sub}
        all_headers = set(i_header_map) | set(a_header_map)

        missing_h = {}
        extra_h = {}
        missing_whole = []   # 整段缺失：预期有 header、采集侧无
        extra_whole = []     # 整段多余：采集有 header、预期侧无
        for lh in sorted(all_headers):
            i_h = i_header_map.get(lh)
            a_h = a_header_map.get(lh)
            # 整段缺失/多余单独标记，避免降级为逐行差异造成误报
            if i_h and not a_h:
                missing_whole.append(i_h)
                continue
            if a_h and not i_h:
                extra_whole.append(a_h)
                continue
            # 两侧都有该 header，才做段内逐行对比
            miss, extr = _ci_diff(
                i_sub.get(i_h, []),
                a_sub.get(a_h, []),
            )
            # 用预期的标题名，没有则用实际的
            h = i_h or a_h
            if miss:
                missing_h[h] = miss
            if extr:
                extra_h[h] = extr

        if missing_h:
            cat_diffs['missing_headers'] = missing_h
        if extra_h:
            cat_diffs['extra_headers'] = extra_h
        if missing_whole:
            cat_diffs['missing_whole'] = sorted(missing_whole)
        if extra_whole:
            cat_diffs['extra_whole'] = sorted(extra_whole)

        if cat_diffs:
            result['diffs'][cat] = cat_diffs

    # --- 全局比较 ---
    i_global = intended.get('global', [])
    a_global = actual.get('global', [])

    # SSH cipher 无序比较
    ssh_missing, ssh_extra = _ssh_cipher_diff(i_global, a_global)

    # 其余行集合差集（忽略大小写）
    i_rest = [l for l in i_global if not _parse_ssh_cipher_line(l)]
    a_rest = [l for l in a_global if not _parse_ssh_cipher_line(l)]

    missing, extra = _ci_diff(i_rest, a_rest)
    missing += ssh_missing
    extra += ssh_extra

    if missing or extra:
        global_diffs = {}
        if missing:
            global_diffs['missing'] = missing
        if extra:
            global_diffs['extra'] = extra
        result['diffs']['全局配置'] = global_diffs

    logger.debug('配置对比完成: %d 个分类有差异', len(result['diffs']))
    return result


# ============================================================
# 8. 生成报告
# ============================================================

def _mask_sensitive(text):
    """报告脱敏处理"""
    text = re.sub(r'(password\s+irreversible-cipher\s+)\S+', r'\1<密文>', text)
    text = re.sub(r'(snmp-agent\s+community\s+read\s+cipher\s+)\S+', r'\1<密文>', text)
    text = re.sub(r'(set\s+authentication\s+password\s+cipher\s+)\S+', r'\1<密文>', text)
    return text


def generate_report(results, timestamp):
    """生成 Markdown 报告"""
    logger.info('生成Markdown报告, 共 %d 台设备', len(results))
    lines = [
        '# 配置下发验证比对报告\n',
        f'- 生成时间: {timestamp}',
        f'- 预期配置: `{INTENDED_DIR}`',
        f'- 采集配置: `{COLLECTED_DIR}`',
        f'- 规则文件: `{RULES_PATH}`\n',
    ]

    # ======== 总览 ========
    total_devices = len(results)
    error_devices = [r for r in results if isinstance(r[1], str)]
    ok_devices = [r for r in results if not isinstance(r[1], str)]

    # 统计差异
    total_diffs = 0
    zero_diff = 0
    summary_rows = []
    for dev_name, result in ok_devices:
        diffs = result.get('diffs', {})
        count = sum(
            len(v.get('missing', [])) + len(v.get('extra', []))
            + sum(len(x) for x in v.get('missing_headers', {}).values())
            + sum(len(x) for x in v.get('extra_headers', {}).values())
            + len(v.get('missing_whole', []))
            + len(v.get('extra_whole', []))
            for v in diffs.values()
        )
        total_diffs += count
        if count == 0:
            zero_diff += 1
        model = result.get('model') or '-'
        version = result.get('version') or '-'
        summary_rows.append((dev_name, model, version, count))

    lines.append('## 总览\n')
    lines.append(f'| 项目 | 数量 |')
    lines.append(f'|------|------|')
    lines.append(f'| 比对设备 | {total_devices} 台 |')
    lines.append(f'| 异常设备 | {len(error_devices)} 台 |')
    lines.append(f'| 无差异 | {zero_diff} 台 |')
    lines.append(f'| 有差异 | {len(ok_devices) - zero_diff} 台 |')
    lines.append(f'| 差异总计 | {total_diffs} 处 |')
    lines.append('')

    if summary_rows:
        lines.append(f'| 设备 | 型号 | 版本 | 差异 |')
        lines.append(f'|------|------|------|------|')
        for dev_name, model, version, count in summary_rows:
            # 设备名太长截短
            short_name = dev_name if len(dev_name) <= 35 else dev_name[:32] + '...'
            lines.append(f'| {short_name} | {model} | {version} | {count} |')
        lines.append('')

    # 异常设备
    if error_devices:
        lines.append('### 异常设备\n')
        for dev_name, err_msg in error_devices:
            lines.append(f'- **{dev_name}**: {err_msg}')
        lines.append('')

    # ======== 详情 ========
    lines.append('## 详情\n')

    for dev_name, result in results:
        if isinstance(result, str):
            lines.append(f'### {dev_name}\n\n> {result}\n')
            continue

        model = result.get('model') or '未知型号'
        version = result.get('version') or '未知版本'
        diffs = result.get('diffs', {})

        count = sum(
            len(v.get('missing', [])) + len(v.get('extra', []))
            + sum(len(x) for x in v.get('missing_headers', {}).values())
            + sum(len(x) for x in v.get('extra_headers', {}).values())
            + len(v.get('missing_whole', []))
            + len(v.get('extra_whole', []))
            for v in diffs.values()
        )
        lines.append(f'### {dev_name}  [{model}]  [{version}]  ({count} 处)\n')

        if not diffs:
            lines.append('无差异\n')
            continue

        for cat in sorted(diffs.keys()):
            d = diffs[cat]
            lines.append(f'#### {cat}\n')

            # 段落差异
            for h in sorted(set(d.get('missing_headers', {}).keys())
                            | set(d.get('extra_headers', {}).keys())):
                lines.append(f'  - **{h}**')
                for ml in d.get('missing_headers', {}).get(h, []):
                    lines.append(f'    - `[缺失] {ml}`')
                for el in d.get('extra_headers', {}).get(h, []):
                    lines.append(f'    - `[多余] {el}`')

            # 整段缺失/多余（一侧 header 整个不存在）
            for h in d.get('missing_whole', []):
                lines.append(f'  - `[整段缺失] {h}`')
            for h in d.get('extra_whole', []):
                lines.append(f'  - `[整段多余] {h}`')

            # 全局差异
            for ml in d.get('missing', []):
                lines.append(f'  - `[缺失] {ml}`')
            for el in d.get('extra', []):
                lines.append(f'  - `[多余] {el}`')

            lines.append('')

    return _mask_sensitive('\n'.join(lines))


def generate_txt_report(results, timestamp):
    """生成纯文本报告（保留空格）"""
    logger.info('生成纯文本报告, 共 %d 台设备', len(results))
    lines = []
    lines.append('=' * 60)
    lines.append('配置下发验证比对报告')
    lines.append('=' * 60)
    lines.append(f'生成时间: {timestamp}')
    lines.append(f'预期配置: {INTENDED_DIR}')
    lines.append(f'采集配置: {COLLECTED_DIR}')
    lines.append(f'规则文件: {RULES_PATH}')
    lines.append('')

    # ======== 总览 ========
    lines.append('-' * 60)
    lines.append('总览')
    lines.append('-' * 60)

    error_devices = [r for r in results if isinstance(r[1], str)]
    ok_devices = [r for r in results if not isinstance(r[1], str)]

    for dev_name, result in results:
        if isinstance(result, str):
            lines.append(f'  {dev_name}: {result}')
            continue
        model = result.get('model') or '-'
        version = result.get('version') or '-'
        diffs = result.get('diffs', {})
        count = sum(
            len(v.get('missing', [])) + len(v.get('extra', []))
            + sum(len(x) for x in v.get('missing_headers', {}).values())
            + sum(len(x) for x in v.get('extra_headers', {}).values())
            + len(v.get('missing_whole', []))
            + len(v.get('extra_whole', []))
            for v in diffs.values()
        )
        lines.append(f'  {dev_name}  [{model}]  [{version}]  差异: {count}')

    lines.append('')

    # ======== 详情 ========
    lines.append('-' * 60)
    lines.append('详情')
    lines.append('-' * 60)

    for dev_name, result in results:
        if isinstance(result, str):
            lines.append(f'\n--- {dev_name} ---')
            lines.append(f'  异常: {result}')
            continue

        model = result.get('model') or '未知型号'
        version = result.get('version') or '未知版本'
        diffs = result.get('diffs', {})

        count = sum(
            len(v.get('missing', [])) + len(v.get('extra', []))
            + sum(len(x) for x in v.get('missing_headers', {}).values())
            + sum(len(x) for x in v.get('extra_headers', {}).values())
            + len(v.get('missing_whole', []))
            + len(v.get('extra_whole', []))
            for v in diffs.values()
        )
        lines.append(f'\n--- {dev_name}  [{model}]  [{version}]  ({count} 处) ---')

        if not diffs:
            lines.append('  无差异')
            continue

        for cat in sorted(diffs.keys()):
            d = diffs[cat]
            lines.append(f'\n  {cat}')

            # 段落差异
            for h in sorted(set(d.get('missing_headers', {}).keys())
                            | set(d.get('extra_headers', {}).keys())):
                lines.append(f'    {h}')
                for ml in d.get('missing_headers', {}).get(h, []):
                    lines.append(f'      [缺失] {ml}')
                for el in d.get('extra_headers', {}).get(h, []):
                    lines.append(f'      [多余] {el}')

            # 整段缺失/多余（一侧 header 整个不存在）
            for h in d.get('missing_whole', []):
                lines.append(f'    [整段缺失] {h}')
            for h in d.get('extra_whole', []):
                lines.append(f'    [整段多余] {h}')

            # 全局差异
            for ml in d.get('missing', []):
                lines.append(f'    [缺失] {ml}')
            for el in d.get('extra', []):
                lines.append(f'    [多余] {el}')

    return _mask_sensitive('\n'.join(lines))


# ============================================================
# 9. 主流程
# ============================================================

def process_one_device(dev_name, cfg_path, log_path, rules):
    """
    处理单台设备：解析 → 忽略 → 归一化 → 对比。
    返回: (设备名, 结果dict 或 错误信息)
    """
    logger.info('开始处理设备: %s', dev_name)
    # 读取预期配置
    cfg_text = _read_file(cfg_path)
    if cfg_text is None:
        logger.warning('%s 读取预期配置文件失败: %s', dev_name, cfg_path)
        return dev_name, '读取预期配置文件失败'

    # 读取采集日志
    log_text = _read_file(log_path)
    if log_text is None:
        logger.warning('%s 读取采集日志文件失败: %s', dev_name, log_path)
        return dev_name, '读取采集日志文件失败'

    # 提取 current-configuration 段
    collected_text = extract_collected_config(log_text)
    if collected_text is None:
        logger.warning('%s 未从采集日志中提取到配置段', dev_name)
        return dev_name, '未从采集日志中提取到配置段'

    # 提取型号版本
    model, version = extract_model_version(log_text)

    sections_def = rules.get('sections', [])
    ignore_rules = rules.get('ignore', {})

    # 解析
    intended = parse_config(cfg_text, sections_def)
    collected = parse_config(collected_text, sections_def)

    # 忽略
    intended = apply_ignore(intended, ignore_rules, model, version)
    collected = apply_ignore(collected, ignore_rules, model, version)

    # 密码归一化
    intended = normalize_passwords(intended)
    collected = normalize_passwords(collected)

    # IPv6 地址归一化（压缩形式，消除前导零写法差异）
    intended = normalize_ipv6(intended)
    collected = normalize_ipv6(collected)

    # 对比
    diff = compare_configs(intended, collected, model, version)

    logger.info('设备 %s 处理完成', dev_name)
    return dev_name, diff


def main():
    """主入口"""
    setup_logging('compare_configs')
    print('=' * 50)
    print('配置下发验证比对工具 v2')
    print('=' * 50)

    # 加载规则
    print(f'\n[1/4] 加载规则: {RULES_PATH}')
    rules = load_rules(RULES_PATH)

    # 读取 YAML 中的目录设置，未配置则用默认值
    settings = rules.get('settings', {})
    intended_dir = settings.get('intended_dir') or INTENDED_DIR
    collected_dir = settings.get('collected_dir') or COLLECTED_DIR
    output_dir = settings.get('output_dir') or OUTPUT_DIR
    print(f'  → 预期配置: {intended_dir}')
    print(f'  → 采集配置: {collected_dir}')
    print(f'  → 报告输出: {output_dir}')

    secs = rules.get('sections', [])
    for s in secs:
        print(f'  → 段落: {s["name"]} ({s["regex"][:40]}...)')
    ig = rules.get('ignore', {})
    print(f'  → 忽略规则: global {len(ig.get("global", []))} 条, '
          f'sections {len(ig.get("sections", []))} 组')

    # 设备配对
    print(f'\n[2/4] 设备配对')
    matched, only_intended, only_collected = match_devices(intended_dir, collected_dir)
    print(f'  → 匹配: {len(matched)} 台')
    if only_intended:
        print(f'  → 仅预期有（未采集）: {len(only_intended)} 台')
    if only_collected:
        print(f'  → 仅采集有（无预期）: {len(only_collected)} 台')

    if not matched:
        print('\n没有匹配的设备，退出。')
        return

    # 逐台对比
    print(f'\n[3/4] 开始比对 {len(matched)} 台设备...')
    from alive_progress import alive_bar
    results = []
    with alive_bar(title='比对进度', bar='filling', spinner='waves2',
                   total=len(matched), receipt=False, enrich_print=False) as bar:
        for dev_name, cfg_path, log_path in matched:
            name, result = process_one_device(dev_name, cfg_path, log_path, rules)
            if isinstance(result, str):
                bar.text = f'❌ {name}: {result}'
            else:
                diff_count = sum(
                    len(v.get('missing', [])) + len(v.get('extra', []))
                    + sum(len(x) for x in v.get('missing_headers', {}).values())
                    + sum(len(x) for x in v.get('extra_headers', {}).values())
                    + len(v.get('missing_whole', []))
                    + len(v.get('extra_whole', []))
                    for v in result.get('diffs', {}).values()
                )
                bar.text = f'✅ {name}: {diff_count} 处差异'
            results.append((name, result))
            bar()

    # 输出报告
    print(f'\n[4/4] 生成报告...')
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    report = generate_report(results, ts)
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, f'配置比对结果_{ts}.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'  报告已保存: {report_path}')
    print('完成。')


if __name__ == '__main__':
    main()
