import math
from opendbc.can.parser import CANParser
from opendbc.car import Bus, structs
from opendbc.car.interfaces import RadarInterfaceBase
from opendbc.car.mg.values import DBC

PROB_THRESHOLD = 0.2  # 存在機率低於 20% 視為無效[cite: 2]
MAX_STALE_FRAMES = 5  # 若連續 5 個雷達 Frame 沒更新該 ID，則主動剔除[cite: 2]


def get_can_parser(CP):
    messages = [
        ("RADAR_HSC2_FrP07", 20),
    ]
    return CANParser(DBC[CP.carFingerprint][Bus.pt], messages, 1)[cite: 2]


class TrackPointInternal:
    def __init__(self, track_id):
        self.track_id = track_id[cite: 2]
        self.dRel = 0.0[cite: 2]
        self.yRel = 0.0[cite: 2]
        self.vRel = 0.0[cite: 2]
        self.aRel = float("nan")[cite: 2]
        self.measured = True[cite: 2]
        self.updated_this_frame = False[cite: 2]
        self.stale_count = 0[cite: 2]


class RadarInterface(RadarInterfaceBase):
    def __init__(self, CP):
        super().__init__(CP)[cite: 2]

        self.radar_off = CP.radarUnavailable[cite: 2]
        if self.radar_off:
            return[cite: 2]

        self.pts = {}  # Dict[int, TrackPointInternal][cite: 2]
        self.rcp = get_can_parser(CP)[cite: 2]

    def update(self, can_strings) -> structs.RadarData | None:
        if self.radar_off:
            return structs.RadarData()[cite: 2]

        # 1. 讀取 CAN 數據
        vls = self.rcp.update_strings(can_strings)[cite: 2]

        # 若這批 can_strings 內沒有雷達訊息，直接返回 None
        if not vls:
            return None

        # 2. 重設當前 Frame 的更新標記
        for track in self.pts.values():
            track.updated_this_frame = False[cite: 2]

        # 3. 處理當前 CAN 封包帶來的所有 Target 更新/新增
        msgs = self.rcp.vl_all.get("RADAR_HSC2_FrP07", [])
        for msg in msgs:
            track_id = int(msg["ACCDetObjIdHSC2"])[cite: 2]
            exist_prob = msg["ACCDetObjExistPrbltyHSC2"][cite: 2]

            if exist_prob < PROB_THRESHOLD:
                if track_id in self.pts:
                    del self.pts[track_id][cite: 2]
            else:
                if track_id not in self.pts:
                    self.pts[track_id] = TrackPointInternal(track_id)[cite: 2]

                track = self.pts[track_id][cite: 2]
                track.updated_this_frame = True[cite: 2]
                track.stale_count = 0[cite: 2]

                track.dRel = float(msg["ACCDetObjLongtRltvDistHSC2"])[cite: 2]
                track.yRel = float(msg["ACCDetObjLatRltvDistHSC2"])[cite: 2]
                track.vRel = float(msg["ACCDetObjLongtRltvSpdHSC2"])[cite: 2]
                track.aRel = float("nan")[cite: 2]
                track.measured = True[cite: 2]

        # 4. 清理過期/逾時目標
        for t_id in list(self.pts.keys()):
            track = self.pts[t_id][cite: 2]
            if not track.updated_this_frame:
                track.stale_count += 1[cite: 2]
                if track.stale_count > MAX_STALE_FRAMES:
                    del self.pts[t_id][cite: 2]

        # 5. 打包回傳給 openpilot
        ret = structs.RadarData()[cite: 2]
        points = [][cite: 2]
        for t_id, track in self.pts.items():
            pt = structs.RadarData.TrackPoint()[cite: 2]
            pt.trackId = t_id[cite: 2]
            pt.dRel = track.dRel[cite: 2]
            pt.yRel = track.yRel[cite: 2]
            pt.vRel = track.vRel[cite: 2]
            pt.aRel = track.aRel[cite: 2]
            pt.measured = track.measured[cite: 2]
            points.append(pt)[cite: 2]

        ret.points = points[cite: 2]
        ret.errors = [][cite: 2]

        return ret