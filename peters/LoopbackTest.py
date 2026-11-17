import chipwhisperer as cw, time

scope = cw.scope()
scope.default_setup()
target = cw.target(scope, cw.targets.SimpleSerial)

scope.io.tio1 = "serial_tx"
scope.io.tio2 = "serial_rx"
target.ser.cwlite_usart.init(baud=115200, stopbits=1, parity="even")

u = target.ser.cwlite_usart
for p in ("even", "none", "odd"):
    u.init(baud=115200, stopbits=1, parity=p)
    u.flush()
    u.write(b"\x79")
    time.sleep(0.1)
    print(p, bytes(u.read(1, timeout=500)).hex())


    