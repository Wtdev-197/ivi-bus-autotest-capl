"""
test_dtc.py — DTC 注入与清除测试

测试目标：
    验证 DTC（Diagnostic Trouble Code）的注入、读取和清除流程。
    
测试方法：
    1. 通过信号越限触发 DTC
    2. 19 02 服务读取已存储的 DTC
    3. 14 服务清除 DTC
    4. 再次读取确认清除
"""

import time
import pytest
from ivi_bus_capl.virtual_bus import VirtualBus


DIAG_REQ_ID = 0x7E0
DIAG_RESP_ID = 0x7E8


def test_dtc_set_and_read(bus: VirtualBus):
    """
    测试 DTC 置位与读取。
    
    步骤：
        1. 发送越限信号（OverspeedWarning=1，车速 > 120）
        2. 19 02 读取 DTC
        3. 验证 DTC 已置位
    """
    # 步骤 1: 触发 DTC — 发送超速警告
    bus.send("IVI_Status", {
        "ScreenState": 1,
        "AudioVolume": 30,
        "OverspeedWarning": 1  # 超速标志
    })
    bus.send("VehicleSpeed", {"Speed": 130.0})  # 130 km/h
    
    time.sleep(0.1)  # 等待 ECU 处理
    
    # 步骤 2: 19 02 — 读取已存储的 DTC
    dtc_req = bytes([0x19, 0x02])
    bus.send_raw(DIAG_REQ_ID, dtc_req)
    
    resp = bus.recv(timeout=0.5)
    assert resp is not None, "未收到 DTC 读取响应"
    
    resp_data = resp.raw_msg.data
    assert resp_data[0] == 0x59, f"响应 SID 错误: 期望 0x59, 实际 0x{resp_data[0]:02X}"
    
    # 检查 DTC 数量（简化：至少有一个 DTC）
    dtc_count = resp_data[1]
    assert dtc_count > 0, "未检测到 DTC"
    print(f"检测到 {dtc_count} 个 DTC")


def test_dtc_clear_and_verify(bus: VirtualBus):
    """
    测试 DTC 清除与验证。
    
    步骤：
        1. 14 FF FF FF 清除所有 DTC
        2. 19 02 再次读取
        3. 验证 DTC 已被清除
    """
    # 步骤 1: 清除 DTC
    clear_req = bytes([0x14, 0xFF, 0xFF, 0xFF])
    bus.send_raw(DIAG_REQ_ID, clear_req)
    
    clear_resp = bus.recv(timeout=0.5)
    assert clear_resp is not None, "未收到清除响应"
    assert clear_resp.raw_msg.data[0] == 0x54, \
        f"清除响应 SID 错误: 期望 0x54, 实际 0x{clear_resp.raw_msg.data[0]:02X}"
    
    # 步骤 2: 重新读取 DTC
    read_req = bytes([0x19, 0x02])
    bus.send_raw(DIAG_REQ_ID, read_req)
    
    verify_resp = bus.recv(timeout=0.5)
    assert verify_resp is not None, "未收到验证响应"
    
    dtc_count = verify_resp.raw_msg.data[1]
    assert dtc_count == 0, f"DTC 未完全清除: 仍有 {dtc_count} 个"


def test_dtc_full_lifecycle(bus: VirtualBus):
    """
    DTC 全生命周期测试：触发 → 读取 → 清除 → 验证。
    """
    # 触发 DTC
    bus.send("IVI_Status", {
        "ScreenState": 2,
        "AudioVolume": 70,
        "OverspeedWarning": 1
    })
    bus.send("VehicleSpeed", {"Speed": 180.0})
    time.sleep(0.1)
    
    # 读取 → 应有 DTC
    bus.send_raw(DIAG_REQ_ID, bytes([0x19, 0x02]))
    resp1 = bus.recv(timeout=0.5)
    assert resp1 is not None
    assert resp1.raw_msg.data[1] > 0, "DTC 未被触发"
    
    # 清除
    bus.send_raw(DIAG_REQ_ID, bytes([0x14, 0xFF, 0xFF, 0xFF]))
    resp2 = bus.recv(timeout=0.5)
    assert resp2 is not None
    assert resp2.raw_msg.data[0] == 0x54
    
    # 验证清除
    bus.send_raw(DIAG_REQ_ID, bytes([0x19, 0x02]))
    resp3 = bus.recv(timeout=0.5)
    assert resp3 is not None
    assert resp3.raw_msg.data[1] == 0, "DTC 清除失败"