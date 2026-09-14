#!/usr/bin/env python3

from panda import Panda
from opendbc.car.uds import UdsClient
import time


BUS = 0

START_ADDR = 0x700
END_ADDR = 0x7FF


def scan_ecu(panda, addr):
  try:
    uds = UdsClient(
      panda,
      addr,
      bus=BUS,
      timeout=0.15,
    )

    # UDS TesterPresent
    uds.tester_present()

    print(f"[FOUND] ECU TX=0x{addr:03X}")

    return True

  except Exception:
    return False


def main():
  panda = Panda()

  print(f"Scanning bus {BUS}")
  print(f"Address range: 0x{START_ADDR:X} - 0x{END_ADDR:X}")
  print()

  found = []

  for addr in range(START_ADDR, END_ADDR + 1):

    print(f"\rScanning 0x{addr:03X}", end="", flush=True)

    if scan_ecu(panda, addr):
      found.append(addr)

    time.sleep(0.01)

  print()
  print()
  print("================================")
  print("ECU scan completed")
  print("================================")

  for addr in found:
    print(f"0x{addr:03X}")

  print()
  print(f"Total: {len(found)} ECU(s)")


if __name__ == "__main__":
  main()