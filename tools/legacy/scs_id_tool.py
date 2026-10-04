#!/usr/bin/env python3
"""Scanner et changer l'ID de servos Feetech SCS0009 (remplace le logiciel FD sous Linux).

Installation :  pip install feetech-servo-sdk
Scanner :       python3 scs_id_tool.py --port /dev/ttyACM0 --scan
Changer l'ID :  python3 scs_id_tool.py --port /dev/ttyACM0 --set 1 2
                (UN SEUL servo branché sur le bus quand tu changes un ID !)
"""
import argparse
import sys

from scservo_sdk import PortHandler, PacketHandler, COMM_SUCCESS

BAUDRATE = 1_000_000
PROTOCOL_END = 1      # série SCS (SCS0009) = 1, série STS = 0
ADDR_ID = 5           # registre ID (EEPROM)
ADDR_LOCK = 48        # verrou EEPROM de la série SCS (0 = déverrouillé, 1 = verrouillé)


def open_bus(port_name):
    port = PortHandler(port_name)
    if not port.openPort():
        sys.exit(f"Impossible d'ouvrir {port_name} (droits ? bon port ?)")
    if not port.setBaudRate(BAUDRATE):
        sys.exit("Impossible de régler le baudrate")
    return port, PacketHandler(PROTOCOL_END)


def scan(port, ph, max_id=20):
    found = []
    for sid in range(0, max_id + 1):
        model, res, err = ph.ping(port, sid)
        if res == COMM_SUCCESS:
            print(f"  Servo trouvé : ID {sid} (modèle {model})")
            found.append(sid)
    if not found:
        print("  Aucun servo trouvé. Vérifie l'alim 5 V, le cavalier USB et le câble.")
    return found


def write1(port, ph, sid, addr, val, what):
    res, err = ph.write1ByteTxRx(port, sid, addr, val)
    if res != COMM_SUCCESS:
        sys.exit(f"Échec ({what}) : {ph.getTxRxResult(res)}")


def set_id(port, ph, old_id, new_id):
    if old_id not in scan(port, ph):
        sys.exit(f"Aucun servo avec l'ID {old_id} sur le bus.")
    write1(port, ph, old_id, ADDR_LOCK, 0, "déverrouillage EEPROM")
    write1(port, ph, old_id, ADDR_ID, new_id, "écriture ID")
    write1(port, ph, new_id, ADDR_LOCK, 1, "reverrouillage EEPROM")
    print(f"ID {old_id} -> {new_id} OK. Vérification :")
    scan(port, ph)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", default="/dev/ttyACM0")
    ap.add_argument("--scan", action="store_true")
    ap.add_argument("--set", nargs=2, type=int, metavar=("ANCIEN", "NOUVEAU"))
    args = ap.parse_args()

    port, ph = open_bus(args.port)
    try:
        if args.set:
            set_id(port, ph, *args.set)
        else:
            scan(port, ph)
    finally:
        port.closePort()
