import numpy as np
from opendbc.can.packer import CANPacker
from opendbc.car import Bus
from opendbc.car.lateral import apply_driver_steer_torque_limits
from opendbc.car.interfaces import CarControllerBase
from opendbc.car.mg.mgcan import create_lka_steering, create_lkas_hud
from opendbc.car.mg.values import CarControllerParams


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
    apply_torque = 0
    if self.frame % CarControllerParams.STEER_STEP == 0:
      if CC.latActive:
        # calculate steer and also set limits due to driver torque
        new_torque = int(round(actuators.torque * CarControllerParams.STEER_MAX))
        apply_torque = apply_driver_steer_torque_limits(new_torque, self.apply_torque_last, CS.out.steeringTorque, CarControllerParams)
   
      self.apply_torque_last = apply_torque
      can_sends.append(create_lka_steering(self.packer, (self.frame // CarControllerParams.STEER_STEP) % 16, apply_torque, CC.latActive))
      # can_sends.append(create_lkas_hud(self.packer, CC.latActive, CS.lkas_hud, hud_control))
    
    # Longitudinal control 縱向控制
    if self.CP.openpilotLongitudinalControl:
      accel = float(np.clip(actuators.accel, CarControllerParams.ACCEL_MIN, CarControllerParams.ACCEL_MAX))
      #can_sends.append(create_longitudinal(self.packer, self.frame, accel, CC.enabled))
      print(
        f"[ACCEL]:{actuators.accel:.2f}, "
        f"[SPEED]:{actuators.speed:.2f}, "
      )
    else:
      interface_status = None
      if CC.cruiseControl.cancel:
        # if there is a noEntry, we need to send a status of "available" before the ACM will accept "unavailable"
        # send "available" right away as the VDM itself takes a few frames to acknowledge
        interface_status = 1 if self.cancel_frames < 5 else 0
        self.cancel_frames += 1
      else:
        self.cancel_frames = 0

      #for msg in CS.vdm_adas_status:
      #  can_sends.append(create_adas_status(self.packer, msg, interface_status))
    
    new_actuators = actuators.as_builder()
    new_actuators.torque = self.apply_torque_last / CarControllerParams.STEER_MAX
    new_actuators.torqueOutputCan = self.apply_torque_last

    self.frame += 1
    return new_actuators, can_sends
