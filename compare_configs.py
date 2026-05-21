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
import time
from datetime import datetime

import yaml

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
        return None


# ============================================================
# 1. 加载规则
# ============================================================

def load_rules(rules_path):
    """加载 YAML 规则文件，失败返回空规则"""
    content = _read_file(rules_path)
    if not content:
        print(f'[警告] 规则文件 {rules_path} 读取失败')
        return {'sections': [], 'ignore': {'global': [], 'sections': []}}
    return yaml.safe_load(content) or {'sections': [], 'ignore': {'global': [], 'sections': []}}


# ============================================================
# 2. 设备配对
# ============================================================

def _dev_name_from_cfg(filename):
    """从 .cfg 文件名提取设备名"""
    return filename.replace('.cfg', '')


def _dev_name_from_log(filename, cfg_names):
    """
    从 .log 文件名提取设备名，两级匹配。

    .log 文件名格式通常为「管理IP_设备名.log」，但可能有例外。
    1. 先用去掉 .log 的完整文件名匹配 cfg 名
    2. 匹配不到则用正则去掉「IP地址_」前缀后再匹配
    """
    name = filename.replace('.log', '')
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
    # 先扫预期目录，建立 cfg 名集合
    intended_files = {}
    if os.path.isdir(intended_dir):
        for f in os.listdir(intended_dir):
            if f.endswith('.cfg') and not f.startswith('.'):
                intended_files[_dev_name_from_cfg(f)] = os.path.join(intended_dir, f)

    cfg_names = set(intended_files.keys())

    # 扫采集目录，用两级匹配提取设备名
    collected_files = {}
    if os.path.isdir(collected_dir):
        for f in os.listdir(collected_dir):
            if f.endswith('.log') and not f.startswith('.'):
                dev_name = _dev_name_from_log(f, cfg_names)
                collected_files[dev_name] = os.path.join(collected_dir, f)

    # 取并集，分类
    all_devices = set(intended_files.keys()) | set(collected_files.keys())
    matched, only_intended, only_collected = [], [], []

    for dev_name in all_devices:
        cfg = intended_files.get(dev_name)
        log = collected_files.get(dev_name)
        if cfg and log:
            matched.append((dev_name, cfg, log))
        elif cfg:
            only_intended.append(cfg)
        else:
            only_collected.append(log)

    return matched, only_intended, only_collected


# ============================================================
# 3. 采集日志中提取配置段 + 型号版本
# ============================================================

