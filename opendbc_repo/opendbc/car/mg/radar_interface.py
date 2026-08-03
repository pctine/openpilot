import math
from opendbc.can.parser import CANParser
from opendbc.car import Bus, structs
from opendbc.car.interfaces import RadarInterfaceBase
from opendbc.car.mg.values import DBC

PROB_THRESHOLD = 0.2  # 存在機率低於 20% 視為無效
MAX_STALE_FRAMES = 5  # 若連續 5 個雷達 Frame 沒更新該 ID，則主動剔除


def get_can_parser(CP):
    messages = [
        ("RADAR_HSC2_FrP07", 20),
    ]
    return CANParser(DBC[CP.carFingerprint][Bus.pt], messages, 1)


class TrackPointInternal:
    def __init__(self, track_id):
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
        if self.radar_off:
            return

        self.pts = {}  # Dict[int, TrackPointInternal]
        self.rcp = get_can_parser(CP)

    def update(self, can_strings) -> structs.RadarData | None:
        if self.radar_off:
            return structs.RadarData()

        # 1. 讀取 CAN 數據
        vls = self.rcp.update_strings(can_strings)

        # 若這批 can_strings 內沒有雷達訊息，直接返回 None
        if not vls:
            return None

        # 2. 重設當前 Frame 的更新標記
        for track in self.pts.values():
            track.updated_this_frame = False

        # 3. 處理當前 CAN 封包帶來的所有 Target 更新/新增
        msgs = self.rcp.vl_all.get("RADAR_HSC2_FrP07", [])
        for msg in msgs:
            track_id = int(msg["ACCDetObjIdHSC2"])
            exist_prob = msg["ACCDetObjExistPrbltyHSC2"]

            if exist_prob < PROB_THRESHOLD:
                if track_id in self.pts:
                    del self.pts[track_id]
            else:
                if track_id not in self.pts:
                    self.pts[track_id] = TrackPointInternal(track_id)

                track = self.pts[track_id]
                track.updated_this_frame = True
                track.stale_count = 0

                track.dRel = float(msg["ACCDetObjLongtRltvDistHSC2"])
                track.yRel = float(msg["ACCDetObjLatRltvDistHSC2"])
                track.vRel = float(msg["ACCDetObjLongtRltvSpdHSC2"])
                track.aRel = float("nan")
                track.measured = True

        # 4. 清理過期/逾時目標
        for t_id in list(self.pts.keys()):
            track = self.pts[t_id]
            if not track.updated_this_frame:
                track.stale_count += 1
                if track.stale_count > MAX_STALE_FRAMES:
                    del self.pts[t_id]

        # 5. 打包回傳給 openpilot
        ret = structs.RadarData()
        points = []
        for t_id, track in self.pts.items():
            pt = structs.RadarData.TrackPoint()
            pt.trackId = t_id
            pt.dRel = track.dRel
            pt.yRel = track.yRel
            pt.vRel = track.vRel
            pt.aRel = track.aRel
            pt.measured = track.measured
            points.append(pt)

        ret.points = points
        ret.errors = []

        return ret