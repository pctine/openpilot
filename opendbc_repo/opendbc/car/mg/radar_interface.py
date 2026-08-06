from opendbc.can.parser import CANParser
from opendbc.car import Bus
from opendbc.car.interfaces import RadarInterfaceBase
from opendbc.car.mg.values import DBC


RADAR_MSG = "RADAR_HSC2_FrP07"
RADAR_FREQUENCY = 20
RADAR_BUS = 1


def get_can_parser(CP):
  messages = [
    (RADAR_MSG, RADAR_FREQUENCY),
  ]

  # MG Radar 訊息定義在 PT DBC，實際從 CAN bus 1 接收。
  return CANParser(
    DBC[CP.carFingerprint][Bus.pt],
    messages,
    RADAR_BUS,
  )


class RadarInterface(RadarInterfaceBase):
  def __init__(self, CP):
    super().__init__(CP)

    # Debug 版本強制建立 Radar CAN parser，
    # 不檢查 CP.radarUnavailable。
    self.rcp = get_can_parser(CP)

  def update(self, can_strings):
    # 將收到的 CAN 封包交給 CANParser。
    updated_messages = self.rcp.update_strings(can_strings)

    # 本輪沒有收到 901 Radar 訊息。
    if RADAR_MSG not in updated_messages:
      return None

    # 取得本輪收到的所有 901 訊息。
    for msg in self.rcp.vl_all.get(RADAR_MSG, []):
      print(
        f"[MG RADAR 901/0x385] "
        f"ID={int(msg['ACCDetObjIdHSC2']):2d} "
        f"ObjP={float(msg['ACCDetObjExistPrbltyHSC2']):6.3f} "
        f"ObsP={float(msg['ACCDetObsExistPrbltyHSC2']):6.3f} "
        f"D={float(msg['ACCDetObjLongtRltvDistHSC2']):7.2f}m "
        f"Y={float(msg['ACCDetObjLatRltvDistHSC2']):7.2f}m "
        f"V={float(msg['ACCDetObjLongtRltvSpdHSC2']):7.2f}m/s "
        f"Sync={int(msg['ACCDetObjSyncCtrHSC2']):2d}"
      )

    # 純 Debug：不建立 RadarData，也不產生 RadarPoint。
    return None
