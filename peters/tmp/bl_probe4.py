import time

import chipwhisperer as cw

LOG = open(r"C:\Python3.12venv\chipwhisperer\chipwhisperer-jupyter\peters\bl_probe4.log", "w", buffering=1, encoding="utf-8")


def log(*a):
    print(*a, file=LOG, flush=True)


scope = cw.scope()
scope.default_setup()
target = cw.target(scope, cw.targets.SimpleSerial)
scope.io.tio1 = "serial_tx"
scope.io.tio2 = "serial_rx"
ser = target.ser


def rx(n, timeout=300):
    return ser.read(n, timeout=timeout).encode("latin-1")


def tx(data, gap):
    for b in data:
        ser.write(bytes([b]))
        if gap:
            time.sleep(gap)


for baud in (115200, 57600, 38400, 19200, 9600):
    ser.setBaud(baud)
    ser.setParity("even")
    for gap in (0, 0.01):
        rows = []
        for i in range(3):
            scope.io.pdic = "high"; time.sleep(0.05)
            scope.io.nrst = "low"; time.sleep(0.2); scope.io.nrst = "high_z"; time.sleep(0.5)
            ser.flush()
            tx(b"\x7f", gap)
            h = rx(1)
            ser.flush()
            tx(b"\x02\xfd", gap)
            gid = rx(5, timeout=200)
            ser.flush()
            tx(b"\x11\xee", gap)
            r = rx(1)
            rows.append((h.hex() or "-", gid.hex() or "-", r.hex() or "-"))
        log("RES baud", baud, "gap", gap, "(handshake, GetID reply, ReadMem ack):", rows)
scope.io.pdic = "low"
log("RES done")
