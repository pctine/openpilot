from opendbc.car.structs import CarParams
from opendbc.car.mg.values import CAR

Ecu = CarParams.Ecu

FW_VERSIONS = {
  CAR.MG_5_EV: {
    (Ecu.eps, 0x721, None): [
      b'\x10\x67\x73\x16\x01',
    ],
    (Ecu.fwdCamera, 0x733, None): [
      b'\x10\x79\x00\x20\x01',
    ],
    (Ecu.fwdRadar, 0x734, None): [
      b'\x10\x79\x00\x30\x01',
    ],
  },
  CAR.MG_ZS_EV: {
    (Ecu.eps, 0x721, None): [
      b'\x11\x06\x63\x94\x01',
    ],
    (Ecu.fwdCamera, 0x733, None): [
      b'\x11\x03\x09\x21\x01',
    ],
    (Ecu.fwdRadar, 0x734, None): [
      b'\x11\x03\x09\x18\x01',
    ],
  },
  CAR.MG_ZS: {
    (Ecu.eps, 0x721, None): [
      b'\x11\x06\x63\x94\x01',
    ],
    (Ecu.fwdCamera, 0x733, None): [
      b'\x10\x89\x77\x51\x01',
    ],
    (Ecu.fwdRadar, 0x732, None): [
      b'\x11\x52\x75\x50\x01',
    ],
  },  
}
