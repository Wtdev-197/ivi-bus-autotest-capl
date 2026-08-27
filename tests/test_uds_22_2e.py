"""
test_uds_22_2e.py — UDS 22/2E 服务测试

测试目标：
    验证 UDS 22 服务（ReadDataByIdentifier）和 2E 服务（WriteDataByIdentifier）
    的正确响应。
    
测试方法：
    1. 通过虚拟总线发送 UDS 诊断请求
    2. 模拟 ECU 响应（virtual_bus 内置的虚拟 ECU 逻辑）
    3. 断言响应中的 DID 和数据正确性
"""

import time
import pytest
from ivi_bus_capl.virtual_bus import VirtualBus


# UDS 诊断地址
DIAG_REQ_ID = 0x7E0
DIAG_RESP_ID = 0x7E8

# 常用 DID
DID_VIN = 0xF190        # VIN 码
DID_HARDWARE_VERSION = 0xF1A0  # 硬件版本


def test_uds_22_read_vin(bus: VirtualBus):
    """
    测试 22 服务：读取 VIN 码 (DID 0xF190)。
    
    期望响应：62 F1 90 + VIN 数据（17 字节 ASCII）
    """
    # 构造 22 请求：22 F1 90
    req_data = bytes([0x22, 0xF1, 0x90])
    
    # 发送诊断请求
    bus.send_raw(DIAG_REQ_ID, req_data)
    
    # 等待响应
    resp = bus.recv(timeout=0.5)
    assert resp is not None, "未收到诊断响应"
    
    # 检查响应 ID
    assert resp.raw_msg.arbitration_id == DIAG_RESP_ID, \
        f"响应 ID 错误: 期望 0x{DIAG_RESP_ID:X}, 实际 0x{resp.raw_msg.arbitration_id:X}"
    
    # 解析响应：62 + DID(2字节) + 数据
    resp_data = resp.raw_msg.data
    assert resp_data[0] == 0x62, f"响应 SID 错误: 期望 0x62, 实际 0x{resp_data[0]:02X}"
    assert resp_data[1:3] == bytes([0xF1, 0x90]), "DID 回显错误"
    
    vin_bytes = resp_data[3:]
    vin_str = vin_bytes.decode("ascii", errors="replace").strip('\x00')
    print(f"VIN: {vin_str}")
    
    assert len(vin_str) > 0, "VIN 为空"
    assert len(vin_str) <= 17, f"VIN 长度超过 17: {len(vin_str)}"


def test_uds_2e_write_and_verify(bus: VirtualBus):
    """
    测试 2E 服务：写入 DID 并回读验证。
    
    步骤：
        1. 2E 写入 DID 0xF1A0（硬件版本）
        2. 22 回读该 DID
        3. 验证写入值与回读值一致
    """
    TEST_VALUE = "v2.1.0"
    
    # 步骤 1: 2E 写入
    write_req = bytes([0x2E, 0xF1, 0xA0]) + TEST_VALUE.encode("ascii")
    bus.send_raw(DIAG_REQ_ID, write_req)
    
    write_resp = bus.recv(timeout=0.5)
    assert write_resp is not None, "未收到 2E 响应"
    assert write_resp.raw_msg.data[0] == 0x6E, \
        f"2E 响应 SID 错误: 期望 0x6E, 实际 0x{write_resp.raw_msg.data[0]:02X}"
    
    # 步骤 2: 22 回读
    read_req = bytes([0x22, 0xF1, 0xA0])
    bus.send_raw(DIAG_REQ_ID, read_req)
    
    read_resp = bus.recv(timeout=0.5)
    assert read_resp is not None, "未收到 22 响应"
    
    read_value = read_resp.raw_msg.data[3:].decode("ascii", errors="replace").strip('\x00')
    assert read_value == TEST_VALUE, \
        f"回读值不匹配: 期望 '{TEST_VALUE}', 实际 '{read_value}'"


def test_uds_negative_response_invalid_did(bus: VirtualBus):
    """
    测试 22 服务对无效 DID 的负响应。
    
    期望：7F 22 12（SubFunctionNotSupported）
    """
    INVALID_DID = 0xFFFF
    
    req = bytes([0x22, 0xFF, 0xFF])
    bus.send_raw(DIAG_REQ_ID, req)
    
    resp = bus.recv(timeout=0.5)
    assert resp is not None, "未收到负响应"
    
    resp_data = resp.raw_msg.data
    assert resp_data[0] == 0x7F, f"期望负响应 0x7F, 实际 0x{resp_data[0]:02X}"
    assert resp_data[1] == 0x22, "NRC 中 SID 回显错误"
    assert resp_data[2] == 0x12, \
        f"期望 NRC 0x12 (SubFunctionNotSupported), 实际 0x{resp_data[2]:02X}"