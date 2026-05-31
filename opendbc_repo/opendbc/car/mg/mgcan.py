from opendbc.car.mg.values import Buttons

def calc_checksum(values):
  lka_req_toq = values['LKAReqToqHSC2'] + 1024
  lka_req_toq_sts = values['LKAReqToqStsHSC2']
  lka_req_toq_v = values['LKAReqToqVHSC2']
  lka_alv_rc = values['LKAAlvRCHSC2']

  combined = ((lka_req_toq << 1) | (lka_req_toq_sts << 12) | lka_req_toq_v) & 0x3FFF
  with_counter = (combined + lka_alv_rc) & 0x3FFF
  checksum = ((~with_counter) + 1) & 0x3FFF

  return checksum


def create_lka_steering(packer, counter, apply_torque, active):

  values = {
    "LKAReqToqHSC2": apply_torque,
    "LKAReqToqVHSC2": 0,
    "LKAAlvRCHSC2": counter,
    "LDWLKAVbnLvlReqHSC2": 0,  # TODO: vibration level?
    "LKASysStsHSC2": 0,
    "LKAReqToqStsHSC2": active,
    "LKASysFltStsHSC2": 0,
    "LKADrvrTkovReqHSC2": 0,
    "LKAReqToqPVHSC2": 0
  }

  values["LKAReqToqPVHSC2"] = calc_checksum(values)
  return packer.make_can_msg("FVCM_HSC2_FrP03", 0, values)

def create_lkas_hud(packer, lat_active: bool, stock_lkas_hud: dict, hud_control):
  values = dict(stock_lkas_hud)

  print(f"[HUD] LEFT: {values.get('LDWLKALVsulznReqHSC2')}, RIGHT: {values.get('LDWLKARVsulznReqHSC2')}")
  
  if lat_active:
    # values["HandOffStrgWhlDetnStaHSC2"] = 1
    # values["LDWLKALVsulznReqHSC2"] = 2
    # values["LDWLKARVsulznReqHSC2"] = 2
    pass
   
  return packer.make_can_msg("FVCM_HSC2_FrP02", 2, values)

def create_button_cmd(packer, counter, button):
  can = int(button == Buttons.CANCEL)
  res = int(button == Buttons.RESUME)

  values = {
    "CAN_OFF": can,
    "CAN_OFF_INV": (can + 1) % 2,

    "SET_P": 0,
    "SET_P_INV": 1,

    "RES": res,
    "RES_INV": (res + 1) % 2,

    "SET_M": 0,
    "SET_M_INV": 1,

    "DISTANCE_LESS": 0,
    "DISTANCE_LESS_INV": 1,

    "DISTANCE_MORE": 0,
    "DISTANCE_MORE_INV": 1,

    "MODE_X": 0,
    "MODE_X_INV": 1,

    "MODE_Y": 0,
    "MODE_Y_INV": 1,

    "BIT1": 1,
    "BIT2": 1,
    "BIT3": 1,
    "CTR": (counter + 1) % 16,
  }

  #return packer.make_can_msg("CRZ_BTNS", 0, values)
  return []
  
