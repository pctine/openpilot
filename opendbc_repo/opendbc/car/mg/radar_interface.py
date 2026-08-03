#!/usr/bin/env python3
from opendbc.can.parser import CANParser
from opendbc.car import Bus, structs
from opendbc.car.interfaces import RadarInterfaceBase
from opendbc.car.mg.values import DBC

# 設定機率與逾時門檻
PROB_THRESHOLD = 0.2  # 存在機率低於 20% 視為無效
MAX_STALE_FRAMES = 5  # 若連續 5 個雷達 Frame (約 250ms) 沒更新該 ID，則主動剔除


class TrackPointInternal:

  def __init__(self, track_id):
    self.track_id = track_id
    self.point = structs.RadarData.TrackPoint()
    self.point.trackId = track_id
    self.updated_this_frame = False
    self.stale_count = 0  # 記錄未收到更新的連續 Frame 數


class RadarInterface(RadarInterfaceBase):

  def __init__(self, CP):
    super().__init__(CP)

    self.radar_off = CP.radarUnavailable
    if self.radar_off:
      return

    self.trigger_msg = 0x385  # 901
    self.updated_messages = set()

    # 使用內部類別來維護 TrackPoint 及其生命週期狀態
    self.pts = {}  # Dict[int, TrackPointInternal]

    self.rcp = self.get_can_parser(CP)

  def update(self, can_strings) -> structs.RadarData | None:
    if self.radar_off:
      return structs.RadarData()

    # 1. 讀取並更新 CAN 數據
    vls = self.rcp.update_strings(can_strings)
    self.updated_messages.update(vls)

    # 2. 檢查是否收到觸發訊息 (0x385)，未收到前先不安裝完整 Frame
    if self.trigger_msg not in self.updated_messages:
      return None

    # -------------------------------------------------------------
    # 重設當前 Frame 的更新標記
    for track in self.pts.values():
      track.updated_this_frame = False

    # 3. 解析最新的 CAN 報文
    msg = self.rcp.vl["RADAR_HSC2_FrP07"]
    track_id = int(msg["ACCDetObjIdHSC2"])
    exist_prob = msg["ACCDetObjExistPrbltyHSC2"]

    # 4. 處理當前 CAN 封包帶來的 Target 更新/新增/刪除
    if exist_prob < PROB_THRESHOLD:
      # 機率太低：若原本存在則直接移除 (舊目標消失)
      if track_id in self.pts:
        del self.pts[track_id]
    else:
      # 新目標加入：建立新的 TrackPoint
      if track_id not in self.pts:
        self.pts[track_id] = TrackPointInternal(track_id)

      # 舊/新目標數據更新
      track = self.pts[track_id]
      track.updated_this_frame = True
      track.stale_count = 0  # 歸零逾時計數器

      # 填入物理數值
      track.point.dRel = float(msg["ACCDetObjLongtRltvDistHSC2"])
      track.point.yRel = float(msg["ACCDetObjLatRltvDistHSC2"])
      track.point.vRel = float(msg["ACCDetObjLongtRltvSpdHSC2"])
      track.point.aRel = float("nan")
      track.point.measured = True

    # 5. 清理過期/逾時目標 (Stale/Timeout Removal)
    # 處理那些「雷達突然停止發送封包」的舊目標
    for t_id in list(self.pts.keys()):
      track = self.pts[t_id]
      if not track.updated_this_frame:
        track.stale_count += 1
        # 當連續未更新次數超過門檻，將其從列表中剔除
        if track.stale_count > MAX_STALE_FRAMES:
          del self.pts[t_id]

    # 6. 打包所有有效的 TrackPoints 回傳給 openpilot
    ret = structs.RadarData()
    ret.points = [t.point for t in self.pts.values()]
    ret.errors = []
    self.updated_messages.clear()

    return ret

  @staticmethod
  def get_can_parser(CP):
    messages = [
      ("RADAR_HSC2_FrP07", 20),
    ]
    return CANParser(DBC[CP.carFingerprint][Bus.pt], messages, 1)