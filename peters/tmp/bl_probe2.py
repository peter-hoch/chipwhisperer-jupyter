import sys, time, serial, chipwhisperer as cw
sys.stdout = open(r"C:\Python3.12venv\chipwhisperer\chipwhisperer-jupyter\peters\bl_probe2.log", "w", buffering=1, encoding="utf-8")
sys.stderr = sys.stdout
scope = cw.scope(); scope.default_setup()
target = cw.target(scope, cw.targets.SimpleSerial)
scope.io.tio1 = "serial_tx"; scope.io.tio2 = "serial_rx"
u = target.ser.cwlite_usart


def reset_to_bootloader():
    scope.io.pdic = "high"; time.sleep(0.05)
    scope.io.nrst = "low"; time.sleep(0.2); scope.io.nrst = "high_z"; time.sleep(0.5)


def run(name, write, read, flush):
    res = []
    for i in range(4):
        reset_to_bootloader()
        flush(); write(b"\x7f"); h = read(1)
        flush_after = read(0)
        write(b"\x00\xff"); g = read(14)
        res.append((h.hex(), g.hex()))
    print("RES", name)
    for h, g in res:
        print("RES    handshake", h or "-", "| Get reply", g or "-")


# CDC port, 8E1 and 8N1
ser = serial.Serial(scope.get_serial_ports()[0]["port"], 115200, parity=serial.PARITY_EVEN, stopbits=1, bytesize=8, timeout=0.5)
run("CDC 8E1", ser.write, lambda n: ser.read(n) if n else ser.read(ser.in_waiting), ser.reset_input_buffer)
ser.parity = serial.PARITY_NONE
run("CDC 8N1", ser.write, lambda n: ser.read(n) if n else ser.read(ser.in_waiting), ser.reset_input_buffer)
ser.close()


# ChipWhisperer USART driver, even parity
def u_read(n):
    time.sleep(0.3)
    w = u.inWaiting()
    if n and n < w:
        w = n
    return bytes(u.read(w, timeout=100)) if w else b""


u.init(baud=115200, stopbits=1, parity="even")
run("cwlite_usart even", u.write, u_read, u.flush)
scope.io.pdic = "low"
