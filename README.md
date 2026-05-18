# 华为交换机配置检查工具

用于对华为交换机离线配置文件（.log）进行自动化合规检查，生成 Excel 报告。

## 功能

1. **配置检查** — 对 read/config/ 目录下的 .log 配置文件，按设备类型逐项检查合规项
2. **在线检查** — 通过 SSH/Telnet 登录设备，读取配置并实时检查
3. **命令下发** — 批量登录设备下发配置命令
4. **版本补丁对照** — 采集版本/补丁号，与本地 Excel 对照表比对

## 项目结构

```
mywork_script/
├── main.py                 # 入口，功能菜单
├── cfgCheck.py             # 离线配置文件检查（合规性审计）
├── checkConfig.py          # 在线配置检查
├── compare_configs.py      # 配置下发验证比对（意图 .cfg vs 采集 .log）
├── sendCmd.py              # 命令下发
├── mergeExcel.py           # 巡检报告汇总
├── config/
│   ├── __init__.py
│   └── check_items.py      # 检查项名称 & 设备类型配置表
├── interface/
│   ├── connection.py       # 交换机登录、Excel 处理
│   ├── public_env.py       # 全局变量、日志、线程池
│   └── bitFunctions.py     # 网段计算
├── read/
│   ├── config/             # 局点采集的配置文件 (.log)
│   ├── config_intended/    # 意图配置文件 (.cfg) ← 你出的配置放这
│   ├── ignore_rules.yaml   # 过滤规则表（所有过滤/忽略统一在这里配）
│   ├── 版本补丁.xlsx       # 版本补丁推荐对照表
│   ├── keyWords.txt        # 在线检查关键字
│   └── devices_ip.xlsx     # 设备 IP 清单
├── data/                   # 输出目录（Excel 报告 + 比对报告）
└── log/                    # 运行日志
```

## 配置检查（cfgCheck.py）

### 核心流程

1. 读取 `read/config/` 下的 `.log` 配置文件
2. 根据文件名匹配设备类型（Spine / Leaf / Slf 等）
3. 按设备类型的检查项配置（0/1），逐项执行检查
4. 结果写入 Excel 报告

### 新增检查项

两步：

1. **`config/check_items.py`** — `CHECK_ITEM_NAMES` 末尾加名称，在需要的设备类型配置中加一行
2. **`cfgCheck.py`** — 写一个 `_check_xxx()` 函数，在 `_CHECKERS` 字典注册

Excel 报告列头自动从 `CHECK_ITEM_NAMES` 生成，无需修改 `main.py`。

### 新增设备类型

1. **`config/check_items.py`** — `_make_check_option()` 定义检查项，`DEVICE_TYPE_CONFIGS` 注册，`DEVICE_TYPE_PATTERNS` 加匹配规则

### 版本补丁对照

启动时自动加载 `read/版本补丁.xlsx` → `版本补丁推荐（季度）` sheet，筛选 `使用场景=新上线` 建立对照表。

- 采集版本/补丁与推荐一致 → 正常返回
- 不一致 → 返回 `@未通过`
- 型号不在对照表中 → 返回 `-未知`

## 运行

```bash
cd mywork_script
.venv/bin/python main.py
```

菜单：
- 1 — 在线配置检查
- 2 — 离线配置文件检查（主要功能）
- 3 — 下发配置
- 4 — 配置下发验证（比对意图 .cfg vs 采集 .log）

## 配置下发验证（compare_configs.py）

将你出的意图配置（.cfg）与局点采集的配置（.log）进行比对，
检测"我要的你刷了没"的差异，输出排查报告到 `data/` 目录。

### 用法

```bash
.venv/bin/python compare_configs.py
```

或在主菜单选 **4**。

### 工作流程

```
你出 .cfg → read/config_intended/     ← 你放意图配置文件
局点交 .log → read/config/            ← 局点采集的配置
运行脚本 → data/配置比对报告_时间戳.txt ← 对比报告输出
```

### 比对报告内容

- 每台设备的**型号和版本**信息（从 .log 提取，同 cfgCheck.py 规则）
- **[缺失]** — .cfg 里有但 .log 里没有，局点没刷上的配置
- **[多余]** — .log 里有但 .cfg 里没有，局点多配或设备自动生成的配置
- **[告警]** — 设备上的 `display alarm active` 告警信息
- **汇总** — 一致/差异/未采集各多少台

### 三层过滤机制

所有过滤规则统一在 `read/ignore_rules.yaml` 中配置，代码不保留硬编码列表。

| 层级 | YAML 节 | 作用 | 场景 |
|---|---|---|---|
| noise | `noise` | 两边都不比对 | 设备自动生成的噪音（WLAN、硬件检测、默认段等） |
| ignore_missing | `ignore_missing` | 不报"缺失" | 配了但不回显的命令（lldp enable、pki 等） |
| ignore_extra | `ignore_extra` | 不报"多余" | 设备自动生成的配置（SNMP alias、capwap 等） |

#### noise 节（43条规则）

自动生成的配置内容，不参与比对。想关掉某条规则，YAML 里行首加 `#`：

```yaml
noise:
  - "^device\\s+(board|card|transceiver|fan|power)\\s+"
  # - "^shutdown$"    ← 注释掉这行，shutdown 就会开始参与比对
```

#### 型号/版本差异化规则

每条规则可以附带 `models` 和 `versions` 约束，只有设备型号/版本匹配时才生效：

```yaml
ignore_missing:
  - pattern: "lldp enable"
    models: ["S5731"]           # 仅 S5731 系列生效
    versions: ["V200R024.*"]    # 仅该版本生效（正则）
```

型号和版本的提取规则与 **cfgCheck.py** 完全一致。

### SSH 密码套件无序比较

SSH 密码套件（`ssh server cipher`、`ssh client hmac` 等）后面的算法列表
在 .cfg 和 .log 中顺序可能不同，工具会自动做**集合归一化**（排序后比对），
不会因为顺序不同而误报差异。

### 文件名规则

- **.cfg 文件名必须与 .log 去掉 IP 前缀后的名字一致**
  - 例：.log `12.255.190.206_SZBL1D4FC01U31...log`
  - .cfg 应为 `SZBL1D4FC01U31...cfg`
