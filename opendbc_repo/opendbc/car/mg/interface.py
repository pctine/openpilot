from opendbc.car import get_safety_config, structs
from opendbc.car.interfaces import CarInterfaceBase
from opendbc.car.mg.carcontroller import CarController
from opendbc.car.mg.carstate import CarState
from opendbc.car.mg.values import CAR, MgSafetyFlags


class CarInterface(CarInterfaceBase):
  CarState = CarState
  CarController = CarController

  @staticmethod
  def _get_params(ret: structs.CarParams, candidate, fingerprint, car_fw, alpha_long, is_release, docs) -> structs.CarParams:
    ret.brand = "mg"

    ret.safetyConfigs = [get_safety_config(structs.CarParams.SafetyModel.mg)]

    # DEBUG
    print(f"MG interface called: candidate={candidate}")
    
    if candidate == CAR.MG_ZS_EV:
      ret.safetyConfigs[0].safetyParam |= MgSafetyFlags.ALT_BRAKE.value
    elif candidate == CAR.MG_ZS:
      ret.safetyConfigs[0].safetyParam |= MgSafetyFlags.NON_EV.value

    ret.steerActuatorDelay = 0.3
    CarInterfaceBase.configure_torque_tune(candidate, ret.lateralTuning)

    ret.steerControlType = structs.CarParams.SteerControlType.torque
    
    # 1. 啟用實體雷達 (不再將雷達標記為不可用)
    ret.radarUnavailable = True

    # Shadow longitudinal：
    # 讓 openpilot 執行縱向規劃與 LongControl 計算，
    # 但 CarController 不送任何縱向 CAN 訊息
    ret.alphaLongitudinalAvailable = False
    ret.openpilotLongitudinalControl = True

    # Engagement 繼續跟隨原車 ACC 狀態
    ret.pcmCruise = True
    
    ret.longitudinalActuatorDelay = 0.35
    ret.vEgoStopping = 0.25
    ret.stopAccel = 0

    return ret
