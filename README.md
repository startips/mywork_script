# 网络设备配置检查工具

用于对华为交换机配置文件进行自动化合规检查和配置下发验证。

## 功能

| 序号 | 功能 | 说明 |
|------|------|------|
| 1 | 在线配置检查 | SSH/Telnet 登录设备，按 keyWords.txt 关键字检查 |
| 2 | 离线配置检查 | 对 read/config/*.log 按设备类型逐项合规审计 |
| 3 | 下发配置 | 批量登录设备下发命令 |
| 4 | 配置下发验证比对 | 预期配置(.cfg) vs 采集配置(.log) 差异分析 |

## 项目结构

```
mywork_script/
├── main.py                    # 入口，功能菜单
├── cfgCheck.py                # 离线配置文件合规检查
├── checkConfig.py             # 在线配置检查
├── compare_configs.py         # 配置下发验证比对 v2
├── sendCmd.py                 # 命令下发
├── mergeExcel.py              # 巡检报告汇总
├── interface/
│   ├── check_items.py         # 检查项 & 设备类型配置表
│   ├── connection.py          # 交换机登录、Excel 处理
│   ├── public_env.py          # 全局变量、日志、线程池
│   └── bitFunctions.py        # 网段计算
├── read/
│   ├── config/                # 采集配置 (.log)
│   ├── config_intended/       # 预期配置 (.cfg)
│   ├── template/              # 配置模板
│   ├── compare_rules_v2.yaml  # 比对规则（段落定义 + 忽略规则 + 目录设置）
│   ├── keyWords.txt           # 在线检查关键字
│   ├── 版本补丁.xlsx          # 版本补丁推荐对照表
│   └── devices_ip.xlsx        # 设备 IP 清单
├── log/                       # 运行日志
└── data/                      # 输出目录（报告）
```

## 运行

```bash
cd mywork_script
.venv/bin/python main.py
```

菜单选择 `4` 进入配置比对。

也可直接运行：
```bash
.venv/bin/python compare_configs.py
```

## 配置比对规则 (compare_rules_v2.yaml)

### 全局设置

```yaml
settings:
  intended_dir: 'read/config_intended'   # 预期配置目录
  collected_dir: 'read/config'           # 采集配置目录
  output_dir: 'data'                     # 报告输出目录
```

### 段落拆分

用正则从全文提取需要独立对比的段落（避免重复配置误判），其余归入全局配置。

```yaml
sections:
  - name: '端口配置'
    regex: 'interface (?!maximum-vty|con\b|vty\b)[\s\S]*?\n#'
    split_by: '^interface '

  - name: 'BGP配置'
    regex: 'bgp \d+[\s\S]*?\n#'
    split_by: '^bgp \d+'
```

增加新类型只需加一条，不用改代码。

### 忽略规则

统一规则，预期和采集两侧同时过滤。支持按型号/版本精准匹配。

```yaml
ignore:
  global:                          # 全局行忽略
    - '^\s*#\s*$'
    - '^return$'
    - '^\|\s*no\s*$'              # display | no 残留

  sections:                        # 段落行忽略
    - header_pattern: '^interface '
      lines:
        - '^shutdown$'
        - 'device transceiver'
```

每条规则支持可选的 `model` / `version` 字段：

```yaml
    - pattern: '^specific command'
      model: 'CE6881'              # 只对 CE6881 系列生效
      version: 'V200R020'          # AND 关系，同时满足
```

## 比对流程

```
加载规则 → 设备配对 → 正则提取段落
→ 忽略过滤 → 密码归一化 → 集合差集对比 → 输出 Markdown 报告
```

报告包含总览表（每台设备差异数）和逐台详情。
