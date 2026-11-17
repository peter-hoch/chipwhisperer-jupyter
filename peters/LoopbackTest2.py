import chipwhisperer as cw, time

scope = cw.scope()
scope.default_setup()
target = cw.target(scope, cw.targets.SimpleSerial)

u = target.ser.cwlite_usart
u.init(baud=9600, stopbits=1, parity="none")
for b in (b"\x00", b"\xff", b"\x55", b"\x79"):
    u.flush(); u.write(b); time.sleep(0.1)
    print(b.hex(), bytes(u.read(1, timeout=500)).hex())

    