#!/usr/bin/env python3

import time

from panda import Panda

from opendbc.car.uds import (
  UdsClient,
  MessageTimeoutError,
  NegativeResponseError,
)


# ============================================
# MG ECU Scanner
# ============================================

BUSES = [0, 1, 2]

START_ADDR = 0x700
END_ADDR = 0x7FF

SCAN_TIMEOUT = 0.15
DID_TIMEOUT = 0.3

SCAN_DELAY = 0.01


# 常用 UDS DID
DIDS = {
  0xF180: "Boot Software Identification",
  0xF181: "Application Software Identification",
  0xF182: "Application Data Identification",
  0xF187: "Spare Part Number",
  0xF188: "ECU Software Number",
  0xF189: "ECU Software Version",
  0xF18A: "System Supplier Identifier",
  0xF18B: "ECU Manufacturing Date",
  0xF18C: "ECU Serial Number",
  0xF190: "VIN",
  0xF191: "ECU Hardware Number",
  0xF192: "Supplier ECU Hardware Number",
  0xF193: "Supplier ECU Hardware Version",
  0xF194: "Supplier ECU Software Number",
  0xF195: "Supplier ECU Software Version",
  0xF197: "System Name / Engine Type",
  0xF19E: "ODX File",
}


def clean_ascii(data):
  """
  嘗試把 ECU 回傳內容顯示成可讀 ASCII。
  無法顯示的 byte 仍保留 hex。
  """
  if not data:
    return ""

  try:
    text = data.decode("ascii", errors="replace")
    text = text.replace("\x00", "").strip()
  except Exception:
    text = ""

  return text


def create_uds(panda, bus, addr, timeout):
  return UdsClient(
    panda,
    addr,
    bus=bus,
    timeout=timeout,
    tx_timeout=timeout,
  )


def probe_ecu(panda, bus, addr):
  """
  用 TesterPresent 判斷 ECU 是否存在。

  Positive response:
      3E 00 -> 7E 00

  若 ECU 回 NegativeResponse，仍代表 address 有 ECU。
  """

  uds = create_uds(
    panda,
    bus,
    addr,
    SCAN_TIMEOUT,
  )

  try:
    uds.tester_present()
    return True, "positive"

  except NegativeResponseError as e:
    # 有 Negative Response 其實也證明 ECU 存在
    return True, f"negative response: {e}"

  except MessageTimeoutError:
    return False, None

  except Exception:
    return False, None


def read_did(panda, bus, addr, did):
  uds = create_uds(
    panda,
    bus,
    addr,
    DID_TIMEOUT,
  )

  try:
    data = uds.read_data_by_identifier(did)

    return {
      "ok": True,
      "data": data,
      "ascii": clean_ascii(data),
      "hex": data.hex(" "),
    }

  except NegativeResponseError as e:
    return {
      "ok": False,
      "error": f"NegativeResponse: {e}",
    }

  except MessageTimeoutError:
    return {
      "ok": False,
      "error": "timeout",
    }

  except Exception as e:
    return {
      "ok": False,
      "error": str(e),
    }


def scan_bus(panda, bus):
  print()
  print("=" * 70)
  print(f"Scanning CAN BUS {bus}")
  print(f"Address range: 0x{START_ADDR:03X} - 0x{END_ADDR:03X}")
  print("=" * 70)

  found = []

  for addr in range(START_ADDR, END_ADDR + 1):

    print(
      f"\rBUS {bus} scanning 0x{addr:03X}",
      end="",
      flush=True,
    )

    exists, response_type = probe_ecu(
      panda,
      bus,
      addr,
    )

    if exists:
      print()
      print(
        f"[FOUND] BUS={bus} "
        f"TX=0x{addr:03X} "
        f"RX=0x{addr + 8:03X} "
        f"({response_type})"
      )

      found.append(addr)

    time.sleep(SCAN_DELAY)

  print()

  return found


def dump_ecu_info(panda, bus, addr):
  print()
  print("-" * 70)

  print(
    f"ECU BUS={bus} "
    f"TX=0x{addr:03X} "
    f"RX=0x{addr + 8:03X}"
  )

  print("-" * 70)

  results = {}

  for did, name in DIDS.items():

    result = read_did(
      panda,
      bus,
      addr,
      did,
    )

    results[did] = result

    if result["ok"]:

      ascii_value = result["ascii"]
      hex_value = result["hex"]

      print(
        f"0x{did:04X} "
        f"{name}"
      )

      if ascii_value:
        print(
          f"    ASCII : {ascii_value}"
        )

      print(
        f"    HEX   : {hex_value}"
      )

    else:

      error = result["error"]

      # 不印大量 timeout，畫面比較乾淨
      if error != "timeout":
        print(
          f"0x{did:04X} "
          f"{name}"
        )

        print(
          f"    ERROR : {error}"
        )

  return results


def print_summary(all_ecus):
  print()
  print()
  print("=" * 70)
  print("MG ECU SCAN SUMMARY")
  print("=" * 70)

  total = 0

  for bus, ecus in all_ecus.items():

    print()
    print(f"BUS {bus}")

    if not ecus:
      print("  No ECU found")
      continue

    for addr in ecus:
      print(
        f"  TX 0x{addr:03X} "
        f"-> RX 0x{addr + 8:03X}"
      )

      total += 1

  print()
  print("=" * 70)
  print(f"Total ECU addresses found: {total}")
  print("=" * 70)


def main():
  print()
  print("MG openpilot ECU scanner")
  print("========================")
  print()
  print("Scan buses:", BUSES)
  print(
    f"Address range: "
    f"0x{START_ADDR:03X}-0x{END_ADDR:03X}"
  )

  print()
  print("Connecting Panda...")

  panda = Panda()

  #
  # Diagnostic mode
  #
  # ELM327 safety mode 允許 diagnostic CAN traffic，
  # 避免 openpilot car safety policy 阻擋 UDS request。
  #
  try:
    from cereal import car

    panda.set_safety_mode(
      car.CarParams.SafetyModel.elm327
    )

    print("Panda safety mode: ELM327")

  except Exception as e:
    print(
      f"WARNING: unable to set ELM327 safety mode: {e}"
    )

  all_ecus = {}

  #
  # STEP 1
  # Scan ECU addresses
  #

  for bus in BUSES:

    found = scan_bus(
      panda,
      bus,
    )

    all_ecus[bus] = found

  #
  # Summary
  #

  print_summary(all_ecus)

  #
  # STEP 2
  # Read ECU DID information
  #

  print()
  print()
  print("=" * 70)
  print("Reading ECU identification DIDs")
  print("=" * 70)

  all_results = {}

  for bus, ecus in all_ecus.items():

    for addr in ecus:

      key = (bus, addr)

      all_results[key] = dump_ecu_info(
        panda,
        bus,
        addr,
      )

  print()
  print()
  print("=" * 70)
  print("SCAN COMPLETE")
  print("=" * 70)


if __name__ == "__main__":
  main()