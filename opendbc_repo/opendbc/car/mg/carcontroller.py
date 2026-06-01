import numpy as np
from opendbc.can.packer import CANPacker
from opendbc.car import Bus
from opendbc.car.lateral import apply_driver_steer_torque_limits
from opendbc.car.interfaces import CarControllerBase
from opendbc.car.mg import mgcan
from opendbc.car.mg.values import CarControllerParams, Buttons


class CarController(CarControllerBase):
  def __init__(self, dbc_names, CP):
    super().__init__(dbc_names, CP)
    self.packer = CANPacker(dbc_names[Bus.pt])
    self.apply_torque_last = 0
    self.brake_counter = 0
    self.frame = 0
    self.cancel_frames = 0

  def update(self, CC, CS, now_nanos):
    actuators = CC.actuators
    hud_control = CC.hudControl

    can_sends = []

    # steering command
    if self.frame % CarControllerParams.STEER_STEP == 0:
      if CC.latActive:
        # calculate steer and also set limits due to driver torque
        new_torque = int(round(actuators.torque * CarControllerParams.STEER_MAX))
        apply_torque = apply_driver_steer_torque_limits(new_torque, self.apply_torque_last, CS.out.steeringTorque, CarControllerParams)
      else:
        apply_torque = 0
            
      self.apply_torque_last = apply_torque
      can_sends.append(mgcan.create_lka_steering(self.packer, (self.frame // CarControllerParams.STEER_STEP) % 16, apply_torque, CC.latActive))
      # can_sends.append(mgcan.create_lkas_hud(self.packer, CC.latActive, CS.lkas_hud, hud_control))

    # 修正優化：如果 LKA 根本沒激活，確保回傳給 safety 核心的扭力絕對是 0，避免殘留
    if not CC.latActive:
      self.apply_torque_last = 0
    
    # Longitudinal control 縱向控制
    if self.CP.openpilotLongitudinalControl:
      accel = float(np.clip(actuators.accel, CarControllerParams.ACCEL_MIN, CarControllerParams.ACCEL_MAX))
      #can_sends.append(mgcan.create_longitudinal(self.packer, self.frame, accel, CC.enabled))
      #print(f"[ACCEL]={actuators.accel:.2f}")
    else:
      interface_status = None
      if CC.cruiseControl.cancel:
        # if there is a noEntry, we need to send a status of "available" before the ACM will accept "unavailable"
        # send "available" right away as the VDM itself takes a few frames to acknowledge
        interface_status = 1 if self.cancel_frames < 5 else 0
        self.cancel_frames += 1
        self.brake_counter += 1
      else:
        self.cancel_frames = 0

    self.brake_counter = 0
    if CC.cruiseControl.resume:
      # MG Stop and Go requires a RES button (or gas) press if the car stops more than 3 seconds
      # Send Resume button when planner wants car to move
      pass
      #can_sends.append(mgcan.create_button_cmd(self.packer, CS.crz_btns_counter, Buttons.RESUME))

    #CC.cruiseControl.resume = CC.enabled and CS.cruiseState.standstill and not self.sm['longitudinalPlan'].shouldStop
  
    new_actuators = actuators.as_builder()
    new_actuators.torque = self.apply_torque_last / CarControllerParams.STEER_MAX
    new_actuators.torqueOutputCan = self.apply_torque_last

    self.frame += 1
    return new_actuators, can_sends
