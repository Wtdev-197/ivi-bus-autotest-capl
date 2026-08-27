# ivi-bus-autotest-capl
> 智能座舱总线自动化测试工具包 — 将 CANoe/CAPL 能力桥接进 pytest CI 体系。
![CI](https://github.com/Wtdev-197/ivi-bus-autotest-capl/actions/workflows/ci.yml/badge.svg)
![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11-blue)
![License](https://img.shields.io/badge/license-MIT-green)
---
## 概述
本项目不是一份 CAPL 教程，而是一套**可落地、可集成、可仿真**的智能座舱总线测试解决方案。它与以下两个仓库组成完整的测试栈：

| 层级 | 仓库 | 职责 |
|------|------|------|
| 🖥️ 应用层 | [ai-cockpit-test-framework](https://github.com/Wtdev-197/ai-cockpit-test-framework) | pytest 工程化框架 + GitHub Actions CI |
| 📊 平台层 | [AI-intelligent-testing-platform](https://github.com/Wtdev-197/AI-intelligent-testing-platform) | Node.js 测试管理平台 |
| 🔌 总线层 | **ivi-bus-autotest-capl** ← 你在这里 | CAN/CAPL/UDS 信号级验证 |

**一句话定位**：补齐智能座舱测试栈的信号层拼图，让应用层用例能够向下穿透到总线信号。
---
## 特性
- ✅ **双模运行**：支持 `virtual`（无硬件）和 `canoe`（硬件在环）两种后端，通过环境变量一键切换
- ✅ **Python-CANoe 桥接**：通过 Vector COM 接口将 pytest 与 CANoe 运行时打通，实现全链路闭环
- ✅ **CAPL 脚本库**：8 个覆盖核心场景的参考脚本，每个均附 DBC 上下文说明与预期断言
- ✅ **降级仿真**：无 CANoe 授权时，基于 `python-can` + `socketcan` 实现等效逻辑验证
- ✅ **CI 就绪**：GitHub Actions 自动运行 virtual 后端测试，生成 Allure 报告
- ✅ **可复现构建**：pyproject.toml + 锁定依赖，确保环境一致性

---
## 快速开始
### 前置条件
- Python 3.10+
- （可选）Linux SocketCAN 内核模块：`sudo modprobe vcan`
- （可选）Windows + CANoe 11.0+ + Vector 硬件授权

### 安装
bash
1.克隆仓库
git clone https://github.com/Wtdev-197/ivi-bus-autotest-capl.git
cd ivi-bus-autotest-capl
2.创建虚拟环境
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate # Windows
3.安装依赖
pip install -r requirements.txt
pip install -e .

### 运行测试
bash
1.使用 virtual 后端（默认，无需硬件）
pytest tests/ -v --tb=short
2.指定后端
BUS_BACKEND=socketcan pytest tests/ -v --tb=short
3.推荐运行方式
 a.Windows、本地开发及 GitHub Actions：
   pytest tests/ -v --tb=short --bus-backend=virtual
 b.Linux + SocketCAN：
   sudo modprobe vcan
   sudo ip link add dev vcan0 type vcan
   sudo ip link set up vcan0
   pytest tests/ -v --tb=short --bus-backend=socketcan
4.生成 Allure 报告
pytest tests/ --alluredir=results
allure serve results

### 预期输出
tests/test_periodic_msg.py::test_ivi_status_period_within_tolerance ✓
tests/test_periodic_msg.py::test_ivi_status_signals_valid_range ✓
tests/test_uds_22_2e.py::test_uds_22_read_vin ✓
tests/test_uds_22_2e.py::test_uds_2e_write_and_verify ✓
tests/test_uds_22_2e.py::test_uds_negative_response_invalid_did ✓
tests/test_dtc.py::test_dtc_set_and_read ✓
tests/test_dtc.py::test_dtc_clear_and_verify ✓
tests/test_dtc.py::test_dtc_full_lifecycle ✓
---
## 架构
┌─────────────────────────────────────────────────────────┐

│                    pytest 测试用例                        │

│  (test_periodic_msg / test_uds_22_2e / test_dtc)        │

└──────────────────────┬──────────────────────────────────┘

│

▼

┌─────────────────────────────────────────────────────────┐

│               Bus 抽象层 (conftest.py)                    │

│                                                          │

│    BUS_BACKEND=virtual     │    BUS_BACKEND=canoe        │

│    ┌──────────────────┐    │    ┌──────────────────┐     │

│    │  VirtualBus      │    │    │  CanoeBridge     │     │

│    │  (python-can)    │◄───┼───►│  (COM 接口)      │     │

│    │  vcan / virtual  │    │    │  CANoe 运行时    │     │

│    └────────┬─────────┘    │    └────────┬─────────┘     │

└─────────────┼──────────────┴──────────────┼──────────────┘

│                             │

▼                             ▼

┌──────────────────────┐    ┌──────────────────────────────┐

│  DBC 编解码           │    │  CAPL 脚本 (.can)            │

│  (cantools)           │    │  · 周期监控                  │

│  · encode_message()   │    │  · 信号范围验证              │

│  · decode_message()   │    │  · UDS 22/2E               │

└──────────────────────┘    │  · DTC 注入/清除             │

│  · 多节点仿真                │

└──────────────────────────────┘
---

## 项目结构
ivi-bus-autotest-capl/

├── src/ivi_bus_capl/           # 核心源码

│   ├── init.py             # 包入口

│   ├── virtual_bus.py          # 虚拟总线引擎

│   ├── canoe_bridge.py         # CANoe COM 桥接

│   ├── dbc_loader.py           # DBC 加载器

│   └── capl_templates/         # CAPL 模板（预留）

├── tests/                      # pytest 测试套件

│   ├── conftest.py             # 共享夹具与配置

│   ├── test_periodic_msg.py    # 周期监控测试

│   ├── test_uds_22_2e.py      # UDS 诊断测试

│   └── test_dtc.py             # DTC 生命周期测试

├── capl/                       # CAPL 参考脚本

│   ├── 01_periodic_check.can   # 周期监控

│   ├── 02_signal_range.can     # 信号范围

│   ├── 03_uds_session.can      # 会话控制

│   ├── 04_uds_22_read_did.can  # 22 服务

│   ├── 05_uds_2e_write_did.can # 2E 服务

│   ├── 06_dtc_inject_clear.can # DTC 注入/清除

│   ├── 07_multinode_sim.can    # 多节点仿真

│   └── 08_error_frame_check.can# 错误帧监控

├── fixtures/

│   └── vehicle_ivi.dbc         # 样例 DBC 文件

├── .github/workflows/

│   └── ci.yml                  # GitHub Actions CI

├── pyproject.toml              # 项目元数据

├── requirements.txt            # 依赖锁定

└── README.md                   # 本文档
---

## CAPL 脚本索引

| 编号 | 文件名 | 场景 | 对应 pytest |
|------|--------|------|-------------|
| 01 | `01_periodic_check.can` | IVI_Status 周期 100±10ms 监控 | `test_periodic_msg.py` |
| 02 | `02_signal_range.can` | ScreenState/AudioVolume 范围验证 | `test_periodic_msg.py` |
| 03 | `03_uds_session.can` | 10/3E 会话控制 | — |
| 04 | `04_uds_22_read_did.can` | 22 读取 VIN/硬件版本 | `test_uds_22_2e.py` |
| 05 | `05_uds_2e_write_did.can` | 2E 写入 DID 并回读 | `test_uds_22_2e.py` |
| 06 | `06_dtc_inject_clear.can` | DTC 注入/读取/清除 | `test_dtc.py` |
| 07 | `07_multinode_sim.can` | IVI_ECU + BodyCtrl 双节点仿真 | — |
| 08 | `08_error_frame_check.can` | 错误帧检测与阈值告警 | — |

---

## 如何贡献
1. Fork 本仓库
2. 创建特性分支：`git checkout -b feat/my-feature`
3. 提交变更：`git commit -m "feat(xxx): add my feature"`
4. 推送分支：`git push origin feat/my-feature`
5. 发起 Pull Request

### 开发指南
- 所有代码需通过 `pytest tests/ -v --bus-backend=virtual` 测试
- CAPL 脚本需附带 DBC 上下文说明和预期断言注释
- 新增依赖请同步更新 `pyproject.toml` 和 `requirements.txt`

---
## 许可证
[MIT License](LICENSE)

---
## 作者

&zwnj;**zhangwentao**&zwnj;

- 📧 邮箱: [2669279956@qq.com](mailto:2669279956@qq.com)
- 🌐 GitHub: https://github.com/Wtdev-197
---

## 致谢
- [python-can](https://github.com/hardbyte/python-can) — Python CAN 总线接口
- [cantools](https://github.com/eerimoq/cantools) — DBC 解析与编码
- [udsoncan](https://github.com/jacobschaer/udsoncan) — UDS 诊断协议栈
- [Vector CANoe](https://www.vector.com/int/en/products/products-a-z/software/canoe/) — 专业总线分析工具