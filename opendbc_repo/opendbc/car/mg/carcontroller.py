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

  def update(self, CC, CS, now_nanos):
    actuators = CC.actuators

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
      can_sends.append(create_lka_steering(self.packer, (self.frame // CarControllerParams.STEER_STEP) % 16, apply_torque, CC.latActive))
      
      ## create lka_hud can message (CAN Bus2)
      ## io: (packer, tja_ica_sys_state, is_left_line_visiable, is_right_line_visiable, handoff_wrnng_lvl):
      hud_state = 2 if CC.enabled else 1
      can_sends.append(create_lkas_hud(self.packer, hud_state, hud_state, hud_state, 2))
              
    new_actuators = actuators.as_builder()
    new_actuators.torque = self.apply_torque_last / CarControllerParams.STEER_MAX
    new_actuators.torqueOutputCan = self.apply_torque_last

    self.frame += 1
    return new_actuators, can_sends
