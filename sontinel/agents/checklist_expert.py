import pandas as pd

class ChecklistExpert:
    def __init__(self):
        pass

    def generate(self, tf, smc, liq, bias, exe, mmxm, clock, score_execute=80, score_limit=65):
        """
        Génère une checklist complète et fractale basée sur la Bible ICT.
        Chaque timeframe est traité INDÉPENDAMMENT.
        Retourne (html_checklist, score, verdict).
        """
        score = self._calculate_score_v4(smc, liq, bias, exe, mmxm, clock)
        verdict = self._get_verdict(score, score_execute, score_limit)

        # Calcul du biais local propre au TF (indépendant du biais HTF global)
        local_bias = self._compute_local_bias(smc, exe, mmxm)

        output = f"<h2 style='text-align:center; color:#2962ff;'>📋 {tf} MAÎTRISE</h2>\n"

        # MODULE 0: EN-TÊTE TF — BIAIS LOCAL + TENDANCE + PHASE PO3
        output += self._mod0_tf_header(tf, local_bias, bias, mmxm, smc)

        # MODULE 1: NARRATIF & BIAIS + AMD + STATE OF DELIVERY + IPDA
        output += self._mod1_narrative_bias(tf, bias, mmxm, clock)

        # MODULE 2: STRUCTURE DU PRIX + ANTI-INDUCEMENT (Sweep ERL vérifié)
        output += self._mod2_structure(tf, smc, mmxm, liq)

        # MODULE 3: LIQUIDITÉ EXTERNE (ERL) + SWEEP STATUS
        output += self._mod3_external_liquidity(tf, liq, bias)

        # MODULE 4: ZONES IRL (FVG FRESH détaillés + OB non retestés détaillés)
        output += self._mod4_internal_zones(tf, smc, liq)

        # MODULE 5: PREMIUM / DISCOUNT / OTE
        output += self._mod5_pricing(tf, exe)

        # MODULE 6: TIME & MACRO (Killzone + Silver Bullet + CBDR)
        output += self._mod6_time_macro(tf, clock, mmxm)

        # MODULE 7: SETUPS DÉTECTÉS (Silver Bullet / Grail / Unicorn)
        output += self._mod7_setups(tf, smc, liq, mmxm, clock, exe)

        # SCORE FINAL
        output += f"\n<hr style='border:1px solid #2a2e39'>\n"
        output += f"<p style='text-align:center; font-size:0.85rem;'>⚪ TOTAL {score}/100</p>"

        return output, score, verdict

    # =====================================================
    # MODULE 0 : EN-TÊTE TF — BIAIS LOCAL + TENDANCE + PO3
    # Bible §14.4: Chaque TF doit avoir son propre narrative
    # =====================================================
    def _compute_local_bias(self, smc, exe, mmxm):
        """Calcule le biais local propre au timeframe analysé."""
        mode = smc['structure']['mode']
        eq_pct = exe['equilibrium']['percent']
        po3 = mmxm['po3_phase']

        if 'MSS_BULL' in mode or 'BOS_BULL' in mode or 'EXPANSION_BULL' in mode:
            return 'BULLISH'
        elif 'MSS_BEAR' in mode or 'BOS_BEAR' in mode or 'EXPANSION_BEAR' in mode:
            return 'BEARISH'
        # Fallback: position dans le range
        if eq_pct < 40:
            return 'BULLISH_TENTATIVE'
        elif eq_pct > 60:
            return 'BEARISH_TENTATIVE'
        return 'NEUTRAL'

    def _mod0_tf_header(self, tf, local_bias, bias, mmxm, smc):
        """
        En-tête unique par TF : biais local + tendance + phase PO3 + alignement HTF.
        Bible §14.4 + §12 (Checklist Step 0 + Step 2).
        """
        htf_bias = bias['htf_bias']
        po3 = mmxm['po3_phase']
        mode = smc['structure']['mode']

        # Couleur biais local
        if 'BULL' in local_bias:
            lc = '#00ff88'
            trend_icon = '🟢 HAUSSIER'
        elif 'BEAR' in local_bias:
            lc = '#ef5350'
            trend_icon = '🔴 BAISSIER'
        else:
            lc = '#848e9c'
            trend_icon = '⚪ NEUTRE'

        # Alignement avec HTF
        aligned = (('BULL' in local_bias and 'BULL' in htf_bias) or
                   ('BEAR' in local_bias and 'BEAR' in htf_bias))
        align_icon = '✅ ALIGNÉ HTF' if aligned else '⚠️ CONTRE-TENDANCE HTF'

        r = f"<div style='background:rgba(41,98,255,0.08); border:1px solid rgba(41,98,255,0.3); border-radius:8px; padding:10px; margin-bottom:10px;'>"
        r += f"<b style='font-size:1.0rem;'>📡 BIAIS LOCAL {tf}</b><br>"
        r += f"<b style='color:{lc}; font-size:1.4rem;'>{trend_icon}</b><br>"
        r += f"<span style='font-size:0.85rem; color:#848e9c;'>Structure: <code>{mode}</code></span><br>"
        r += f"<span style='font-size:0.85rem;'>Phase PO3 : <b>{po3}</b></span><br>"
        r += f"<span style='font-size:0.8rem; color:{'#00ff88' if aligned else '#f0b429'};'>{align_icon} ({htf_bias})</span>"
        r += "</div>"
        return r

    # =====================================================
    # MODULE 1 : NARRATIF & BIAIS (AMD + State of Delivery + IPDA)
    # Bible §1.2 (IPDA 20/40/60j) + §5.1 (PO3 Weekly/Daily)
    # =====================================================
    def _mod1_narrative_bias(self, tf, bias, mmxm, clock):
        htf = bias['htf_bias']
        mo = mmxm['midnight_open']
        po3 = mmxm['po3_phase']
        cycle = mmxm['mmxm_cycle']
        ipda = bias.get('ipda_ranges', {})
        day = clock.get('day', 'NONE') # FIX : Récupérer 'day' depuis clock

        # State of Delivery (ACCUM/MANIP/DISTRIB/RE-ACCUM)
        sod = self._detect_state_of_delivery(po3, cycle)

        # AMD Weekly
        # M1 FIX : AMD Weekly basé sur les statistiques ICT réelles
        # Lundi : Accumulation (setup range)
        # Mardi ou Mercredi : Manipulation (High/Low de semaine formé dans 62-73% des cas)
        # Jeudi/Vendredi : Distribution (continuation du vrai move)
        if day == "LUNDI":
            amd_weekly = "ACCUMULATION (Lundi) — Préparer le biais"
        elif day == "MARDI":
            amd_weekly = "MANIPULATION (Mardi) — H/L Weekly probable (statistique ICT : 62-73%)"
        elif day == "MERCREDI":
            amd_weekly = "MANIPULATION ou DISTRIBUTION (Mercredi) — Pivot critique (H/L possible 27-38%)"
        elif day in ["JEUDI", "VENDREDI"]:
            amd_weekly = "DISTRIBUTION (Jeu/Ven) — Continuation momentum (statistique: 65%)"
        else:
            amd_weekly = "REPOS (Weekend)"

        r = f"<b>📅 MODULE 1 : NARRATIF & BIAIS</b><br>"
        r += f"{'🟢' if htf != 'NEUTRAL' else '🔴'} Biais HTF : <code>{htf}</code><br>"
        r += f"{'🟢' if 'MANIPULATION' in po3 or 'DISTRIBUTION' in po3 else '🔴'} PO3 Daily : {po3}<br>"
        r += f"📊 AMD Weekly : <code>{amd_weekly}</code><br>"
        r += f"🔄 State of Delivery : <code>{sod}</code><br>"
        r += f"{'🟢' if cycle != 'TREND_FOLLOWING' else '🟡'} MMXM : {cycle}<br>"
        r += f"⚪ Midnight Open : {mo:.2f}<br>"

        # IPDA 20/40/60 jours — Bible §1.2
        if ipda:
            r20 = ipda.get('r20', {})
            r40 = ipda.get('r40', {})
            r60 = ipda.get('r60', {})
            r += f"<br><b style='font-size:0.8rem; color:#848e9c;'>📐 IPDA RANGES :</b><br>"
            if r20:
                r += f"<span style='font-size:0.8rem;'>20j H: <code>{r20.get('high', 0):.2f}</code> L: <code>{r20.get('low', 0):.2f}</code></span><br>"
            if r40:
                r += f"<span style='font-size:0.8rem;'>40j H: <code>{r40.get('high', 0):.2f}</code> L: <code>{r40.get('low', 0):.2f}</code></span><br>"
            if r60:
                r += f"<span style='font-size:0.8rem;'>60j H: <code>{r60.get('high', 0):.2f}</code> L: <code>{r60.get('low', 0):.2f}</code></span><br>"

        r += "<br>"
        return r  # Midnight Open déjà affiché ligne 143 — suppression doublon (#12)

    def _detect_state_of_delivery(self, po3, cycle):
        if "ACCUMULATION" in po3: return "ACCUMULATION"
        if "MANIPULATION" in po3: return "MANIPULATION"
        if "DISTRIBUTION" in po3 or "EXPANSION" in po3: return "DISTRIBUTION"
        if cycle == "MMBM_PEAK_ACCUMULATION" or cycle == "MMSM_PEAK_DISTRIBUTION": return "RE-ACCUMULATION"
        return "UNKNOWN"

    # =====================================================
    # MODULE 2 : STRUCTURE + ANTI-INDUCEMENT (Sweep ERL vérifié)
    # Bible §18.2 (Sweep ERL AVANT MSS = rule) + §6.2
    # =====================================================
    def _mod2_structure(self, tf, smc, mmxm, liq):
        mode = smc['structure']['mode']
        disp = smc['displacement']
        ts = mmxm['turtle_soup']
        swh = smc['structure']['swh']
        swl = smc['structure']['swl']

        has_mss = "MSS" in mode
        has_bos = "BOS" in mode

        # Anti-Inducement — Bible §18.2 + §18.4:
        # Un MSS est valide SEULEMENT si un Sweep ERL (BSL ou SSL) l'a précédé.
        # On vérifie: le prix a-t-il approché le BSL ou SSL avant le MSS ?
        erl_h = liq['erl']['high']
        erl_l = liq['erl']['low']
        erl_range = erl_h - erl_l if erl_h != erl_l else 1

        # Proximité du sweep: le SWH ou SWL doit être proche de l'extrême de range
        swh_near_erl = abs(swh - erl_h) / erl_range < 0.05  # SWH dans 5% du BSL = sweep probable
        swl_near_erl = abs(swl - erl_l) / erl_range < 0.05  # SWL dans 5% du SSL = sweep probable
        sweep_occurred = swh_near_erl or swl_near_erl

        # Anti-Inducement: MSS valide = sweep ERL + displacement
        if has_mss and disp['is_displaced'] and sweep_occurred:
            anti_induce = "✅ VALIDÉ (Sweep ERL confirmé)"
        elif has_mss and disp['is_displaced'] and not sweep_occurred:
            anti_induce = "⚠️ INDUCEMENT POSSIBLE (pas de sweep ERL clair)"
        elif has_bos and not has_mss:
            anti_induce = "⚠️ CHoCH/BOS sans MSS — Attendre confirmation"
        else:
            anti_induce = "🔴 NON CONFIRMÉ"

        # CHoCH vs BOS distinction — Bible §6.2
        struct_quality = ""
        if "MSS" in mode:
            struct_quality = " (Changement de camp confirmé)"
        elif "BOS" in mode:
            struct_quality = " (Continuation — pas d'entrée seul)"
        elif "EXPANSION" in mode:
            struct_quality = " (Momentum sans structure cassée)"

        r = f"<b>⚡ MODULE 2 : STRUCTURE DU PRIX</b><br>"
        r += f"{'🟢' if has_mss else ('🟡' if has_bos else '🔴')} Structure : <code>{mode}</code>{struct_quality}<br>"
        r += f"{'🟢' if disp['is_displaced'] else '🔴'} Displacement : {disp['velocity']} (×{disp['power_ratio']})<br>"
        r += f"{'🟢' if ts != 'NONE' else '🔴'} SFP/Turtle Soup : {ts}<br>"
        r += f"🛡️ Anti-Inducement : <code>{anti_induce}</code><br>"
        r += f"⚪ SWH: {swh:.2f} | SWL: {swl:.2f}<br>"
        r += f"<span style='font-size:0.8rem; color:{'#00ff88' if sweep_occurred else '#f0b429'};'>{'🎯 Sweep ERL détecté avant structure' if sweep_occurred else '⚠️ Sweep ERL non confirmé — risque inducement'}</span><br><br>"
        return r

    # =====================================================
    # MODULE 3 : LIQUIDITÉ EXTERNE — ENRICHI COMPLET
    # Bible §4.1 (DOL) + §4.2 (Niveaux temporels) + §4.5 (LRLR/HRLR)
    # + §14.1 (Smooth/Jagged) + §15.1 (ERL/IRL)
    # =====================================================
    def _mod3_external_liquidity(self, tf, liq, bias):
        dol = bias['draw_on_liquidity']
        bsl = liq['erl']['high']
        ssl = liq['erl']['low']
        bsl_status = liq['erl'].get('high_status', '?')
        ssl_status = liq['erl'].get('low_status', '?')
        prox = liq['proximal_liquidity']

        # Sweep status couleur
        sweep_status = "🎯 PROXIMAL" if dol['dist'] < 0.003 else "🔎 EN COURS"

        # NDOG / NWOG
        ndog = liq.get('ndog', 0)
        nwog = liq.get('nwog', 0)

        # DOL directionnel
        dol_bull = liq.get('dol_bull', {})
        dol_bear = liq.get('dol_bear', {})

        # LRLR / HRLR
        lrlr = liq.get('lrlr_hrlr', {})

        # Temporal levels
        temporal = liq.get('temporal_levels', {})

        r = f"<b>🧲 MODULE 3 : LIQUIDITÉ EXTERNE (ERL)</b><br>"

        # --- DOL primaire (depuis bias_expert) ---
        r += f"🎯 DOL Principal : <code>{dol['name']}</code> @ {dol['price']:.5f}<br>"
        r += f"⚪ Distance : {dol['dist']:.4f} — {sweep_status}<br>"

        # --- ERL haut / bas avec statut SWEPT/INTACT ---
        bsl_icon = '⚠️' if bsl_status == 'SWEPT' else '🔴'
        ssl_icon = '⚠️' if ssl_status == 'SWEPT' else '🟢'
        r += f"{bsl_icon} BSL (High) : {bsl:.5f} — <code style='color:{'#f0b429' if bsl_status=='SWEPT' else '#ef5350'};'>{bsl_status}</code><br>"
        r += f"{ssl_icon} SSL (Low) : {ssl:.5f} — <code style='color:{'#f0b429' if ssl_status=='SWEPT' else '#26a69a'};'>{ssl_status}</code><br>"

        # --- Niveaux temporels PDH/PDL/PWH/PWL avec SWEPT/INTACT ---
        if temporal:
            r += f"<br><b style='font-size:0.8rem; color:#848e9c;'>📅 NIVEAUX TEMPORELS :</b><br>"
            for key in ['PDH', 'PDL', 'PWH', 'PWL']:
                if key in temporal:
                    t = temporal[key]
                    is_swept = t['status'] == 'SWEPT'
                    color = '#848e9c' if is_swept else ('#ef5350' if 'H' in key else '#26a69a')
                    icon = '✅' if is_swept else ('🔴' if 'H' in key else '🟢')
                    r += f"<span style='font-size:0.8rem; color:{color};'>{icon} {key}: {t['price']:.5f} — <b>{t['status']}</b> ({t['side']})</span><br>"

        # --- EQH avec prix exacts, qualité et statut sweep ---
        eqh = liq.get('eqh', [])
        r += f"<br><b style='font-size:0.8rem; color:#848e9c;'>🔺 EQH (Buy-Side Liquidity) :</b><br>"
        if eqh:
            for e in eqh:
                is_smooth = e['quality'] == 'SMOOTH'
                is_swept = e.get('swept', False)
                prox_tag = e.get('proximity', 'DISTAL')
                color = '#848e9c' if is_swept else ('#ef5350' if is_smooth else '#d1d4dc')
                q_tag = '🔴 SMOOTH ⭐' if is_smooth else '⚪ JAGGED'
                s_tag = '⚠️ SWEPT' if is_swept else '✅ INTACT'
                p_tag = '📍 PROXIMAL' if prox_tag == 'PROXIMAL' else '🔭 DISTAL'
                r += f"<span style='font-size:0.8rem; color:{color};'>  {q_tag} @ {e['price']:.5f} — {s_tag} — {p_tag}</span><br>"
        else:
            r += f"<span style='font-size:0.8rem; color:#848e9c;'>  Aucun EQH détecté</span><br>"

        # --- EQL avec prix exacts, qualité et statut sweep ---
        eql = liq.get('eql', [])
        r += f"<b style='font-size:0.8rem; color:#848e9c;'>🔻 EQL (Sell-Side Liquidity) :</b><br>"
        if eql:
            for e in eql:
                is_smooth = e['quality'] == 'SMOOTH'
                is_swept = e.get('swept', False)
                prox_tag = e.get('proximity', 'DISTAL')
                color = '#848e9c' if is_swept else ('#26a69a' if is_smooth else '#d1d4dc')
                q_tag = '🟢 SMOOTH ⭐' if is_smooth else '⚪ JAGGED'
                s_tag = '⚠️ SWEPT' if is_swept else '✅ INTACT'
                p_tag = '📍 PROXIMAL' if prox_tag == 'PROXIMAL' else '🔭 DISTAL'
                r += f"<span style='font-size:0.8rem; color:{color};'>  {q_tag} @ {e['price']:.5f} — {s_tag} — {p_tag}</span><br>"
        else:
            r += f"<span style='font-size:0.8rem; color:#848e9c;'>  Aucun EQL détecté</span><br>"

        # --- DOL directionnel BULL / BEAR --- Bible §4.1
        r += "<br>"
        if dol_bull and dol_bull.get('name') != 'N/A':
            r += f"🟢 DOL BULL ► {dol_bull['name']} @ {dol_bull['price']:.5f}<br>"
        if dol_bear and dol_bear.get('name') != 'N/A':
            r += f"🔴 DOL BEAR ► {dol_bear['name']} @ {dol_bear['price']:.5f}<br>"

        # --- LRLR / HRLR --- Bible §4.5
        if lrlr:
            bull_run = lrlr.get('bull', {})
            bear_run = lrlr.get('bear', {})
            r += "<br>"
            if bull_run:
                is_lrlr = bull_run['type'] == 'LRLR'
                r += f"{'🟢' if is_lrlr else '🟡'} Chemin BULL : <code>{bull_run['label']}</code><br>"
            if bear_run:
                is_lrlr = bear_run['type'] == 'LRLR'
                r += f"{'🟢' if is_lrlr else '🟡'} Chemin BEAR : <code>{bear_run['label']}</code><br>"

        # --- NDOG / NWOG ---
        r += "<br>"
        r += f"{'🟡' if ndog > 0 else '⚪'} NDOG : {'@ ' + str(round(ndog, 5)) if ndog > 0 else 'Non détecté (D1 requis)'}<br>"
        r += f"{'🟡' if nwog > 0 else '⚪'} NWOG : {'@ ' + str(round(nwog, 5)) if nwog > 0 else 'Non détecté (W1 requis)'}<br>"
        r += f"📍 Proximal Global : <code>{prox:.5f}</code><br><br>"
        return r



    # =====================================================
    # MODULE 4 : ZONES IRL — FVG FRAIS DÉTAILLÉS + OB NON RETESTÉS DÉTAILLÉS
    # Bible §3.2 (hiérarchie) + §3.3 (OB quality) + §3.4 (FVG)
    # =====================================================
    def _mod4_internal_zones(self, tf, smc, liq):
        fvgs = smc['fvgs']
        blocks = smc['institutional_blocks']
        rej = smc['rejections']
        bprs = smc['fvgs_pd_arrays']['bprs']

        # FVG Quality States — FRESH = non mitigés = à surveiller
        fresh_fvgs = [f for f in fvgs if not f.get('mitigated', False) and 'IFVG' not in f['type']]
        mitigated_fvgs = [f for f in fvgs if f.get('mitigated', False)]
        ifvgs = [f for f in fvgs if 'IFVG' in f['type']]

        # OB — distinguer frais (non revisités) et retestés
        obs_fresh = [b for b in blocks if 'OB' in b['type'] and b.get('quality_score', 0) >= 2]
        breakers = [b for b in blocks if 'BREAKER' in b['type']]

        # Rejection Block
        has_rej = rej['bull_wick_ce'] > 0 or rej['bear_wick_ce'] > 0

        # Volume Imbalance
        vis = smc.get('volume_imbalances', [])
        has_vi = len(vis) > 0

        # Best OB quality score
        best_ob_score = max([b.get('quality_score', 0) for b in obs_fresh], default=0)

        r = f"<b>📦 MODULE 4 : ZONES IRL</b><br>"

        # --- FVG FRAIS avec niveaux exacts (Bible §3.4 + §12 Étape 4) ---
        r += f"{'🟢' if fresh_fvgs else '🔴'} FVG Non Équilibrés (FRESH) : {len(fresh_fvgs)}<br>"
        if fresh_fvgs:
            for f in fresh_fvgs[-4:]:  # Afficher les 4 plus récents
                ftype = f['type']
                is_bull = 'BISI' in ftype
                fc = '#00ff88' if is_bull else '#ef5350'
                r += f"<span style='font-size:0.8rem; color:{fc};'>  {'🟢' if is_bull else '🔴'} {ftype}: top={f['top']:.2f} bot={f['bot']:.2f} CE={f['ce']:.2f}</span><br>"
        else:
            r += f"<span style='font-size:0.8rem; color:#848e9c;'>  Aucun FVG frais sur ce TF</span><br>"

        r += f"{'🟡' if mitigated_fvgs else '⚪'} FVG Mitigés : {len(mitigated_fvgs)}<br>"

        # IFVG (FVG inversés — changent de rôle)
        r += f"{'🟡' if ifvgs else '⚪'} IFVG (Inversés) : {len(ifvgs)}<br>"
        if ifvgs:
            for f in ifvgs[-2:]:
                r += f"<span style='font-size:0.8rem; color:#f0b429;'>  🔄 {f['type']}: CE={f['ce']:.2f}</span><br>"

        # --- OB NON RETESTÉS avec niveaux exacts (Bible §3.3 + §12 Étape 4) ---
        r += f"<br>{'🟢' if obs_fresh else '🔴'} Order Blocks Non Retestés : {len(obs_fresh)} (Best: <code>{best_ob_score}/5</code>)<br>"
        if obs_fresh:
            for b in obs_fresh[-4:]:  # Afficher les 4 plus récents
                is_bull_ob = 'BULL' in b['type']
                bc = '#00ff88' if is_bull_ob else '#ef5350'
                score_stars = '⭐' * b.get('quality_score', 0)
                r += f"<span style='font-size:0.8rem; color:{bc};'>  {'🟢' if is_bull_ob else '🔴'} {b['type']}: zone [{b['refined_zone'][0]:.2f}–{b['refined_zone'][1]:.2f}] {score_stars}</span><br>"
        else:
            r += f"<span style='font-size:0.8rem; color:#848e9c;'>  Aucun OB frais sur ce TF</span><br>"

        r += f"{'🟢' if breakers else '🔴'} Breaker Blocks : {len(breakers)}<br>"
        if breakers:
            for b in breakers[-2:]:
                is_bull_bk = 'BULL' in b['type']
                bc = '#00ff88' if is_bull_bk else '#ef5350'
                r += f"<span style='font-size:0.8rem; color:{bc};'>  🔥 {b['type']}: niveau {b['level']:.2f}</span><br>"

        r += f"{'🟢' if bprs else '🔴'} BPR : {len(bprs)} détectés<br>"
        r += f"{'🟢' if has_vi else '🔴'} Volume Imbalance : {'OUI — ' + str(len(vis)) + ' zones' if has_vi else 'NON'}<br>"
        r += f"{'🟢' if has_rej else '🔴'} Rejection Block : {'OUI' if has_rej else 'NON'}<br>"

        # Unicorn detection (Breaker + FVG overlap) — Bible §5.8
        unicorn = False
        for bk in breakers:
            for f in fvgs:
                if abs(f['ce'] - bk['level']) < abs(bk['refined_zone'][1] - bk['refined_zone'][0]):
                    unicorn = True
                    break
        r += f"{'🌟' if unicorn else '⚪'} Unicorn Setup : {'DÉTECTÉ ⭐' if unicorn else 'NON'}<br><br>"
        return r

    # =====================================================
    # MODULE 5 : PREMIUM / DISCOUNT / OTE
    # =====================================================
    def _mod5_pricing(self, tf, exe):
        eq = exe['equilibrium']
        ote = exe['ote']

        is_ote = 62.0 <= eq['percent'] <= 79.0
        is_extreme = eq['percent'] < 25.0 or eq['percent'] > 75.0
        is_discount = 'DISCOUNT' in eq['zone']

        r = f"<b>🎯 MODULE 5 : PREMIUM / DISCOUNT</b><br>"
        r += f"{'🟢' if is_discount else '🔴'} Zone : <code>{eq['zone']}</code> ({eq['percent']:.1f}%)<br>"
        r += f"{'🟢' if is_ote else '🔴'} OTE Range : {'DANS OTE ✅' if is_ote else 'HORS OTE'}<br>"
        r += f"{'⭐' if is_extreme else '⚪'} Zone Extrême : {'OUI (+10%)' if is_extreme else 'NON'}<br>"
        r += f"⚪ Niveau 70.5% : {ote['lvl_705']:.2f}<br><br>"
        return r

    # =====================================================
    # MODULE 6 : TIME & MACRO
    # =====================================================
    def _mod6_time_macro(self, tf, clock, mmxm):
        kz = clock['killzone']
        sb = clock['silver_bullet']
        macro = clock['macro']
        is_tradable = clock['is_tradable']
        is_hp = clock['is_high_prob']

        # M13 FIX : CBDR se forme entre 14h et 20h EST (heure NY) selon ICT
        # C'est la fenêtre "Central Bank Dealers Range" — PAS la session ASIA
        ny_hour = 0
        try:
            import pytz
            from datetime import datetime
            ny_hour = datetime.now(pytz.timezone("America/New_York")).hour
        except Exception:
            pass
        in_cbdr_window = 14 <= ny_hour < 20

        r = f"<b>🕒 MODULE 6 : TIME & MACRO</b><br>"
        r += f"{'🟢' if kz != 'NONE' else '🔴'} Killzone : <code>{kz}</code><br>"
        r += f"{'🟢' if sb != 'NONE' else '🔴'} Silver Bullet : {sb}<br>"
        r += f"{'🟢' if macro != 'NONE' else '🔴'} Macro Active : <code>{macro}</code><br>"
        r += f"{'🟢' if is_tradable else '🔴'} Tradable : {'OUI' if is_tradable else 'NON — HORS SESSION'}<br>"
        r += f"{'⭐' if is_hp else '⚪'} Haute Probabilité : {'OUI ⭐' if is_hp else 'NON'}<br>"
        r += f"{'🟡' if in_cbdr_window else '⚪'} CBDR/Flout : {'WINDOW ACTIVE (14h-20h NY)' if in_cbdr_window else 'Hors fenêtre CBDR (14h-20h NY)'}<br>"
        r += f"⚪ Heure NY : {clock['ny_time']} ({clock['day']})<br><br>"
        return r

    # =====================================================
    # MODULE 7 : SETUPS DÉTECTÉS
    # =====================================================
    def _mod7_setups(self, tf, smc, liq, mmxm, clock, exe):
        sb_status = mmxm['silver_bullet']
        ts = mmxm['turtle_soup']
        has_mss = "MSS" in smc['structure']['mode']
        has_fvg = len(smc['fvgs']) > 0
        has_disp = smc['displacement']['is_displaced']
        in_kz = clock['killzone'] != "NONE"
        in_sb = clock['silver_bullet'] != "NONE"

        # Detect active setups
        setups = []
        if in_sb and has_mss and has_fvg and has_disp:
            setups.append(f"🎯 SILVER BULLET ({sb_status})")
        if ts != "NONE":
            setups.append(f"🐢 TURTLE SOUP ({ts})")
        if "MANIPULATION" in mmxm['po3_phase'] and has_mss:
            setups.append("⚡ JUDAS SWING → DISTRIBUTION")

        # Grail check (Bible §5.7 — 5 conditions simultanées VRAIES ICT)
        # AUDIT #9 FIX : Les 5 vraies conditions du Grail sont :
        # 1. Killzone active  2. Sweep ERL confirmé  3. MSS + Displacement
        # 4. OB + FVG alignés  5. SMT Divergence (paire corrélée)
        breakers = [b for b in smc['institutional_blocks'] if 'BREAKER' in b['type']]
        obs = [b for b in smc['institutional_blocks'] if 'OB' in b['type']]
        erl_h = liq['erl']['high']
        erl_l = liq['erl']['low']
        erl_range = erl_h - erl_l if erl_h != erl_l else 1
        swh = smc['structure']['swh']
        swl = smc['structure']['swl']
        sweep_ok = (abs(swh - erl_h) / erl_range < 0.05) or (abs(swl - erl_l) / erl_range < 0.05)
        sweep_confirmed_ = smc.get('boolean_sweep_erl', {}).get('value', False)

        # Condition 4 : OB + FVG alignés (CE d'un FVG dans la zone d'un OB)
        ob_fvg_aligned = False
        for ob in obs:
            for fvg in smc['fvgs']:
                z = ob.get('refined_zone', [0, 0])
                if z[0] <= fvg.get('ce', -1) <= z[1]:
                    ob_fvg_aligned = True
                    break
        # Condition 5 : proxy SMT = EQH ou EQL smooth non sweepé (cible clé)
        has_smooth_liq = (
            any(e['quality'] == 'SMOOTH' and not e.get('swept', False) for e in liq['eqh'])
            or any(e['quality'] == 'SMOOTH' and not e.get('swept', False) for e in liq['eql'])
        )

        grail_conditions_met = sum([
            bool(in_kz),              # Cond 1
            bool(sweep_confirmed_),   # Cond 2 (Sweep ERL réel)
            bool(has_mss and has_disp),  # Cond 3
            bool(ob_fvg_aligned),     # Cond 4
            bool(has_smooth_liq),     # Cond 5 (proxy SMT)
        ])
        if grail_conditions_met >= 4:  # 4 ou 5 conditions sur 5
            label = f"{'5/5' if grail_conditions_met == 5 else '4/5'} conditions"
            setups.append(f"🏆 GRAIL SETUP POTENTIEL ({label})")

        # Unicorn (sous-set du Grail)
        unicorn = False
        fresh_fvgs = [f for f in smc['fvgs'] if not f.get('mitigated', False)]
        for bk in breakers:
            for f in fresh_fvgs:
                if abs(f['ce'] - bk['level']) < abs(bk['refined_zone'][1] - bk['refined_zone'][0]):
                    unicorn = True
                    break
        if unicorn and not any('GRAIL' in s for s in setups):
            setups.append("🦄 UNICORN (Breaker + FVG)")

        r = f"<b>🔥 MODULE 7 : SETUPS ACTIFS</b><br>"
        if setups:
            for s in setups:
                r += f"<code>{s}</code><br>"
        else:
            r += "⚪ Aucun setup actif détecté<br>"
            r += "⏳ Attendre MSS + Displacement + FVG en Killzone + Sweep ERL<br>"
        r += "<br>"
        return r

    # ====================================================================
    # SCORING V4 ENRICHI — Bible ict_detection_rules.md §11 (100 pts max)
    # FIX-M: Décote -10pts hors Macro/KZ (Bible §11)
    # FIX-N: Boolean_Sweep_ERL gate (Bible §0 — RÈGLE ABSOLUE → cap 45 si False)
    # FIX-L: OTE invalide si retracement > 79% (Bible §8)
    # ====================================================================
    def _calculate_score_v4(self, smc, liq, bias, exe, mmxm, clock):
        score = 0

        # FIX-N: Lire Boolean_Sweep_ERL
        sweep_erl = smc.get('boolean_sweep_erl', {})
        sweep_confirmed = sweep_erl.get('value', False)

        # --- SECTION A: NARRATIF HTF & ERL (25 pts) ---
        if bias['draw_on_liquidity']['dist'] < 0.003:
            score += 10
        if "MSS" in smc['structure']['mode'] and smc['displacement']['is_displaced']:
            score += 10
        if bias['htf_bias'] != "NEUTRAL":
            score += 5

        # --- SECTION B: EMPLACEMENT PD ARRAYS & MACRO (25 pts) ---
        has_fvg_in_ob = False
        for f in smc['fvgs']:
            for b in smc['institutional_blocks']:
                z = b.get('refined_zone', [0, 0])
                if z[0] <= f['ce'] <= z[1]:
                    has_fvg_in_ob = True
        if has_fvg_in_ob:
            score += 10

        # FIX-M: +10 en Macro/KZ, -10 hors session (Bible §11)
        in_kz = clock['killzone'] != "NONE" or clock['macro'] != "NONE"
        if in_kz:
            score += 10
        else:
            score -= 10

        # AUDIT #8 FIX — OTE calculé sur le DERNIER SWING LOCAL (pas le dealing range global)
        # ICT: OTE est la zone 62-79% de retracement Fibonacci du dernier impulse swing.
        # Le swing SMC (swh/swl) est le bon référentiel — pas le dealing range entier (eqh/eql).
        try:
            swh_local = smc['structure']['swh']
            swl_local = smc['structure']['swl']
            cur_p     = exe['equilibrium']['price']
            swing_rng = swh_local - swl_local if swh_local != swl_local else 1
            struct_mode = smc['structure']['mode']

            if 'BULL' in struct_mode or 'BUY' in bias.get('htf_bias', ''):
                # Retracement vers le bas après un impulse haussier
                retrace_pct = ((swh_local - cur_p) / swing_rng) * 100
            else:
                # Retracement vers le haut après un impulse baissier
                retrace_pct = ((cur_p - swl_local) / swing_rng) * 100

            if 62.0 <= retrace_pct <= 79.0:
                score += 5   # Dans l'OTE — zone optimale d'entrée
            elif retrace_pct > 85.0 or retrace_pct < 10.0:
                score -= 5   # Trop loin (prix trop étiqué ou trop tôt)
        except Exception:
            # Fallback sur l'ancien calcul si smc['structure'] incomplet
            eq_pct = exe['equilibrium']['percent']
            if 62.0 <= eq_pct <= 79.0:
                score += 5
            elif eq_pct > 79.0 or eq_pct < 21.0:
                score -= 5

        # --- SECTION C: LIQUIDITY DRAW (25 pts) ---
        eqh_smooth = any(e['quality'] == 'SMOOTH' and not e.get('swept', False) for e in liq['eqh'])
        eql_smooth = any(e['quality'] == 'SMOOTH' and not e.get('swept', False) for e in liq['eql'])
        if eqh_smooth or eql_smooth:
            score += 15
        if bias['draw_on_liquidity']['dist'] < 0.005:
            score += 10

        # LRLR bonus: chemin dégagé vers la cible +5 (Bible §4.5)
        lrlr = liq.get('lrlr_hrlr', {})
        is_bull_bias = 'BULL' in bias['htf_bias']
        if is_bull_bias and lrlr.get('bull', {}).get('type') == 'LRLR':
            score += 5
        elif not is_bull_bias and lrlr.get('bear', {}).get('type') == 'LRLR':
            score += 5

        # --- SECTION D: RISK / RENDEMENT (25 pts) ---
        if (("BULL" in bias['htf_bias'] and "DISCOUNT" in exe['equilibrium']['zone']) or
           ("BEAR" in bias['htf_bias'] and "PREMIUM" in exe['equilibrium']['zone'])):
            score += 10
        if mmxm['turtle_soup'] != "NONE":
            score += 10
        if smc['displacement']['is_displaced']:
            score += 5

        # AUDIT #1 FIX — Blocage dur Sweep ERL (Bible §0 : règle absolue)
        # Si Boolean_Sweep_ERL = False → score plafonné à 44 (sous seuil WATCH=65)
        # Ce plafond est INFRANCHISSABLE : un trade ne peut pas être validé sans Sweep ERL.
        if not sweep_confirmed:
            score = min(score, 44)  # Plafond dur sous le seuil WATCH (65)

        # FIX-O: Vendredi après 14h NYC = NO TRADE
        if clock.get('friday_no_trade', False):
            return 0

        # CORRECTION AFFICHAGE : Le score minimum est 0 (pas de score négatif /100)
        # Les pénalités servent à empêcher d'atteindre les seuils WATCH/EXECUTE,
        # pas à produire des valeurs impossibles comme -5/100.
        score = max(score, 0)
        return min(score, 100)

    def _get_verdict(self, score, score_execute=80, score_limit=65):
        if score >= score_execute: return "🚀 EXÉCUTION A+"
        if score >= score_limit: return "🔍 WATCH / SNIPER"
        return "❌ INTERDIT (Pas de Setup)"

    # =====================================================
    # NARRATIF IA ENRICHI — DOUBLE SCÉNARIO (CONTINUATION + RENVERSEMENT)
    # =====================================================
    def _generate_ia_narrative(self, tf, score, verdict, bias, mmxm, smc=None, liq=None, exe=None, clock=None, score_execute=80, score_limit=65):
        bias_type = bias['htf_bias']
        dol = bias['draw_on_liquidity']
        po3 = mmxm['po3_phase']
        cycle = mmxm['mmxm_cycle']
        ts = mmxm['turtle_soup']
        sb = mmxm['silver_bullet']
        mo = mmxm['midnight_open']
        ipda = bias.get('ipda_ranges', {})

        # Extract data if available
        mode = smc['structure']['mode'] if smc else "N/A"
        disp = smc['displacement'] if smc else {'is_displaced': False, 'velocity': 'N/A', 'power_ratio': 0}
        swh = smc['structure']['swh'] if smc else 0
        swl = smc['structure']['swl'] if smc else 0
        mid = (swh + swl) / 2

        fvgs = smc['fvgs'] if smc else []
        blocks = smc['institutional_blocks'] if smc else []
        fresh_fvgs = [f for f in fvgs if not f.get('mitigated', False) and 'IFVG' not in f['type']]
        breakers = [b for b in blocks if 'BREAKER' in b['type']]
        obs = [b for b in blocks if 'OB' in b['type']]

        bsl = liq['erl']['high'] if liq else 0
        ssl = liq['erl']['low'] if liq else 0
        eqh_smooth = any(e['quality'] == 'SMOOTH' for e in liq['eqh']) if liq else False
        eql_smooth = any(e['quality'] == 'SMOOTH' for e in liq['eql']) if liq else False

        eq_zone = exe['equilibrium']['zone'] if exe else "N/A"
        eq_pct = exe['equilibrium']['percent'] if exe else 50
        ote_lvl = exe['ote']['lvl_705'] if exe else 0

        kz = clock['killzone'] if clock else "NONE"
        macro = clock['macro'] if clock else "NONE"
        day = clock['day'] if clock else "N/A"
        ny_time = clock['ny_time'] if clock else "N/A"

        is_bull = "BULL" in bias_type
        is_bear = "BEAR" in bias_type

        # Biais local TF
        local_bias = self._compute_local_bias(smc, exe, mmxm) if (smc and exe and mmxm) else "NEUTRAL"
        lc = '#00ff88' if 'BULL' in local_bias else ('#ef5350' if 'BEAR' in local_bias else '#848e9c')

        # ---- SECTION 1: CONTEXTE GÉNÉRAL ----
        story = f"<b style='color:#2962ff; font-size:1.1rem;'>📊 ANALYSE COMPLÈTE — {tf}</b>"
        story += f"<br><br>"

        # Biais local TF en première position (Bible §14.4)
        story += f"<b>0. BIAIS LOCAL {tf}</b><br>"
        story += f"Ce timeframe est en tendance <b style='color:{lc};'>{local_bias}</b> "
        story += f"(structure: <code>{mode}</code>). "
        aligned = ('BULL' in local_bias and 'BULL' in bias_type) or ('BEAR' in local_bias and 'BEAR' in bias_type)
        if aligned:
            story += f"✅ Aligné avec le biais HTF global ({bias_type}). "
        else:
            story += f"⚠️ Contra-tendance par rapport au HTF ({bias_type}) — prudence accrue requise. "
        story += "<br><br>"

        story += f"<b>1. FLUX INSTITUTIONNEL (IPDA)</b><br>"
        story += f"L'algorithme de livraison de prix (IPDA) est actuellement engagé dans un flux "
        story += f"<b style='color:{'#00ff88' if is_bull else '#ef5350'}'>{bias_type}</b>. "
        story += f"Cela signifie que les grands opérateurs (banques centrales, hedge funds) "
        if is_bull:
            story += "accumulent des positions acheteuses et cherchent à pousser le prix vers les bassins de liquidité situés au-dessus du marché (BSL). "
        elif is_bear:
            story += "distribuent leurs positions et cherchent à pousser le prix vers les bassins de liquidité situés en dessous du marché (SSL). "
        else:
            story += "n'ont pas encore révélé leur intention directionnelle. Le marché est en phase d'indécision ou de consolidation. "

        story += f"Le Midnight Open (référence institutionnelle de la journée) se situe à <code>{mo:.2f}</code>. "

        # IPDA Ranges dans le narratif
        if ipda:
            r20 = ipda.get('r20', {})
            r40 = ipda.get('r40', {})
            story += f"<br>📐 IPDA 20j: H={r20.get('high',0):.2f} / L={r20.get('low',0):.2f} | "
            story += f"IPDA 40j: H={r40.get('high',0):.2f} / L={r40.get('low',0):.2f}. "

        # AMD Phase
        story += f"<br><br><b>2. PHASE AMD (Power of 3)</b><br>"
        story += f"Nous sommes actuellement en phase <b>{po3}</b>. "
        if "ACCUMULATION" in po3:
            story += "C'est la phase de préparation où les institutions construisent leurs positions dans un range étroit. "
            story += "Le prix consolide avant le vrai mouvement — <i>ne pas trader pendant cette phase</i>. "
        elif "MANIPULATION" in po3:
            story += "C'est le \"Judas Swing\" — le marché effectue un faux mouvement dans la direction opposée "
            story += "pour déclencher les stop-loss et piéger les traders retail. C'est le signal que le vrai mouvement se prépare. "
        elif "DISTRIBUTION" in po3 or "EXPANSION" in po3:
            story += "Le vrai mouvement est en cours. Les institutions ont terminé leur manipulation et le prix se dirige maintenant "
            story += f"vers l'objectif de liquidité à <b>{dol['price']:.2f}</b>. "
        else:
            story += f"Le cycle MMXM indique <b>{cycle}</b>, ce qui suggère une transition entre phases. "

        story += f"<br>Sur le plan hebdomadaire ({day}), "
        if day == "LUNDI":
            story += "nous sommes dans l'<b>Accumulation Weekly</b> — les institutions posent les bases de la semaine. "
        elif day == "MARDI":
            story += "c'est le jour de <b>Manipulation Weekly</b> — le High ou le Low de la semaine est statistiquement formé ce jour-là (62-73% des cas selon ICT). "
        elif day in ["MERCREDI", "JEUDI", "VENDREDI"]:
            story += f"c'est la phase de <b>Distribution Weekly</b> — le vrai mouvement de la semaine devrait être en cours. "
        else:
            story += "le marché est fermé (weekend). "

        # ---- SECTION 2: STRUCTURE DE PRIX ----
        story += f"<br><br><b>3. STRUCTURE DU PRIX</b><br>"
        story += f"La structure actuelle est <code>{mode}</code>. "
        if "MSS" in mode:
            story += "Un <b>Market Structure Shift (MSS)</b> a été confirmé — c'est le signal le plus puissant d'ICT. "
            story += "Il indique un changement définitif de la direction du prix, validé par un Displacement. "
        elif "BOS" in mode:
            story += "Un <b>Break of Structure (BOS)</b> est en cours — le prix casse les anciens niveaux de swing. "
            story += "Attention : un BOS sans Displacement n'est pas un signal d'entrée valide selon ICT. "
        elif "EXPANSION" in mode:
            story += "Le prix est en <b>Expansion</b> sans rupture nette de structure. "
        else:
            story += "Pas de cassure de structure significative. Le prix est en <b>consolidation</b> ou en range. "

        if disp['is_displaced']:
            story += f"<br>Le <b>Displacement</b> est confirmé (force ×{disp['power_ratio']}, vélocité: {disp['velocity']}). "
            story += "Cela signifie que les institutions ont injecté du volume massif — le mouvement est \"réel\" et non une manipulation. "
        else:
            story += "<br>Aucun Displacement significatif détecté. Sans cette confirmation de volume, tout signal structurel reste suspect. "

        if ts != "NONE":
            story += f"<br>🐢 Un <b>{ts}</b> (Turtle Soup / SFP) a été détecté. "
            story += "C'est une signature de renversement institutionnel : le prix a sweepé un niveau clé puis s'est retourné. "

        # ---- SECTION 3: LIQUIDITÉ ----
        story += f"<br><br><b>4. CARTE DE LIQUIDITÉ</b><br>"
        story += f"Le DOL (Draw On Liquidity) principal est <b>{dol['name']}</b> situé à <code>{dol['price']:.2f}</code> "
        story += f"(distance: {dol['dist']:.4f}). "
        if dol['dist'] < 0.003:
            story += "Le prix est <b>très proche</b> de cet objectif — le sweep est imminent ou en cours. "
        elif dol['dist'] < 0.01:
            story += "L'objectif est en vue — le prix devrait l'atteindre dans les prochaines séances. "
        else:
            story += "L'objectif est encore éloigné — plusieurs étapes intermédiaires sont probables. "

        story += f"<br>BSL (Buy-Side Liquidity) : <code>{bsl:.2f}</code> | SSL (Sell-Side Liquidity) : <code>{ssl:.2f}</code>. "
        if eqh_smooth:
            story += "<br>🔴 Les <b>Equal Highs (EQH)</b> sont <b>SMOOTH</b> — c'est un bassin de liquidité de qualité A+, les algorithmes le cibleront. "
        if eql_smooth:
            story += "<br>🟢 Les <b>Equal Lows (EQL)</b> sont <b>SMOOTH</b> — bassin de liquidité prioritaire pour les institutions. "

        # ---- SECTION 4: PD ARRAYS / POI — DÉTAILLÉS ----
        story += f"<br><br><b>5. ZONES D'INTÉRÊT (PD Arrays)</b><br>"
        story += f"Le prix est actuellement en zone <b>{eq_zone}</b> ({eq_pct:.1f}% du Dealing Range). "
        if eq_zone == "DISCOUNT" and is_bull:
            story += "C'est la zone idéale pour acheter selon ICT — les institutions accumulent ici. "
        elif eq_zone == "PREMIUM" and is_bear:
            story += "C'est la zone idéale pour vendre — les institutions distribuent dans cette zone. "
        elif eq_zone == "DISCOUNT" and is_bear:
            story += "⚠️ Le prix est en Discount mais le biais est baissier — une manipulation haussière temporaire est possible avant la reprise baissière. "
        elif eq_zone == "PREMIUM" and is_bull:
            story += "⚠️ Le prix est en Premium alors que le biais est haussier — c'est une zone de risque élevé pour les achats. Attendre un retour en Discount. "

        story += f"<br>OTE 70.5% : <code>{ote_lvl:.2f}</code>. "

        # FVG FRESH détaillés dans le narratif
        if fresh_fvgs:
            story += f"<br>📍 <b>FVG Non Équilibrés à surveiller sur {tf} :</b><br>"
            for f in fresh_fvgs[-3:]:
                is_bull_fvg = 'BISI' in f['type']
                fc = '#00ff88' if is_bull_fvg else '#ef5350'
                story += f"<span style='color:{fc};'>• {f['type']}: [{f['bot']:.2f} → {f['top']:.2f}], CE={f['ce']:.2f}</span><br>"
        else:
            story += f"<br>⚪ Aucun FVG frais détecté sur {tf}. "

        # OB non retestés dans le narratif
        obs_fresh = [b for b in obs if b.get('quality_score', 0) >= 2]
        if obs_fresh:
            story += f"<br>📦 <b>Order Blocks non retestés ({len(obs_fresh)}) :</b><br>"
            for b in obs_fresh[-2:]:
                is_bull_ob = 'BULL' in b['type']
                bc = '#00ff88' if is_bull_ob else '#ef5350'
                story += f"<span style='color:{bc};'>• {b['type']}: [{b['refined_zone'][0]:.2f}–{b['refined_zone'][1]:.2f}] score={b.get('quality_score',0)}/5</span><br>"

        # ---- SECTION 5: TIMING ----
        story += f"<br><br><b>6. FENÊTRE TEMPORELLE</b><br>"
        story += f"Heure NY: <code>{ny_time}</code> | Killzone: <code>{kz}</code> | Macro: <code>{macro}</code>. "
        if kz != "NONE":
            story += f"Nous sommes dans la <b>Killzone {kz}</b> — c'est une fenêtre de haute probabilité pour les mouvements institutionnels. "
        if sb != "INACTIVE" and sb != "NONE":
            story += f"Le modèle <b>Silver Bullet</b> est actif (<code>{sb}</code>) — une entrée de précision est possible si MSS + FVG sont présents. "

        # ==================================================================
        # ---- SECTION 6: DOUBLE SCÉNARIO (CONTINUATION vs RENVERSEMENT) ----
        # ==================================================================
        story += f"<br><br><hr style='border-color:#2a2e39'>"
        story += f"<b style='color:#2962ff; font-size:1rem;'>🔮 SCÉNARIOS DE TRADING</b>"

        # --- SCÉNARIO A: CONTINUATION ---
        story += f"<br><br><b style='color:#00ff88'>▶ SCÉNARIO A — CONTINUATION ({bias_type})</b><br>"
        if is_bull:
            story += f"Si le flux haussier se poursuit, le prix devrait continuer vers le <b>BSL à {bsl:.2f}</b>"
            if eqh_smooth:
                story += " en ciblant les Equal Highs Smooth (liquidité institutionnelle de premier ordre)"
            story += ". "
            story += f"<br><b>Conditions pour valider :</b> "
            story += f"<br>• Le prix reste au-dessus du Midnight Open ({mo:.2f}) "
            story += f"<br>• Tout pullback respecte la zone Discount (sous {mid:.2f}) "
            story += f"<br>• Un FVG haussier (BISI) frais sert de support — ne pas entrer si le FVG est mitigé "
            if obs:
                story += f"<br>• Les Order Blocks haussiers non retestés doivent tenir comme support "
            story += f"<br>• Entrée optimale : retracement vers OTE 70.5% ({ote_lvl:.2f}) dans un FVG non comblé "
            story += f"<br>• Stop Loss : sous le dernier SWL ({swl:.2f}) + spread "
            story += f"<br>• Take Profit : BSL à {bsl:.2f} (partiel à EQ {mid:.2f}) "
        elif is_bear:
            story += f"Si le flux baissier se maintient, le prix devrait descendre vers le <b>SSL à {ssl:.2f}</b>"
            if eql_smooth:
                story += " en ciblant les Equal Lows Smooth"
            story += ". "
            story += f"<br><b>Conditions pour valider :</b> "
            story += f"<br>• Le prix reste sous le Midnight Open ({mo:.2f}) "
            story += f"<br>• Tout retracement ne dépasse pas la zone Premium (au-dessus de {mid:.2f}) "
            story += f"<br>• Un FVG baissier (SIBI) frais sert de résistance "
            story += f"<br>• Entrée optimale : retracement vers OTE 70.5% ({ote_lvl:.2f}) dans un SIBI "
            story += f"<br>• Stop Loss : au-dessus du dernier SWH ({swh:.2f}) + spread "
            story += f"<br>• Take Profit : SSL à {ssl:.2f} "
        else:
            story += "Le biais n'est pas clairement directionnel. La continuation dépend de la résolution de la consolidation actuelle. "
            story += "Surveiller un BOS clair suivi d'un Displacement pour déterminer la direction. "

        # --- SCÉNARIO B: RENVERSEMENT ---
        story += f"<br><br><b style='color:#ef5350'>◀ SCÉNARIO B — RENVERSEMENT</b><br>"
        if is_bull:
            story += f"Un renversement baissier serait envisageable si : "
            story += f"<br>• Le prix casse le SWL ({swl:.2f}) avec <b>Displacement</b> (fermeture de corps nette en dessous) "
            story += f"<br>• Un <b>MSS Bearish</b> se forme, suivi d'un FVG baissier (SIBI) "
            story += f"<br>• Le prix rejette violemment le BSL ({bsl:.2f}) — "
            story += "une mèche longue au-dessus suivie d'une clôture en dessous = <b>SFP/Turtle Soup baissier</b> "
            if ts == "BEARISH_TURTLE_SOUP":
                story += "<br>⚠️ <b>ATTENTION : Un Turtle Soup Baissier est ACTIF</b> — le renversement est possible ! "
            story += f"<br>• L'objectif de renversement serait le SSL à {ssl:.2f} "
            story += f"<br>• Confirmation : perte du Midnight Open ({mo:.2f}) avec volume "
        elif is_bear:
            story += f"Un renversement haussier serait envisageable si : "
            story += f"<br>• Le prix casse le SWH ({swh:.2f}) avec <b>Displacement</b> "
            story += f"<br>• Un <b>MSS Bullish</b> se forme avec un FVG haussier (BISI) "
            story += f"<br>• Le prix rejette le SSL ({ssl:.2f}) — mèche sous + clôture au-dessus = <b>SFP haussier</b> "
            if ts == "BULLISH_TURTLE_SOUP":
                story += "<br>⚠️ <b>ATTENTION : Un Turtle Soup Haussier est ACTIF</b> — le renversement est probable ! "
            story += f"<br>• L'objectif de renversement serait le BSL à {bsl:.2f} "
            story += f"<br>• Confirmation : reconquête du Midnight Open ({mo:.2f}) "
        else:
            story += "Sans biais établi, les deux directions sont possibles. "
            story += f"<br>• Un BOS + Displacement au-dessus de {swh:.2f} → Scénario haussier vers {bsl:.2f} "
            story += f"<br>• Un BOS + Displacement en dessous de {swl:.2f} → Scénario baissier vers {ssl:.2f} "

        # ---- SECTION 7: VERDICT FINAL ----
        story += f"<br><br><hr style='border-color:#2a2e39'>"
        story += f"<b style='color:#2962ff;'>⚖️ VERDICT ({score}/100) : {verdict}</b><br>"
        if score >= score_execute:
            story += "Les conditions sont réunies pour une <b>exécution de haute confiance</b>. "
            story += "Le biais HTF, la structure, le timing et la liquidité convergent vers un setup A+. "
            story += "Exécuter avec discipline au niveau du FVG/OB en Killzone. "
        elif score >= score_limit:
            story += "Le setup est prometteur mais incomplet. Placer un <b>ordre limite au OTE 70.5%</b> "
            story += f"({ote_lvl:.2f}) et attendre que le prix vienne à vous. Ne pas chasser le prix. "
        else:
            story += "<b>Ne pas trader.</b> La confiance est insuffisante. "
            story += "Le marché est probablement en mode 'Seek and Destroy' où les algorithmes chassent la liquidité des deux côtés. "
            story += "Attendre que le prix atteigne un POI majeur sur un HTF ou qu'un MSS clair se dessine avec un Displacement. "

        return story
