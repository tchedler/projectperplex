"""
pa_checklist_expert.py — Expert Juge Price Action
==================================================
Reçoit les features PA (de PAFeatureExtractor) et note le setup sur 100 points
selon la Bible Ultime du Price Action (Chapitres 1 à 8).

Ce module est INDÉPENDANT du code ICT. Il ne connaît rien des FVG, OB ou Sweep.
"""


class PAChecklistExpert:
    """
    Génère une checklist PA complète avec score sur 100, verdict, direction et narratif HTML.
    """

    # ──────────────────────────────────────────────────────────────────────
    # Seuils de verdicts
    SCORE_EXECUTE = 80   # Seuil exécution directe
    SCORE_WATCH   = 65   # Seuil "Regarder / Sniper"

    def generate(self, tf: str, pa_features: dict, score_execute: int = 80, score_limit: int = 65) -> tuple:
        """
        Point d'entrée principal.
        Retourne (html_checklist, score, verdict, direction).
        """
        self.SCORE_EXECUTE = score_execute
        self.SCORE_WATCH   = score_limit

        cycle        = pa_features.get("cycle", {})
        ema_pos      = pa_features.get("ema_position", {})
        bar_count    = pa_features.get("bar_count", {})
        last_signal  = pa_features.get("last_signal", {})
        microchannel = pa_features.get("microchannel", {})
        patterns     = pa_features.get("patterns", {})
        mm           = pa_features.get("measured_move", {})
        rsi          = pa_features.get("rsi", {})
        volume       = pa_features.get("volume", {})

        # === 1. BLOCAGES ABSOLUS (annulent tout setup) ===
        hard_blocker = self._check_hard_blockers(cycle, microchannel, last_signal)

        # === 2. CALCUL DU SCORE ===
        score, detail = self._calculate_score(cycle, ema_pos, bar_count, last_signal, microchannel, patterns, mm, rsi, volume)

        # Appliquer les blocages
        if hard_blocker["blocked"]:
            score = min(score, 20)

        score = max(0, min(100, score))

        # === 3. DIRECTION PROBABLE ===
        direction = self._determine_direction(cycle, bar_count, last_signal, ema_pos)

        # === 4. VERDICT ===
        verdict = self._get_verdict(score, hard_blocker)

        # === 5. GÉNÉRATION HTML ===
        html = self._render_html(tf, score, verdict, direction, cycle, ema_pos,
                                  bar_count, last_signal, microchannel, patterns, mm,
                                  detail, hard_blocker, rsi, volume)

        return html, score, verdict, direction

    # ══════════════════════════════════════════════════════════════════════
    # BLOCAGES ABSOLUS (Chapitre 6 & 7 — Bible PA)
    # ══════════════════════════════════════════════════════════════════════
    def _check_hard_blockers(self, cycle: dict, microchannel: dict, last_signal: dict) -> dict:
        blocker_msgs = []

        # Règle 1 : Micro-canal actif dans la direction opposée
        if microchannel.get("danger"):
            blocker_msgs.append("⛔ Micro-Canal Baissier actif — Ne pas acheter le premier pullback")

        # Règle 2 : Tight Trading Range = interdiction totale
        if cycle.get("tight_range"):
            blocker_msgs.append("⛔ TIGHT TRADING RANGE — Interdiction de trader (Barb Wire)")

        # Règle 3 : Doji seul sans confirmation
        if last_signal.get("bar_type") == "doji" and last_signal.get("quality") == "NEUTRE":
            blocker_msgs.append("⚠️ Doji sans confirmation — Signal trop faible")

        return {
            "blocked": len(blocker_msgs) > 0,
            "messages": blocker_msgs,
        }

    # ══════════════════════════════════════════════════════════════════════
    # CALCUL DU SCORE (Barème Bible PA — /100)
    # ══════════════════════════════════════════════════════════════════════
    def _calculate_score(self, cycle, ema_pos, bar_count, last_signal, microchannel, patterns, mm, rsi=None, volume=None) -> tuple:
        detail = {}
        score = 0
        if rsi is None: rsi = {}
        if volume is None: volume = {}

        # ── CRITÈRE 1 : Cycle / Contexte (Chapitre 1) — /20 points ──
        cycle_type = cycle.get("type", "UNKNOWN")
        if cycle_type in ("BULL_CANAL", "BEAR_CANAL"):
            c1 = 20
            detail["cycle"] = (c1, "Canal directionnel clair (Always-In)")
        elif cycle_type in ("BREAKOUT_BULL", "BREAKOUT_BEAR"):
            c1 = 20
            detail["cycle"] = (c1, "Breakout fort — inertie maximale")
        elif cycle_type == "TRADING_RANGE":
            c1 = 10
            detail["cycle"] = (c1, "Trading Range — Scalping uniquement")
        elif cycle_type == "TIGHT_RANGE":
            c1 = 0
            detail["cycle"] = (c1, "Tight Range — ZONE INTERDITE (Barb Wire)")
        else:
            c1 = 5
            detail["cycle"] = (c1, "Contexte incertain")
        score += c1

        # ── CRITÈRE 2 : Force de la Signal Bar (Chapitre 2) — /20 points ──
        sig_quality = last_signal.get("quality", "FAIBLE")
        body_gap    = last_signal.get("body_gap", False)
        if sig_quality == "FORTE":
            c2 = 20
            detail["signal_bar"] = (c2, "Signal Bar puissante — Reversal Bar / Pin Bar")
        elif sig_quality == "MODÉRÉE":
            c2 = 12
            detail["signal_bar"] = (c2, "Trend Bar — Force modérée")
        elif sig_quality == "COMPRESSION":
            c2 = 8
            detail["signal_bar"] = (c2, "Inside Bar — Compression (attendre cassure)")
        else:
            c2 = 0
            detail["signal_bar"] = (c2, "Doji ou Signal trop faible")
        if body_gap:
            c2 = min(c2 + 5, 20)
            detail["signal_bar"] = (c2, detail["signal_bar"][1] + " + Body Gap confirmé")
        score += c2

        # ── CRITÈRE 3 : Qualité du Setup / Bar Count (Chapitre 3) — /30 points ──
        h_count = bar_count.get("h_count", 0)
        l_count = bar_count.get("l_count", 0)
        b_setup = bar_count.get("bullish_setup")
        s_setup = bar_count.get("bearish_setup")
        best_count = max(h_count, l_count)

        if best_count == 2:
            c3 = 30
            label = b_setup or s_setup
            detail["setup"] = (c3, f"Setup {label} — Deuxième tentative (Haute Probabilité)")
        elif best_count == 1:
            c3 = 10
            label = b_setup or s_setup
            detail["setup"] = (c3, f"Setup {label} — Première tentative (Prudence)")
        elif best_count >= 3:
            c3 = 15
            detail["setup"] = (c3, "3ème tentative+ — Risque d'exhaustion (Pénalité)")
        else:
            c3 = 5
            detail["setup"] = (c3, "Pas de pullback identifié — Contexte ambigu")
        score += c3

        # ── CRITÈRE 4 : Validation EMA 20 (Chapitre 3) — /15 points ──
        ema_touch = ema_pos.get("ema_touch_last3", False)
        pct_from  = abs(ema_pos.get("pct_from_ema", 999))

        if ema_touch:
            c4 = 15
            detail["ema20"] = (c4, "Toucher / Rejet de l'EMA 20 — Signal de Pullback validé")
        elif pct_from < 0.05:
            c4 = 10
            detail["ema20"] = (c4, "Prix proche de l'EMA 20 (< 0.05%)")
        elif pct_from < 0.2:
            c4 = 5
            detail["ema20"] = (c4, "Prix modérément distant de l'EMA 20")
        else:
            c4 = 0
            detail["ema20"] = (c4, "Prix loin de l'EMA 20 — Prudence (Trade contraire à la moyenne)")
        score += c4

        # ── CRITÈRE 5 : Filtres Danger, Micro-Structures & Patterns (Ch. 6,7,8) — /15 points ──
        pts_detected = patterns.get("detected", [])
        mc_active    = microchannel.get("active", False)

        c5 = 0
        if "DOUBLE_BOTTOM" in pts_detected or "DOUBLE_TOP" in pts_detected:
            c5 = 15
            detail["patterns"] = (c5, f"Pattern classique détecté : {pts_detected}")
        elif "BULL_FLAG" in pts_detected:
            c5 = 12
            detail["patterns"] = (c5, "Bull Flag — Continuation probable")
        elif "SYMMETRIC_TRIANGLE" in pts_detected:
            c5 = 8
            detail["patterns"] = (c5, "Triangle Symétrique — Breakout imminent (Direction inconnue)")
        elif mc_active and not microchannel.get("danger"):
            c5 = 12
            detail["patterns"] = (c5, "Micro-Canal confirme la tendance")
        else:
            c5 = 5
            detail["patterns"] = (c5, "Aucun pattern majeur — Micro-structures absentes")

        if microchannel.get("danger"):
            c5 = max(0, c5 - 10)
            detail["patterns"] = (c5, "⛔ Micro-Canal Baissier actif — Pénalité danger")

        score += c5

        # ── BONUS RSI (0 à +10 pts) ──
        rsi_val      = rsi.get("value", 50)
        rsi_bias     = rsi.get("bias", "NEUTRE")
        bull_div     = rsi.get("bull_divergence", False)
        bear_div     = rsi.get("bear_divergence", False)
        overbought   = rsi.get("overbought", False)
        oversold     = rsi.get("oversold", False)

        c_rsi = 0
        if bull_div:
            c_rsi = 10
            detail["rsi"] = (c_rsi, f"Divergence Haussière (RSI {rsi_val}) — Signal fort")
        elif bear_div:
            c_rsi = 10
            detail["rsi"] = (c_rsi, f"Divergence Baissière (RSI {rsi_val}) — Signal fort")
        elif overbought:
            c_rsi = 0
            detail["rsi"] = (c_rsi, f"RSI {rsi_val} — Zone Surchauffe (Prudence)")
        elif oversold:
            c_rsi = 0
            detail["rsi"] = (c_rsi, f"RSI {rsi_val} — Zone Survente (Rebond possible)")
        elif rsi_bias == "BULL" and rsi_val > 55:
            c_rsi = 6
            detail["rsi"] = (c_rsi, f"RSI {rsi_val} — Biais Haussier confirmé (> 50)")
        elif rsi_bias == "BEAR" and rsi_val < 45:
            c_rsi = 6
            detail["rsi"] = (c_rsi, f"RSI {rsi_val} — Biais Baissier confirmé (< 50)")
        else:
            c_rsi = 3
            detail["rsi"] = (c_rsi, f"RSI {rsi_val} — Zone neutre (45-55)")
        score += c_rsi

        # ── BONUS VOLUME (0 à +15 pts) ──
        c_vol = 0
        if volume.get("available"):
            vol_label      = volume.get("label", "NORMAL")
            sig_high_vol   = volume.get("sig_bar_high_vol", False)
            brkout_low_vol = volume.get("breakout_low_vol", False)
            pb_healthy     = volume.get("pullback_healthy", False)
            climax         = volume.get("climax", False)
            vol_ratio      = volume.get("vol_ratio", 1.0)

            if climax:
                c_vol = 0
                detail["volume"] = (c_vol, f"CLIMAX Volume (x{vol_ratio}) — Épuisement probable")
            elif sig_high_vol:
                c_vol = 15
                detail["volume"] = (c_vol, f"Volume {vol_label} sur Signal Bar — Confirmation puissante")
            elif brkout_low_vol:
                c_vol = 0
                detail["volume"] = (c_vol, f"Volume Faible sur Breakout (x{vol_ratio}) — Faux Breakout ?")
            elif pb_healthy:
                c_vol = 10
                detail["volume"] = (c_vol, "Volume décroissant sur Pullback — Tendance saine")
            elif vol_label == "ÉLEVÉ":
                c_vol = 8
                detail["volume"] = (c_vol, f"Volume Élevé (x{vol_ratio}) — Intérêt institutionnel")
            elif vol_label == "FAIBLE":
                c_vol = 2
                detail["volume"] = (c_vol, f"Volume Faible (x{vol_ratio}) — Méfiance")
            else:
                c_vol = 5
                detail["volume"] = (c_vol, f"Volume Normal (x{vol_ratio})")
        else:
            detail["volume"] = (0, "Volume indisponible")
        score += c_vol

        return score, detail

    # ══════════════════════════════════════════════════════════════════════
    # DIRECTION PROBABLE
    # ══════════════════════════════════════════════════════════════════════
    def _determine_direction(self, cycle, bar_count, last_signal, ema_pos) -> str:
        ctype = cycle.get("type", "")
        sig_dir = last_signal.get("direction")
        above   = ema_pos.get("above_ema")

        if sig_dir in ("BUY", "SELL"):
            return sig_dir

        if ctype in ("BULL_CANAL", "BREAKOUT_BULL"):
            return "BUY"
        if ctype in ("BEAR_CANAL", "BREAKOUT_BEAR"):
            return "SELL"
        if above is True:
            return "BUY"
        if above is False:
            return "SELL"
        return "NEUTRE"

    # ══════════════════════════════════════════════════════════════════════
    # VERDICT FINAL
    # ══════════════════════════════════════════════════════════════════════
    def _get_verdict(self, score: int, hard_blocker: dict) -> str:
        if hard_blocker.get("blocked"):
            return "INTERDIT (Bloquer PA)"
        if score >= self.SCORE_EXECUTE:
            return "EXÉCUTION A+"
        if score >= self.SCORE_WATCH:
            return "REGARDER / SNIPER"
        return "INTERDIT (Score Faible)"

    # ══════════════════════════════════════════════════════════════════════
    # RENDU HTML (Même style que ChecklistExpert ICT)
    # ══════════════════════════════════════════════════════════════════════
    def _render_html(self, tf, score, verdict, direction,
                     cycle, ema_pos, bar_count, last_signal,
                     microchannel, patterns, mm, detail, hard_blocker,
                     rsi=None, volume=None) -> str:
        dir_icon  = "🟢 BUY" if direction == "BUY" else ("🔴 SELL" if direction == "SELL" else "⬜ NEUTRE")
        ver_color = "#00ff88" if "EXÉCUTION" in verdict else ("#f0b429" if "SNIPER" in verdict else "#ef5350")

        out = f"<h2 style='text-align:center; color:#d4a017;'>📊 {tf} — ANALYSE PRICE ACTION</h2>\n"

        # En-tête Cycle + Direction
        cycle_type = cycle.get("type", "?")
        out += (
            f"<div style='background:rgba(212,160,23,0.1); border:1px solid #d4a01733; "
            f"border-radius:8px; padding:10px 16px; margin-bottom:14px;'>"
            f"<b>Cycle :</b> <span style='color:#f0b429'>{cycle_type}</span>"
            f" &nbsp;|&nbsp; <b>Direction :</b> {dir_icon}"
            f"</div>"
        )

        # Blocages absolus
        if hard_blocker.get("messages"):
            for msg in hard_blocker["messages"]:
                out += f"<div style='background:#ef535015;color:#ef5350;border-radius:6px;padding:8px 12px;margin:4px 0;'>{msg}</div>\n"

        # Critères détaillés
        out += "<table style='width:100%;border-collapse:collapse;font-size:0.82rem;'>\n"
        out += "<tr style='color:#848e9c;'><th style='text-align:left;padding:4px 8px;'>Critère</th><th style='text-align:center;'>Pts</th><th style='text-align:left;padding:4px 8px;'>Détail</th></tr>\n"

        criteria_map = {
            "cycle":      ("Cycle (Ch.1)",           "/20"),
            "signal_bar": ("Signal Bar (Ch.2)",       "/20"),
            "setup":      ("Setup H/L Count (Ch.3)",  "/30"),
            "ema20":      ("EMA 20 Ligne de Vie (Ch.3)", "/15"),
            "patterns":   ("Patterns & Micro-struct (Ch.7,8)", "/15"),
            "rsi":        ("RSI 14 + Divergences (Bonus)", "/+10"),
            "volume":     ("Volume Tick + Confirmation (Bonus)", "/+15"),
        }

        for key, (label, max_pts) in criteria_map.items():
            if key in detail:
                pts, txt = detail[key]
                color = "#00ff88" if pts >= int(max_pts[1:]) * 0.8 else ("#f0b429" if pts > 0 else "#ef5350")
                icon  = "✅" if pts >= int(max_pts[1:]) * 0.8 else ("🟡" if pts > 0 else "❌")
                out += (
                    f"<tr style='border-bottom:1px solid #ffffff08;'>"
                    f"<td style='padding:5px 8px; color:#d4d4d4;'>{icon} {label}</td>"
                    f"<td style='text-align:center; color:{color}; font-weight:700;'>{pts}{max_pts}</td>"
                    f"<td style='padding:5px 8px; color:#848e9c;'>{txt}</td>"
                    f"</tr>\n"
                )

        out += "</table>\n"

        # Measured Move
        if mm.get("valid"):
            out += (
                f"<div style='margin-top:10px; padding:8px 14px; background:rgba(255,255,255,0.03); "
                f"border-radius:8px; font-size:0.8rem; color:#848e9c;'>"
                f"🎯 <b>Measured Move :</b> "
                f"Bull Target → <b style='color:#00ff88'>{mm.get('mm_bull_target','?')}</b> &nbsp;|&nbsp;"
                f"Bear Target → <b style='color:#ef5350'>{mm.get('mm_bear_target','?')}</b>"
                f" (Leg1 = {mm.get('leg1_size','?')} pts)"
                f"</div>\n"
            )

        # Score Final + Verdict
        out += (
            f"<hr style='border:1px solid #2a2e39;margin:12px 0;'>"
            f"<div style='text-align:center;'>"
            f"<span style='font-size:1.5rem; font-weight:900; color:{ver_color};'>{score}/100</span>"
            f"<br><span style='font-size:0.9rem; color:{ver_color}; letter-spacing:1px;'>{verdict}</span>"
            f"</div>"
        )

        return out