def extract_collected_config(text):
    """从采集日志中提取 display current-configuration 输出段"""
    m = re.search(r'display current-configuration([\s\S]*?return)', text, re.IGNORECASE)
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

    规则可含可选的 model / version 字段，子串匹配，AND 关系。
    无 model/version → 匹配所有设备。
    """
    if not isinstance(rule, dict):
        return True  # 纯字符串规则，无条件

    rm = rule.get('model')
    rv = rule.get('version')
    if rm is None and rv is None:
        return True

    if rm is not None:
        if model is None or rm not in model:
            return False
    if rv is not None:
        if version is None or rv not in version:
            return False
    return True


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
            if kept:
                result['sections'][cat_name][header] = kept

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
    return result


# ============================================================
# 6. SSH 密码套件比较（无序集合）
# ============================================================

def _parse_ssh_cipher_line(line):
    """提取 SSH cipher/hmac 行的套件集合"""
    m = re.match(
        r'(ssh\s+(?:server|client)\s+(?:cipher|hmac|key-exchange|publickey)\s+)(.*)',
        line, re.IGNORECASE
    )
    return set(m.group(2).split()) if m else None


def _ssh_cipher_diff(i_lines, a_lines):
    """SSH 密码套件无序集合比较"""
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

def compare_configs(intended, actual, model=None, version=None):
    """
    对比预期和实际配置，逐段做集合差集。

    返回: {'model': ..., 'version': ..., 'diffs': {分类: {missing/extra: [...]}}}
    """
    result = {
        'model': model,
        'version': version,
        'diffs': {},
    }

    all_cats = set(intended.get('sections', {}).keys()) | set(actual.get('sections', {}).keys())

    for cat in sorted(all_cats):
        cat_diffs = {}

        # --- 段落比较 ---
        i_sub = intended.get('sections', {}).get(cat, {})
        a_sub = actual.get('sections', {}).get(cat, {})
        all_headers = set(i_sub.keys()) | set(a_sub.keys())

        missing_h = {}
        extra_h = {}
        for h in sorted(all_headers):
            i_lines = set(i_sub.get(h, []))
            a_lines = set(a_sub.get(h, []))
            miss = sorted(i_lines - a_lines)
            extr = sorted(a_lines - i_lines)
            if miss:
                missing_h[h] = miss
            if extr:
                extra_h[h] = extr

        if missing_h:
            cat_diffs['missing_headers'] = missing_h
        if extra_h:
            cat_diffs['extra_headers'] = extra_h

        if cat_diffs:
            result['diffs'][cat] = cat_diffs

    # --- 全局比较 ---
    i_global = intended.get('global', [])
    a_global = actual.get('global', [])

    # SSH cipher 无序比较
    ssh_missing, ssh_extra = _ssh_cipher_diff(i_global, a_global)

    # 其余行集合差集
    i_rest = set(l for l in i_global if not _parse_ssh_cipher_line(l))
    a_rest = set(l for l in a_global if not _parse_ssh_cipher_line(l))

    missing = sorted(i_rest - a_rest) + ssh_missing
    extra = sorted(a_rest - i_rest) + ssh_extra

    if missing or extra:
        global_diffs = {}
        if missing:
            global_diffs['missing'] = missing
        if extra:
            global_diffs['extra'] = extra
        result['diffs']['全局配置'] = global_diffs

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

            # 全局差异
            for ml in d.get('missing', []):
                lines.append(f'  - `[缺失] {ml}`')
            for el in d.get('extra', []):
                lines.append(f'  - `[多余] {el}`')

            lines.append('')

    return _mask_sensitive('\n'.join(lines))


# ============================================================
# 9. 主流程
# ============================================================

def process_one_device(dev_name, cfg_path, log_path, rules):
    """
    处理单台设备：解析 → 忽略 → 归一化 → 对比。
    返回: (设备名, 结果dict 或 错误信息)
    """
    # 读取预期配置
    cfg_text = _read_file(cfg_path)
    if cfg_text is None:
        return dev_name, '读取预期配置文件失败'

    # 读取采集日志
    log_text = _read_file(log_path)
    if log_text is None:
        return dev_name, '读取采集日志文件失败'

    # 提取 current-configuration 段
    collected_text = extract_collected_config(log_text)
    if collected_text is None:
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

    # 对比
    diff = compare_configs(intended, collected, model, version)

    return dev_name, diff


def main():
    """主入口"""
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
    results = []
    for idx, (dev_name, cfg_path, log_path) in enumerate(matched, 1):
        print(f'  [{idx}/{len(matched)}] {dev_name}...', end=' ', flush=True)
        name, result = process_one_device(dev_name, cfg_path, log_path, rules)
        if isinstance(result, str):
            print(f'❌ {result}')
        else:
            diff_count = sum(
                len(v.get('missing', [])) + len(v.get('extra', []))
                + sum(len(x) for x in v.get('missing_headers', {}).values())
                + sum(len(x) for x in v.get('extra_headers', {}).values())
                for v in result.get('diffs', {}).values()
            )
            print(f'{diff_count} 处差异')
        results.append((name, result))

    # 输出报告
    print(f'\n[4/4] 生成报告...')
    ts = datetime.now().strftime('%Y-%m-%d_%H%M%S')
    report = generate_report(results, ts)
    os.makedirs(output_dir, exist_ok=True)
    report_path = os.path.join(output_dir, f'compareResult_{ts}.md')
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    print(f'  报告已保存: {report_path}')
    print('完成。')


if __name__ == '__main__':
    main()
