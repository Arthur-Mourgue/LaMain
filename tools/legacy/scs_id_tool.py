#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Scan and change Feetech SCS0009 servo IDs (replaces the FD software on Linux).

Install:      pip install feetech-servo-sdk
Scan:         python3 scs_id_tool.py --port /dev/ttyACM0 --scan
Change an ID: python3 scs_id_tool.py --port /dev/ttyACM0 --set 1 2
              (ONLY one servo on the bus while changing an ID!)
"""
import argparse
import sys

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

BAUDRATE = 1_000_000
PROTOCOL_END = 1      # SCS series (SCS0009) = 1, STS series = 0
ADDR_ID = 5           # ID register (EEPROM)
ADDR_LOCK = 48        # SCS-series EEPROM lock (0 = unlocked, 1 = locked)


def open_bus(port_name):
    port = PortHandler(port_name)
    if not port.openPort():
        sys.exit(f"Cannot open {port_name} (permissions? wrong port?)")
    if not port.setBaudRate(BAUDRATE):
        sys.exit("Cannot set the baudrate")
    return port, PacketHandler(PROTOCOL_END)


def scan(port, ph, max_id=20):
    found = []
    for sid in range(0, max_id + 1):
        model, res, err = ph.ping(port, sid)
        if res == COMM_SUCCESS:
            print(f"  Servo found: ID {sid} (model {model})")
            found.append(sid)
    if not found:
        print("  No servo found. Check the 5 V power, the USB jumper and the cable.")
    return found


def write1(port, ph, sid, addr, val, what):
    res, err = ph.write1ByteTxRx(port, sid, addr, val)
    if res != COMM_SUCCESS:
        sys.exit(f"Failed ({what}): {ph.getTxRxResult(res)}")


def set_id(port, ph, old_id, new_id):
    if old_id not in scan(port, ph):
        sys.exit(f"No servo with ID {old_id} on the bus.")
    write1(port, ph, old_id, ADDR_LOCK, 0, "EEPROM unlock")
    write1(port, ph, old_id, ADDR_ID, new_id, "ID write")
    write1(port, ph, new_id, ADDR_LOCK, 1, "EEPROM lock")
    print(f"ID {old_id} -> {new_id} OK. Verification:")
    scan(port, ph)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--set", nargs=2, type=int, metavar=("OLD", "NEW"))
    args = ap.parse_args()

    port, ph = open_bus(args.port)
    try:
        if args.set:
            set_id(port, ph, *args.set)
        else:
            scan(port, ph)
    finally:
        port.closePort()
