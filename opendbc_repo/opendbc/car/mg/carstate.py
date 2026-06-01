import copy

from opendbc.can.parser import CANParser
from opendbc.car import Bus, structs
from opendbc.car.interfaces import CarStateBase
from opendbc.car.mg.values import CAR, DBC, GEAR_MAP, GEAR_MAP_EV, BUTTON_STATES
from opendbc.car.common.conversions import Conversions as CV

GearShifter = structs.CarState.GearShifter


class CarState(CarStateBase):
  def __init__(self, CP):
    super().__init__(CP)
    self.lkas_hud = {}
    self.button_states = BUTTON_STATES.copy()
    
  def update(self, can_parsers) -> structs.CarState:
    cp = can_parsers[Bus.pt]
    cp_cam = can_parsers[Bus.cam]
    ret = structs.CarState()

    # Vehicle speed
    ret.vEgoRaw = cp.vl["SCS_HSC2_FrP19"]["VehSpdAvgHSC2"] * CV.KPH_TO_MS
    ret.vEgo, ret.aEgo = self.update_speed_kf(ret.vEgoRaw)
    if self.CP.carFingerprint == CAR.MG_ZS:
      ret.standstill = ret.vEgoRaw < 0.01
    else:
      ret.standstill = cp.vl["SCS_HSC2_FrP24"]["VehSdslStsHSC2"] == 1

    # Gas pedal
    if self.CP.carFingerprint == CAR.MG_ZS:
      ret.gasPressed = cp.vl["Tester_HSC2_ECM_FrP00"]["AccelActuPosHSC2"] > 0
    else:
      ret.gasPressed = cp.vl["GW_HSC2_HCU_FrP00"]["EPTAccelActuPosHSC2"] > 0
    
    # Brake pedal
    ret.brake = 0
    if self.CP.carFingerprint == CAR.MG_ZS_EV:
      ret.brakePressed = cp.vl["GW_HSC2_HCU_FrP00"]["EPTBrkPdlDscrtInptStsHSC2"] == 1
    elif self.CP.carFingerprint == CAR.MG_ZS:
      ret.brakePressed = cp.vl["SCS_HSC2_FrP09"]["BrkPdlDrvrAppdPrsHSC2"] > 0
    else:
      ret.brakePressed = cp.vl["EHBS_HSC2_FrP00"]["BrkPdlAppdHSC2"] == 1

    # Steering wheel
    ret.steeringAngleDeg = cp.vl["SAS_HSC2_FrP00"]["StrgWhlAngHSC2"]
    ret.steeringRateDeg = cp.vl["SAS_HSC2_FrP00"]["StrgWhlAngGrdHSC2"]
    ret.steeringTorque = cp.vl["EPS_HSC2_FrP03"]["DrvrStrgDlvrdToqHSC2"]
    ret.steeringTorqueEps = cp.vl["EPS_HSC2_FrP03"]["ChLKARespToqHSC2"]
    ret.steeringPressed = self.update_steering_pressed(abs(ret.steeringTorque) > 1.0, 5)

    # Lane Departure Warning System Fault Status（車道偏離警示系統故障狀態)
    ret.steerFaultTemporary = cp_cam.vl["FVCM_HSC2_FrP02"]["LDWSysFltStsHSC2"] != 0  # TODO: validate
    if ret.steerFaultTemporary:
      print("(Steer Fault Temporary)！")
     
    # Cruise state
    ret.cruiseState.enabled = cp.vl["RADAR_HSC2_FrP00"]["ACCSysSts_RadarHSC2"] in (2, 3)  # Active, Override
    ret.cruiseState.available = True
    ret.cruiseState.standstill = cp.vl["RADAR_HSC2_FrP00"]["ACCSysSts_RadarHSC2"] == 6
    ret.cruiseState.speed = cp.vl["RADAR_HSC2_FrP02"]["ACCDrvrSelTrgtSpd_RadarHSC2"] * CV.KPH_TO_MS
    ret.accFaulted = cp_cam.vl["FVCM_HSC2_FrP02"]["TJAICASysFltStsHSC2"] != 0  # TODO: validate

    # Gear
    if self.CP.carFingerprint == CAR.MG_ZS:
      ret.gearShifter = GEAR_MAP.get(int(cp.vl["GW_HSC2_ECM_FrP04"]["TrShftLvrPos_h1HSC2"]), GearShifter.unknown)
    else:
      ret.gearShifter = GEAR_MAP_EV.get(int(cp.vl["GW_HSC2_ECM_FrP04"]["TrEstdGearHSC2"]), GearShifter.unknown)

    # Doors 駕駛及副駕開門狀態 
    ret.doorOpen = any([cp.vl["GW_HSC2_BCM_FrP04"]["DrvrDoorOpenSts_H1_Safety"],
                        cp.vl["GW_HSC2_BCM_FrP04"]["FrtPsngDoorOpenSts_H1_Safety"]])
    
    # Blinkers
    if self.CP.carFingerprint == CAR.MG_ZS:
      ret.leftBlinker = bool(cp.vl["GW_HSC2_BCM_FrP04"]["BlinkerLeft"])
      ret.rightBlinker = bool(cp.vl["GW_HSC2_BCM_FrP04"]["BlinkerRight"])
    else:
      ret.leftBlinker = cp.vl["GW_HSC2_BCM_FrP04"]["DircnIndLampSwStsHSC2"] == 1
      ret.rightBlinker = cp.vl["GW_HSC2_BCM_FrP04"]["DircnIndLampSwStsHSC2"] == 2

    # Seatbelt
    ret.seatbeltUnlatched = cp.vl["GW_HSC2_SDM_FrP00"]["DrvrSbltAtcHSC2"] != 1

    # Blindspot 盲點偵測
    ret.leftBlindspot = cp.vl["RDA_HSC1_P02"]["LBSDAndLCAWrnng_HS"] > 0
    ret.rightBlindspot = cp.vl["RDA_HSC1_P02"]["RBSDAndLCAWrnng_HS"] > 0

    # AEB
    ret.stockAeb = False

    # AEB
    # stop & go 起步請求
    # TSR 限速 ret.cruiseState.speedLimit
    limit_speed = cp_cam.vl["FVCM_HSC2_FrP02"]["TrgtSpdReqCamrHSC2"] 
    #print(
      #f'SPEED={limit_speed}, '
      #f'AEB={cp.vl["RADAR_HSC2_FrP02"]["AEBMsgReqHSC2"]}, '
      #f'GO={cp.vl["RADAR_HSC2_FrP02"]["ACCGoNotfr_RadarHSC2"]}'
    #) 

    # Update control button states for turn signals and ACC controls.
    self.button_states["accel_cruise"]  = bool(cp.vl["GW_HSC2_FrP04"]["CCSwStsSpdIncSwA_h2HSC2"])
    self.button_states["decel_cruise"]  = bool(cp.vl["GW_HSC2_FrP04"]["CCSwStsSpdDecSwA_h2HSC2"])
    self.button_states["cancel"]        = bool(cp.vl["GW_HSC2_FrP04"]["CCSwStsCanclSwA_h2HSC2"])
    self.button_states["set_cruise"]    = bool(cp.vl["GW_HSC2_FrP04"]["CCSwStsSetSwA_h2HSC2"])
    self.button_states["resume_cruise"] = bool(cp.vl["GW_HSC2_FrP04"]["CCSwStsRsmSwA_h2HSC2"])
    self.button_states["on_cruise"]     = bool(cp.vl["GW_HSC2_FrP04"]["CCSwStsOnSwA_h2HSC2"])
    
    # forward stock LKAS HUD
#   self.lkas_hud = copy.copy(cp_cam.vl["FVCM_HSC2_FrP02"])
    
    return ret

  @staticmethod
  def get_can_parsers(CP):
    return {
      Bus.pt: CANParser(DBC[CP.carFingerprint][Bus.pt], [], 0),
      Bus.radar: CANParser(DBC[CP.carFingerprint][Bus.pt], [], 1),
      Bus.cam: CANParser(DBC[CP.carFingerprint][Bus.pt], [], 2),
    }
