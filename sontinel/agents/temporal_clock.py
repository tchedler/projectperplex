import datetime
import pytz

class TemporalClock:
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.tz = pytz.timezone('America/New_York')

    def get_audit(self):
        now = datetime.datetime.now(self.tz)
        h = now.hour
        m = now.minute
        day = now.weekday()
        time_str = now.strftime("%H:%M")
        minutes_total = h * 60 + m

        # ============================================================
        # KILLZONES — Bible §4 (heures exactes UTC/EST)
        # ============================================================
        kz = "NONE"
        if 20 <= h or h < 2:   kz = "ASIA"
        elif 2 <= h < 5:        kz = "LONDON"
        elif 5 <= h < 7:        kz = "LONDON_PM"
        elif 7 <= h < 10:       kz = "NY_AM"
        elif 10 <= h < 12:      kz = "NY_LUNCH"
        elif 13 <= h < 16:      kz = "NY_PM"

        # ============================================================
        # SILVER BULLET WINDOWS — Bible §4 (3 fenêtres exactes)
        # ============================================================
        sb = "NONE"
        if 3 <= h < 4:     sb = "LONDON_SB"
        elif 10 <= h < 11: sb = "NY_AM_SB"
        elif 14 <= h < 15: sb = "NY_PM_SB"

        # ============================================================
        # 12 MACROS ALGORITHMIQUES COMPLÈTES — Bible §4
        # ============================================================
        macro = "NONE"
        macros = [
            (1430, 1440, "MIDNIGHT_OPEN_MACRO"),  # 23:50-00:00
            (0,    10,   "MIDNIGHT_OPEN_MACRO"),  # 00:00-00:10
            (110,  130,  "LONDON_OPEN_MACRO"),    # 01:50-02:10
            (243,  263,  "LONDON_AM_MACRO_1"),    # 04:03-04:23
            (313,  333,  "LONDON_AM_MACRO_2"),    # 05:13-05:33
            (470,  490,  "NY_OPEN_MACRO"),        # 07:50-08:10
            (530,  550,  "NY_AM_MACRO_1"),        # 08:50-09:10
            (590,  610,  "NY_AM_MACRO_2"),        # 09:50-10:10
            (650,  670,  "NY_AM_MACRO_3"),        # 10:50-11:10
            (710,  730,  "NY_LUNCH_MACRO"),       # 11:50-12:10
            (790,  810,  "NY_PM_MACRO_1"),        # 13:10-13:30
            (890,  910,  "NY_PM_MACRO_2"),        # 14:50-15:10
            (915,  945,  "NY_CLOSE_MACRO"),       # 15:15-15:45
        ]

        for start, end, name in macros:
            if start <= minutes_total <= end:
                macro = name
                break

        day_name = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI", "DIMANCHE"][day]

        # ============================================================
        # OVR-1 : Configuration dynamique pour les actifs 24/7 (Cryptos)
        # ============================================================
        disable_killzone = self.config.get("disable_killzone_check", False)

        friday_no_trade = False if disable_killzone else (day == 4 and h >= 14)
        in_cbdr_window = (14 <= h < 20)

        if disable_killzone:
            # Active le trading 24h/24 sans bloquer sur les zones ICT
            is_tradable = True
            is_high_prob = True
        else:
            is_tradable = (kz != "NONE" or macro != "NONE") and not friday_no_trade
            is_high_prob = macro != "NONE" or sb != "NONE"

        return {
            "ny_time": time_str,
            "day": day_name,
            "weekday_num": day,
            "killzone": kz,
            "silver_bullet": sb,
            "macro": macro,
            "is_tradable": is_tradable,
            "is_high_prob": is_high_prob,
            "friday_no_trade": friday_no_trade,
            "in_cbdr_window": in_cbdr_window,
            "minutes_total": minutes_total,
        }
