"""Dump the STM32L452 flash through the system bootloader (USART, 8E1)
using the ChipWhisperer target serial (target.ser), no pyserial.

Wiring: Husky TIO1 (pin 10) / TIO2 (pin 12) to the Nucleo's PA9/PA10 so that
PA9 (Nucleo TX) lands on the pin set to serial_rx. PDIC (pin 13) -> BOOT0,
nRST (pin 5) -> NRST, common GND.

Usage: python dump_flash_target.py [output.bin] [size_bytes]
"""
import sys
import time

import chipwhisperer as cw

FLASH_BASE = 0x08000000
FLASH_SIZE = 512 * 1024      # STM32L452RE: 512 KB
CHUNK = 64                   # SAM3U RX buffer holds only 128-200 bytes
BAUD = 115200
BYTE_GAP = 0.01              # back-to-back bytes get NACKed by the bootloader
RETRIES = 3

out_path = sys.argv[1] if len(sys.argv) > 1 else "flash_dump.bin"
size = int(sys.argv[2], 0) if len(sys.argv) > 2 else FLASH_SIZE

scope = cw.scope()
scope.default_setup()
target = cw.target(scope, cw.targets.SimpleSerial)
scope.io.tio1 = "serial_tx"
scope.io.tio2 = "serial_rx"

ser = target.ser
ser.setBaud(BAUD)
ser.setParity("even")


def rx(n, timeout=300):
    """Read up to n bytes; returns fewer on timeout."""
    return ser.read(n, timeout=timeout).encode("latin-1")


def tx(data):
    for b in data:
        ser.write(bytes([b]))
        if BYTE_GAP:
            time.sleep(BYTE_GAP)


def enter_bootloader():
    """BOOT0 high, reset, then send 0x7F for auto-baud."""
    for _ in range(RETRIES):
        scope.io.pdic = "high"
        time.sleep(0.05)
        scope.io.nrst = "low"
        time.sleep(0.2)
        scope.io.nrst = "high_z"
        time.sleep(0.5)
        ser.flush()
        tx(b"\x7f")
        reply = rx(1)
        if reply == b"\x79":
            return
        print(f"  handshake reply: {reply.hex() or '(none)'}")
    raise RuntimeError("no ACK to 0x7F handshake")


def cmd(code):
    ser.flush()                       # resync: drop leftovers
    tx(bytes([code, code ^ 0xFF]))
    return rx(1)


def read_mem(addr, length):
    """Read Memory command (0x11), length 1..256."""
    if cmd(0x11) != b"\x79":
        raise RuntimeError("Read Memory NACK")
    a = addr.to_bytes(4, "big")
    tx(a + bytes([a[0] ^ a[1] ^ a[2] ^ a[3]]))
    if rx(1) != b"\x79":
        raise RuntimeError(f"address NACK at 0x{addr:08X}")
    tx(bytes([length - 1, (length - 1) ^ 0xFF]))
    if rx(1) != b"\x79":
        raise RuntimeError("length NACK")
    data = rx(length, timeout=1000)
    if len(data) != length:
        raise RuntimeError(f"short read at 0x{addr:08X}: {len(data)}/{length}")
    return data


def read_chunk_with_retry(addr, length):
    for attempt in range(RETRIES):
        try:
            return read_mem(addr, length)
        except RuntimeError as e:
            print(f"\n  retry {attempt + 1}/{RETRIES}: {e}")
            enter_bootloader()        # clean state, then try again
    raise RuntimeError(f"giving up at 0x{addr:08X}")


enter_bootloader()

# Get ID as a sanity check (expect 0462 for the L45x family)
if cmd(0x02) == b"\x79":
    n = rx(1)[0]
    pid = rx(n + 1)
    rx(1)
    print("product ID:", pid.hex())

t0 = time.time()
with open(out_path, "wb") as f:
    for off in range(0, size, CHUNK):
        data = read_chunk_with_retry(FLASH_BASE + off, min(CHUNK, size - off))
        f.write(data)
        if (off // CHUNK) % 64 == 0:
            print(f"\r{100 * off / size:5.1f}%  0x{FLASH_BASE + off:08X}", end="", flush=True)

print(f"\ndone: {size} bytes -> {out_path} in {time.time() - t0:.0f}s")

# Boot normally again next time
scope.io.pdic = "low"
