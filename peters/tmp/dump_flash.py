"""Dump the STM32L452 flash through the system bootloader (USART, 8E1)
using a ChipWhisperer Husky.

Wiring: Husky TIO1 (pin 10) / TIO2 (pin 12) to the Nucleo's PA9/PA10 so that
PA9 (Nucleo TX) lands on the pin set to serial_rx. PDIC (pin 13) -> BOOT0,
nRST (pin 5) -> NRST, common GND.

Usage: python dump_flash.py [output.bin]
"""
import sys
import time

import serial

import chipwhisperer as cw

FLASH_BASE = 0x08000000
FLASH_SIZE = 512 * 1024      # STM32L452RE: 512 KB
CHUNK = 256                  # max bytes per Read Memory command
BAUD = 115200
BYTE_GAP = 0.01              # back-to-back bytes through the Husky CDC port get NACKed
RETRIES = 3

out_path = sys.argv[1] if len(sys.argv) > 1 else "flash_dump.bin"

scope = cw.scope()
scope.default_setup()
scope.io.tio1 = "serial_tx"
scope.io.tio2 = "serial_rx"

port = scope.get_serial_ports()[0]["port"]
ser = serial.Serial(port, BAUD, parity=serial.PARITY_EVEN,
                    stopbits=1, bytesize=8, timeout=1)


def enter_bootloader():
    """BOOT0 high, reset, then send 0x7F for auto-baud."""
    scope.io.pdic = "high"
    time.sleep(0.05)
    scope.io.nrst = "low"
    time.sleep(0.2)
    scope.io.nrst = "high_z"
    time.sleep(0.5)
    ser.reset_input_buffer()
    ser.write(b"\x7f")
    if ser.read(1) != b"\x79":
        raise RuntimeError("no ACK to 0x7F handshake")


def send(data):
    for b in data:
        ser.write(bytes([b]))
        time.sleep(BYTE_GAP)


def cmd(code):
    ser.reset_input_buffer()          # resync: drop leftovers
    send(bytes([code, code ^ 0xFF]))
    return ser.read(1)


def read_mem(addr, length):
    """Read Memory command (0x11), length 1..256."""
    if cmd(0x11) != b"\x79":
        raise RuntimeError("Read Memory NACK (readout protection enabled?)")
    a = addr.to_bytes(4, "big")
    send(a + bytes([a[0] ^ a[1] ^ a[2] ^ a[3]]))
    if ser.read(1) != b"\x79":
        raise RuntimeError(f"address NACK at 0x{addr:08X}")
    send(bytes([length - 1, (length - 1) ^ 0xFF]))
    if ser.read(1) != b"\x79":
        raise RuntimeError("length NACK")
    data = ser.read(length)
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

# Get ID as a sanity check (expect 79 01 04 62 79 for the L45x family)
if cmd(0x02) == b"\x79":
    n = ser.read(1)[0]
    pid = ser.read(n + 1)
    ser.read(1)
    print("product ID:", pid.hex())

t0 = time.time()
with open(out_path, "wb") as f:
    for off in range(0, FLASH_SIZE, CHUNK):
        data = read_chunk_with_retry(FLASH_BASE + off, CHUNK)
        f.write(data)
        if (off // CHUNK) % 32 == 0:
            pct = 100 * off / FLASH_SIZE
            print(f"\r{pct:5.1f}%  0x{FLASH_BASE + off:08X}", end="", flush=True)

print(f"\ndone: {FLASH_SIZE} bytes -> {out_path} in {time.time() - t0:.0f}s")

# Boot normally again next time
scope.io.pdic = "low"
ser.close()
