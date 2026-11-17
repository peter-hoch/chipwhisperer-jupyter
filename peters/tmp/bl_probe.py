import time, serial, chipwhisperer as cw
scope = cw.scope(); scope.default_setup()
scope.io.tio1 = "serial_tx"; scope.io.tio2 = "serial_rx"
ser = serial.Serial(scope.get_serial_ports()[0]["port"], 115200, parity=serial.PARITY_EVEN, stopbits=1, bytesize=8, timeout=1)
scope.io.pdic = "high"; time.sleep(0.05)
scope.io.nrst = "low"; time.sleep(0.2); scope.io.nrst = "high_z"; time.sleep(0.5)
ser.reset_input_buffer(); ser.write(b"\x7f"); print("RES handshake", ser.read(1).hex() or "(none)")


def cmd(c):
    ser.reset_input_buffer(); ser.write(bytes([c, c ^ 0xFF])); return ser.read(1)


r = cmd(0x00); print("RES Get ack", r.hex())
if r == b"\x79":
    n = ser.read(1)[0]; data = ser.read(n + 1); ser.read(1)
    print("RES bootloader version", hex(data[0]), "commands", data[1:].hex())
r = cmd(0x01); print("RES GetVersion ack", r.hex())
if r == b"\x79":
    print("RES version/RDP bytes", ser.read(3).hex(), ser.read(1).hex())
r = cmd(0x02); print("RES GetID ack", r.hex())
if r == b"\x79":
    n = ser.read(1)[0]; print("RES PID", ser.read(n + 1).hex(), ser.read(1).hex())
for addr in (0x08000000, 0x1FFF0000, 0x20000000):
    r = cmd(0x11); print("RES ReadMem cmd ack", r.hex())
    if r != b"\x79": break
    a = addr.to_bytes(4, "big"); ser.write(a + bytes([a[0] ^ a[1] ^ a[2] ^ a[3]]))
    r = ser.read(1); print("RES  addr", hex(addr), "ack", r.hex())
    if r != b"\x79": continue
    ser.write(bytes([15, 15 ^ 0xFF])); r = ser.read(1); print("RES  len ack", r.hex())
    print("RES  data", ser.read(16).hex())
    break
scope.io.pdic = "low"
