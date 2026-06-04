from opendbc.car.structs import CarParams
from opendbc.car.mg.values import CAR

Ecu = CarParams.Ecu

FW_VERSIONS = {
  CAR.MG_5_EV: {
    (Ecu.eps, 0x721, None): [
      b'\x10gs\x16\x01',
    ],
    (Ecu.fwdCamera, 0x733, None): [
      b'\x10y\x00 \x01',
    ],
    (Ecu.fwdRadar, 0x734, None): [
      b'\x10y\x000\x01',
    ],
  },
  CAR.MG_ZS_EV: {
    (Ecu.eps, 0x721, None): [
      b'\x11\x06c\x94\x01',
    ],
    (Ecu.fwdCamera, 0x733, None): [
      b'\x11\x03\t!\x01',
    ],
    (Ecu.fwdRadar, 0x734, None): [
      b'\x11\x03\t\x18\x01',
    ],
  },
}

FINGERPRINTS = {
  # TODO: populate via tools/car_porting/auto_fingerprint.py once a route
  # with FW query enabled is captured on the 2025 MG ZS
  CAR.MG_ZS: [{
    201: 8, 251: 8, 355: 8, 389: 8, 404: 8, 481: 8, 
    485: 8, 489: 8, 492: 8, 516: 8, 532: 8, 540: 8, 
    593: 8, 758: 8, 851: 8, 886: 8, 901: 8, 1130: 8, 582: 8
  }],
}
