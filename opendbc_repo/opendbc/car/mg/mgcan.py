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
  values = {**stock_lkas_hud, "HandOffStrgWhlDetnStaHSC2": 1}
    
  if lat_active:
    values.update({
      "HandOffStrgWhlDetnStaHSC2"  : 1,  # hands off warnning, 1 is no warnning
      "HandOffStrgWhlDetnStaVHSC2" : 0,  # hands off warnning valid, 0 is valid
      "LDWLKADspCmdHSC2"           : 1,  #  LKA display command
      "LDWLKAHapticWrnngDspCmdHSC2": 0,  # handoff_wrnng_lvl 
      "TJAICADspCmdHSC2"           : 1,  #  TJA display command ,default open
      "TJAICASysFltStsHSC2"        : 0,
      "TJAICASysStsHSC2"           : 2,  #  TJA system status
      "LDWLKALVsulznReqHSC2"       : 15, # left lane line display
      "LDWLKARVsulznReqHSC2"       : 15, # right lane line display
    })
    
  return packer.make_can_msg("FVCM_HSC2_FrP02", 2, values)
