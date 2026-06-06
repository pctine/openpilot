from dataclasses import dataclass, field
from enum import IntFlag

from opendbc.car import Bus, CarSpecs, DbcDict, PlatformConfig, Platforms, structs, uds
from opendbc.car.docs_definitions import CarHarness, CarDocs, CarParts
from opendbc.car.fw_query_definitions import FwQueryConfig, Request, StdQueries, p16


@dataclass
class MgCarDocs(CarDocs):
  package: str = "All"
  car_parts: CarParts = field(default_factory=CarParts.common([CarHarness.mg_a]))


@dataclass
class MgPlatformConfig(PlatformConfig):
  dbc_dict: DbcDict = field(default_factory=lambda: {Bus.pt: 'mg', Bus.radar: 'mg'})


class CAR(Platforms):
  MG_5_EV = MgPlatformConfig(
    [
      MgCarDocs("MG 5 EV 2021-24"),
    ],
    CarSpecs(mass=1640., wheelbase=2.66, steerRatio=15.8),
  )

  MG_ZS_EV = MgPlatformConfig(
    [
      MgCarDocs("MG ZS EV 2022"),
    ],
    CarSpecs(mass=1590., wheelbase=2.58, steerRatio=15.8),
  )

  MG_ZS = MgPlatformConfig(
    [
      MgCarDocs("MG ZS 2025"),
    ],
    CarSpecs(mass=1295., wheelbase=2.58, steerRatio=15.8),
  )


MG_VERSION_REQUEST = bytes([uds.SERVICE_TYPE.READ_DATA_BY_IDENTIFIER]) + \
  p16(0xf1a0)
MG_VERSION_RESPONSE = bytes([uds.SERVICE_TYPE.READ_DATA_BY_IDENTIFIER + 0x40])

FW_QUERY_CONFIG = FwQueryConfig(
  requests=[
    Request(
      [StdQueries.TESTER_PRESENT_REQUEST, StdQueries.MANUFACTURER_ECU_HARDWARE_NUMBER_REQUEST],
      [StdQueries.TESTER_PRESENT_RESPONSE, StdQueries.MANUFACTURER_ECU_HARDWARE_NUMBER_RESPONSE],
      bus=1,
    ),
  ],
)

GEAR_MAP_EV = {
  0: structs.CarState.GearShifter.unknown,
  15: structs.CarState.GearShifter.park,
  14: structs.CarState.GearShifter.reverse,
  13: structs.CarState.GearShifter.neutral,
  **{i: structs.CarState.GearShifter.drive for i in range(1, 9)},
}

GEAR_MAP = {
  0: structs.CarState.GearShifter.unknown,
  1: structs.CarState.GearShifter.park,
  2: structs.CarState.GearShifter.reverse,
  3: structs.CarState.GearShifter.neutral,
  4: structs.CarState.GearShifter.drive,
}

BUTTON_STATES = {
  "accel_cruise": False,
  "decel_cruise": False,
  "cancel": False,
  "set_cruise": False,
  "resume_cruise": False,
  "on_cruise": False
}

class CarControllerParams:
  # --- 橫向控制（轉向力矩） ---
  STEER_STEP = 2               # FVCM_HSC2_FrP03 訊息發送步長，Base 100Hz / 2 = 50Hz (每20ms發送一次)
  STEER_MAX = 300              # 系統允許輸出的最大轉向力矩絕對值（CAN 允許上限）
# STEER_DELTA_UP = 10          # 每次循環（20ms）允許力矩增加的最大幅度，用來防止轉向過猛
# STEER_DELTA_DOWN = 15        # 每次循環（20ms）允許力矩減少的最大幅度，設定較高可讓系統快速釋放控制權
  STEER_DELTA_UP = 8          # 每次循環（20ms）允許力矩增加的最大幅度，用來防止轉向過猛
  STEER_DELTA_DOWN = 8        # 每次循環（20ms）允許力矩減少的最大幅度，設定較高可讓系統快速釋放控制權
  
  # --- 駕駛介入與安全權重（防止拉扯/畫龍） ---
  STEER_DRIVER_ALLOWANCE = 100 # 駕駛介入時，允許人手施加的最大力矩緩衝值，超過後系統開始限流
  STEER_DRIVER_MULTIPLIER = 2  # 駕駛力矩的計算權重，數值愈大對人手介入越敏感
  STEER_DRIVER_FACTOR = 100    # 駕駛介入的縮放係數，用於計算最終的安全限制邊界（Driver Filter）

  # --- 縱向控制（加減速限制） ---
  ACCEL_MIN = -3.5             # 最大減速度限制 (m/s^2)，約 -0.36g，確保煞車舒適度
  ACCEL_MAX = 2.0              # 最大加速度限制 (m/s^2)，約 0.2g，避免起步跟車暴衝
  
  def __init__(self, CP):
    pass


class MgSafetyFlags(IntFlag):
  LONG_CONTROL = 1
  ALT_BRAKE = 2
  NON_EV = 4


class Buttons:
  NONE = 0
  SET_PLUS = 1
  SET_MINUS = 2
  RESUME = 3
  CANCEL = 4

DBC = CAR.create_dbc_map()
