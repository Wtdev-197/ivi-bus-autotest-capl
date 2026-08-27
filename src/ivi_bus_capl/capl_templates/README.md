# CAPL 模板目录

> 本目录为 `ivi-bus-autotest-capl` 项目的 CAPL 脚本模板存储位置。

---

## 设计意图

当前阶段，CAPL 脚本以**静态 `.can` 文件**形式存放在项目根目录的 `capl/` 文件夹下。  
本目录 (`src/ivi_bus_capl/capl_templates/`) 是为**下一阶段**预留的扩展点。

### 为什么需要模板？

在实际的车载测试项目中，不同车型、不同 ECU 往往只有少量参数差异（如 CAN ID、周期、DID 值），
而 CAPL 脚本的逻辑骨架是完全相同的。此时如果为每个变体手动维护一份完整的 `.can` 文件，
会导致大量重复代码，维护成本急剧上升。

### 模板化的好处

| 方面 | 静态脚本 | 模板化生成 |
|------|----------|------------|
| 维护性 | 每改一个参数要改 N 份文件 | 只需修改模板 + 参数配置文件 |
| 可追溯 | 难以追踪参数变更历史 | 参数变化由 Git 记录，一目了然 |
| 可扩展 | 新增车型需复制粘贴 | 新增配置行即可自动生成 |
| 与 CI 集成 | 需要手动同步 | 构建时自动生成，减少人为失误 |

---

## 当前状态

✅ **已完成**：8 个参考 CAPL 脚本（位于 `capl/` 目录）  
🔜 **规划中**：基于 Jinja2 的模板引擎，支持以下变量的参数化渲染

| 变量名 | 类型 | 说明 | 示例 |
|--------|------|------|------|
| `can_id` | hex | 目标消息 ID | `0x123` |
| `interval_ms` | int | 周期检查容忍度 | `100` |
| `signal_name` | string | 待验证的信号名 | `ScreenState` |
| `min_val` | int | 信号最小值 | `0` |
| `max_val` | int | 信号最大值 | `3` |
| `did` | hex | UDS DID 标识符 | `0xF190` |
| `expected_data` | hex | UDS 期望响应数据 | `01 02 03 04` |

---

## 目录结构（规划中）
capl_templates/

├── init.py          # 模板引擎入口

├── README.md            # 本文档

├── base/                # 基础模板片段

│   ├── timer_setup.j2   # 定时器初始化

│   ├── uds_common.j2    # UDS 通用处理函数

│   └── dtc_common.j2    # DTC 通用处理函数

├── scenarios/           # 场景完整模板

│   ├── periodic_check.j2

│   ├── signal_range.j2

│   ├── uds_22_read_did.j2

│   ├── uds_2e_write_did.j2

│   ├── dtc_inject_clear.j2

│   └── error_frame_check.j2

└── configs/             # 车型参数配置

├── model_a.yaml     # A 车型参数

└── model_b.yaml     # B 车型参数
## 如何使用（未来版本）
python
from ivi_bus_capl.capl_templates import CaplTemplateEngine
## 初始化引擎
engine = CaplTemplateEngine(template_dir="capl_templates/scenarios")

## 渲染单个脚本
script = engine.render(
template_name="uds_22_read_did",
can_id="0x123",
did="0xF190",
expected_data="01 02 03 04"
)

## 批量生成（基于 YAML 配置）
engine.batch_generate(config_path="configs/model_a.yaml", output_dir="generated/")

## （未来版本）写入文件
with open("generated/read_vin.can", "w") as f:
f.write(script)
## 贡献指南
##如果你想为本目录贡献新的模板：
1. 在 `scenarios/` 下创建 `.j2` 文件，遵循现有命名规范
2. 使用 `{{ variable }}` 标记可变部分，`{% if %}` 控制可选逻辑
3. 在 `configs/` 下添加对应的参数配置文件（YAML 格式）
4. 更新本 README 的变量表和目录结构图
5. 确保生成的 `.can` 文件能通过 CANoe 编译

---
## 相关资源
- [Jinja2 模板引擎文档](https://jinja.palletsprojects.com/)
- [CAPL 编程语言参考](https://assets.vector.com/cao_downloadcenter/CAPL_Documentation.pdf)
- 项目根目录 `capl/` 下的 8 个参考脚本（静态版本）