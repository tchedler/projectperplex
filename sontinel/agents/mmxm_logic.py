import pandas as pd
import numpy as np

class MMXMLogic:
    def __init__(self, symbol):
        self.symbol = symbol

    def get_model(self, df, time_data, smc_data, liq_data):
        if df is None or len(df) < 50: return None
        
        p = df['Close'].iloc[-1]
        midnight_open = self._get_midnight_open(df)
        
        amd = self._detect_amd(time_data, p, midnight_open, smc_data)
        turtle_soup = self._detect_turtle_soup(df, liq_data)
        sb_setup = self._detect_silver_bullet(time_data, smc_data)
        mmxm_phase = self._detect_mmxm_cycle(df, smc_data, liq_data)

        return {
            "midnight_open": midnight_open,
            "po3_phase": amd,
            "turtle_soup": turtle_soup,
            "silver_bullet": sb_setup,
            "mmxm_cycle": mmxm_phase
        }

    def _get_midnight_open(self, df):
        try:
            df_time = df.copy()
            midnight_candles = df_time.at_time('00:00')
            if not midnight_candles.empty:
                return midnight_candles['Open'].iloc[-1]
            return df['Open'].iloc[0]
        except:
            return df['Open'].iloc[0]

    def _detect_amd(self, time_data, current_p, mo, smc_data):
        """
        Bible §5.1 ENRICHI: PO3 détecté par position dans le range + momentum + timing.
        Valide pour TOUS les timeframes (y compris MN/W1/D1 sans killzone active).

        Logique:
        - ACCUMULATION = prix dans un range étroit, pas de displacement, zone neutre
        - MANIPULATION = prix sweepé un extrême (BSL ou SSL) sans displacement (Judas Swing)
        - DISTRIBUTION = après un MSS + displacement fort = vrai mouvement
        - EXPANSION = continuation du mouvement post-distribution
        """
        struct = smc_data['structure']['mode']
        kz = time_data['killzone']
        is_displaced = smc_data['displacement']['is_displaced']
        swh = smc_data['structure']['swh']
        swl = smc_data['structure']['swl']
        swing_range = swh - swl if swh != swl else 1

        # Position % dans le range (0% = bas, 100% = haut)
        pos_pct = (current_p - swl) / swing_range * 100

        # === PRIORITÉ 1: Session Asia = ACCUMULATION (toujours) ===
        if kz == "ASIA":
            return "ACCUMULATION"

        # === PRIORITÉ 2: MSS + Displacement confirmé = DISTRIBUTION/EXPANSION ===
        if is_displaced:
            if "MSS" in struct:
                return "DISTRIBUTION_ACTIVE"
            if "BOS" in struct or "EXPANSION" in struct:
                return "EXPANSION_PHASE"

        # === PRIORITÉ 3: Manipulation détectée par position extrême sans displacement ===
        # Prix dans le haut du range (> 85%) sans displacement = Judas Swing bullish (manipulation)
        if pos_pct > 85 and not is_displaced:
            if kz in ["LONDON", "NY_AM"] or time_data['macro'] != "NONE":
                return "MANIPULATION_HIGH_HUNT"

        # Prix dans le bas du range (< 15%) sans displacement = Judas Swing bearish (manipulation)
        if pos_pct < 15 and not is_displaced:
            if kz in ["LONDON", "NY_AM"] or time_data['macro'] != "NONE":
                return "MANIPULATION_LOW_HUNT"

        # === PRIORITÉ 4: Killzone active + position intermédiaire ===
        if kz in ["LONDON", "NY_AM", "NY_PM"]:
            if not is_displaced:
                # Position dans le range intermédiaire = accumulation pré-move
                if 30 <= pos_pct <= 70:
                    return "ACCUMULATION"
                elif pos_pct > 70:
                    return "MANIPULATION_HIGH_HUNT"
                else:
                    return "MANIPULATION_LOW_HUNT"
            else:
                if time_data['macro'] != "NONE":
                    return "DISTRIBUTION_ACTIVE"
                return "EXPANSION_PHASE"

        # === PRIORITÉ 5: Hors session — analyse par structure seule ===
        if kz == "NONE":
            if "EXPANSION" in struct and is_displaced:
                return "EXPANSION_PHASE"
            # Range étroit sans displacement = ACCUMULATION (HTF typique MN/W1)
            if not is_displaced and 25 <= pos_pct <= 75:
                return "ACCUMULATION"
            # Position extrême sans displacement = MANIPULATION probable
            if pos_pct > 80 and not is_displaced:
                return "MANIPULATION_HIGH_HUNT"
            if pos_pct < 20 and not is_displaced:
                return "MANIPULATION_LOW_HUNT"
            return "CONSOLIDATION"

        return "CONSOLIDATION"

    def _detect_turtle_soup(self, df, liq):
        """
        Bible §3: SFP = mèche casse le High/Low MAIS Close revient en dessous/dessus
        Scan les 3 dernières bougies pour un signal récent
        """
        erl_h = liq['erl']['high']
        erl_l = liq['erl']['low']
        
        for i in range(-1, -4, -1):
            try:
                h_peak = df['High'].iloc[i]
                l_pit = df['Low'].iloc[i]
                close = df['Close'].iloc[i]
                
                if h_peak > erl_h * 0.9999 and close < erl_h:
                    return "BEARISH_TURTLE_SOUP"
                if l_pit < erl_l * 1.0001 and close > erl_l:
                    return "BULLISH_TURTLE_SOUP"
            except:
                continue
        return "NONE"

    def _detect_silver_bullet(self, time, smc):
        """
        Bible §Strategy Triggers CORRIGÉ: SB requiert MSS + Displacement + FVG
        """
        if time['silver_bullet'] == "NONE": return "INACTIVE"
        
        has_fvg = len(smc['fvgs']) > 0
        has_displacement = smc['displacement']['is_displaced']
        has_mss = "MSS" in smc['structure']['mode']  # AJOUTÉ: MSS requis
        has_bos = "BOS" in smc['structure']['mode'] or "EXPANSION" in smc['structure']['mode']
        
        if has_fvg and has_displacement and has_mss:
            struct = smc['structure']['mode']
            if "BULL" in struct: return "SB_BUY_CONFIRMED"
            if "BEAR" in struct: return "SB_SELL_CONFIRMED"
        
        if has_fvg and has_displacement and has_bos:
            return "SB_WATCH"  # BOS sans MSS = Watch seulement
        
        return "SCANNING_SB"

    def _detect_mmxm_cycle(self, df, smc, liq):
        """
        Bible §13 CORRIGÉ: MMXM basé sur position prix vs ERL + structure
        Consolidation → Manipulation → CHoCH → MSS → Expansion → Retracement → DOL
        """
        struct = smc['structure']['mode']
        p = df['Close'].iloc[-1]
        erl_h = liq['erl']['high']
        erl_l = liq['erl']['low']
        is_displaced = smc['displacement']['is_displaced']
        
        # Calcul de la position relative dans le range
        erl_range = erl_h - erl_l if erl_h != erl_l else 1
        position_pct = (p - erl_l) / erl_range * 100
        
        # Phase 1: Près des extrêmes (< 10% ou > 90%) = Peak possible
        if position_pct > 95:
            if not is_displaced:
                return "MMSM_PEAK_DISTRIBUTION"  # Near high, weakening
            else:
                return "MMSM_EXPANSION_HIGH"
        
        if position_pct < 5:
            if not is_displaced:
                return "MMBM_PEAK_ACCUMULATION"  # Near low, building
            else:
                return "MMBM_EXPANSION_LOW"
        
        # Phase 2: MSS/BOS detected with displacement = Active expansion
        if "MSS" in struct and is_displaced:
            if "BULL" in struct:
                return "MMBM_EXPANSION_ACTIVE"
            else:
                return "MMSM_EXPANSION_ACTIVE"
        
        # Phase 3: BOS without displacement = early trend
        if "BOS" in struct:
            return "TREND_FOLLOWING"
        
        # Phase 4: Expansion without structure break
        if "EXPANSION" in struct:
            return "TREND_FOLLOWING"
        
        # Default: consolidation / range
        return "CONSOLIDATION_RANGE"