import sys, time, serial, chipwhisperer as cw

LOG = open(r"C:\Python3.12venv\chipwhisperer\chipwhisperer-jupyter\peters\bl_probe3.log", "w", buffering=1, encoding="utf-8")


def log(*a):
    print(*a, file=LOG, flush=True)


scope = cw.scope()
scope.io.tio1 = "serial_tx"; scope.io.tio2 = "serial_rx"
port = scope.get_serial_ports()[0]["port"]


def to_bootloader(ser):
    scope.io.pdic = "high"; time.sleep(0.05)
    scope.io.nrst = "low"; time.sleep(0.2); scope.io.nrst = "high_z"; time.sleep(0.5)
    ser.reset_input_buffer(); ser.write(b"\x7f")
    return ser.read(1)


def send_cmd(ser, code, gap):
    ser.reset_input_buffer()
    if gap:
        ser.write(bytes([code])); time.sleep(gap); ser.write(bytes([code ^ 0xFF]))
    else:
        ser.write(bytes([code, code ^ 0xFF]))
    return ser.read(1)


for baud, gap in ((115200, 0), (115200, 0.01), (57600, 0), (9600, 0)):
    ser = serial.Serial(port, baud, parity=serial.PARITY_EVEN, stopbits=1, bytesize=8, timeout=0.5)
    res = []
    for i in range(5):
        h = to_bootloader(ser)
        g = send_cmd(ser, 0x02, gap)
        if g == b"\x79":
            n = ser.read(1); ser.read(2); ser.read(1)
        r = send_cmd(ser, 0x11, gap)
        res.append((h.hex() or "-", g.hex() or "-", r.hex() or "-"))
    log("RES baud", baud, "gap", gap, "(handshake, GetID ack, ReadMem ack):", res)
    ser.close()

scope.io.pdic = "low"
log("RES done")
