#!/usr/bin/env python3
"""
MG firmware scanner for openpilot / comma hardware.

Queries the MG firmware fingerprint currently used by opendbc:
  Tester Present (0x3E 00)
  ReadDataByIdentifier F191 (Vehicle Manufacturer ECU Hardware Number)

Targets:
  EPS        0x721
  Fwd Camera 0x733
  Fwd Radar  0x734

MG's FW_QUERY_CONFIG uses bus 1 and the standard +0x8 ISO-TP response offset.

IMPORTANT:
- Run while parked, ignition ON.
- Stop openpilot/tmux processes first so boardd is not using the panda.
- This script only performs diagnostic reads; it does not write ECU data.
"""

import argparse
import sys
import time

from panda import Panda
from opendbc.car.structs import CarParams
from opendbc.car.uds import (
  UdsClient,
  DATA_IDENTIFIER_TYPE,
  MessageTimeoutError,
  NegativeResponseError,
)

BUS = 1

ECUS = [
  ("eps", "Ecu.eps", 0x721),
  ("fwdCamera", "Ecu.fwdCamera", 0x733),
  ("fwdRadar", "Ecu.fwdRadar", 0x734),
]


def bytes_literal(data: bytes) -> str:
  """Return a copy/paste-safe Python bytes literal."""
  # repr(bytes) already produces the exact format expected by fingerprints.py.
  return repr(data)


def printable(data: bytes) -> str:
  """Best-effort human-readable representation."""
  return "".join(chr(b) if 32 <= b <= 126 else "." for b in data)


def query_ecu(panda: Panda, name: str, addr: int, bus: int, timeout: float) -> bytes | None:
  print(f"\n[{name}] TX=0x{addr:03X} RX=0x{addr + 8:03X} bus={bus}")

  client = UdsClient(
    panda,
    tx_addr=addr,
    rx_addr=addr + 8,
    bus=bus,
    timeout=timeout,
    response_pending_timeout=5,
  )

  try:
    print("  -> Tester Present")
    client.tester_present()

    # This is DID F191, exactly what MG FW_QUERY_CONFIG requests.
    print("  -> Read DID F191 (Vehicle Manufacturer ECU Hardware Number)")
    fw = client.read_data_by_identifier(
      DATA_IDENTIFIER_TYPE.VEHICLE_MANUFACTURER_ECU_HARDWARE_NUMBER
    )

    print(f"  <- HEX : {fw.hex(' ')}")
    print(f"  <- ASCII: {printable(fw)}")
    print(f"  <- Python: {bytes_literal(fw)}")
    return fw

  except MessageTimeoutError:
    print("  !! timeout: no response")
  except NegativeResponseError as e:
    print(f"  !! negative UDS response: {e}")
  except Exception as e:
    print(f"  !! error: {type(e).__name__}: {e}")

  return None


def print_fw_versions(results: dict[str, bytes | None]) -> None:
  print("\n")
  print("=" * 72)
  print("Copy/paste result for opendbc/car/mg/fingerprints.py")
  print("=" * 72)
  print("CAR.MG_ZS: {")

  for short_name, ecu_enum, addr in ECUS:
    fw = results.get(short_name)
    print(f"  ({ecu_enum}, 0x{addr:03X}, None): [")
    if fw is not None:
      print(f"    {bytes_literal(fw)},")
    else:
      print("    # NO RESPONSE")
    print("  ],")

  print("},")


def main() -> int:
  parser = argparse.ArgumentParser(
    description="Query MG ZS EPS/camera/radar F191 firmware identifiers."
  )
  parser.add_argument("--bus", type=int, default=BUS,
                      help=f"CAN bus to query (default: {BUS}, matching MG FW_QUERY_CONFIG)")
  parser.add_argument("--timeout", type=float, default=1.0,
                      help="UDS response timeout in seconds (default: 1.0)")
  parser.add_argument("--debug", action="store_true",
                      help="Enable UDS debug logging")
  args = parser.parse_args()

  if args.debug:
    from opendbc.car.carlog import carlog
    carlog.setLevel("DEBUG")

  print("MG firmware scanner")
  print("-------------------")
  print("Ignition must be ON. Vehicle must be parked.")
  print("Make sure openpilot/tmux processes are stopped before continuing.")
  print(f"Query bus: {args.bus}")
  print("ECUs:", ", ".join(f"{name}=0x{addr:03X}" for name, _, addr in ECUS))
  print()

  try:
    panda = Panda()
  except Exception as e:
    print(f"Unable to connect to panda: {type(e).__name__}: {e}")
    return 1

  try:
    # Diagnostic-oriented safety mode used by openpilot diagnostic tools.
    panda.set_safety_mode(CarParams.SafetyModel.elm327)
    time.sleep(0.2)

    results: dict[str, bytes | None] = {}
    for short_name, _, addr in ECUS:
      results[short_name] = query_ecu(
        panda, short_name, addr, args.bus, args.timeout
      )

    print_fw_versions(results)

    if not any(v is not None for v in results.values()):
      print("\nNo ECU responded.")
      print("Try:")
      print("  1. Verify ignition is ON")
      print("  2. Verify openpilot/boardd is stopped")
      print("  3. Try --bus 0 or --bus 2 if your branch/harness routes MG diagnostics differently")
      print("  4. Retry with --debug")
      return 2

    return 0

  finally:
    try:
      panda.set_safety_mode(CarParams.SafetyModel.noOutput)
    except Exception:
      pass


if __name__ == "__main__":
  sys.exit(main())
