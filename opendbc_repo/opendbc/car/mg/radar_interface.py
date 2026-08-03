from opendbc.can.parser import CANParser
from opendbc.car import Bus, structs
from opendbc.car.interfaces import RadarInterfaceBase
from opendbc.car.mg.values import DBC


PROB_THRESHOLD = 0.2  # 存在機率低於 20% 視為無效
MAX_STALE_FRAMES = 5  # 連續多個雷達更新週期未出現時剔除
RADAR_MSG = "RADAR_HSC2_FrP07"
RADAR_FREQUENCY = 20


def get_can_parser(CP):
  messages = [
    (RADAR_MSG, RADAR_FREQUENCY),
  ]

  # MG 雷達訊息目前定義在 PT DBC，但實際接收來源為 radar bus。
  return CANParser(
    DBC[CP.carFingerprint][Bus.pt],
    messages,
    Bus.radar,
  )


class TrackPointInternal:
  def __init__(self, track_id: int):
    self.track_id = track_id
    self.dRel = 0.0
    self.yRel = 0.0
    self.vRel = 0.0
    self.aRel = float("nan")
    self.measured = True
    self.updated_this_frame = False
    self.stale_count = 0


class RadarInterface(RadarInterfaceBase):
  def __init__(self, CP):
    super().__init__(CP)

    self.radar_off = CP.radarUnavailable
    self.pts: dict[int, TrackPointInternal] = {}
    self.rcp = None if self.radar_off else get_can_parser(CP)

  def update(self, can_strings) -> structs.RadarData | None:
    if self.radar_off or self.rcp is None:
      return structs.RadarData()

    # 讀取這次收到的 CAN 封包。
    updated_messages = self.rcp.update_strings(can_strings)
    if not updated_messages:
      return None

    # 重設本輪更新狀態。
    for track in self.pts.values():
      track.updated_this_frame = False

    # 處理本輪收到的所有雷達目標。
    for msg in self.rcp.vl_all.get(RADAR_MSG, []):
      track_id = int(msg["ACCDetObjIdHSC2"])
      exist_prob = float(msg["ACCDetObjExistPrbltyHSC2"])

      if exist_prob < PROB_THRESHOLD:
        self.pts.pop(track_id, None)
        continue

      track = self.pts.setdefault(track_id, TrackPointInternal(track_id))
      track.updated_this_frame = True
      track.stale_count = 0
      track.dRel = float(msg["ACCDetObjLongtRltvDistHSC2"])
      track.yRel = float(msg["ACCDetObjLatRltvDistHSC2"])
      track.vRel = float(msg["ACCDetObjLongtRltvSpdHSC2"])
      track.aRel = float("nan")
      track.measured = True

    # 清除連續多輪沒有更新的目標。
    for track_id in list(self.pts):
      track = self.pts[track_id]
      if track.updated_this_frame:
        continue

      track.stale_count += 1
      if track.stale_count > MAX_STALE_FRAMES:
        del self.pts[track_id]

    # 打包成 openpilot RadarData。
    ret = structs.RadarData()
    ret.points = []

    for track_id, track in self.pts.items():
      point = structs.RadarData.TrackPoint()
      point.trackId = track_id
      point.dRel = track.dRel
      point.yRel = track.yRel
      point.vRel = track.vRel
      point.aRel = track.aRel
      point.measured = track.measured
      ret.points.append(point)

    ret.errors = []
    return ret
