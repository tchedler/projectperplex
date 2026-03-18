"""
interface/chart_builder.py — Graphiques Plotly annotés ICT
===========================================================
Construit le graphique candlestick enrichi ICT
à partir des données du market_state.pkl (App2 KB5).

Annotations :
  - Sessions ICT colorées (Asie / Londres / NY AM / NY PM)
  - Dealing Range (Premium / EQ 50% / Discount)
  - FVG actifs (BISI / SIBI) avec ligne CE
  - Order Blocks (BULL / BEAR / BREAKER)
  - BSL / SSL (lignes de liquidité)
  - Structure MSS / BOS / CHoCH
  - Entry / SL / TP actifs
  - Prix actuel

Utilisation :
    from interface.chart_builder import build_chart_from_pkl
    fig = build_chart_from_pkl(pair_data, tf="H1", symbol="XAUUSDm")
    st.plotly_chart(fig, use_container_width=True)
"""

import logging
import pandas as pd

logger = logging.getLogger(__name__)

try:
    import plotly.graph_objects as go
    PLOTLY_OK = True
except ImportError:
    PLOTLY_OK = False

# ── Palette de couleurs ──────────────────────────────────────
C = {
    "bull":            "#26a69a",
    "bear":            "#ef5350",
    "fvg_bull_fill":   "rgba(0,200,100,0.13)",
    "fvg_bear_fill":   "rgba(239,83,80,0.13)",
    "fvg_bull_line":   "#00c864",
    "fvg_bear_line":   "#ef5350",
    "ob_bull_fill":    "rgba(41,98,255,0.18)",
    "ob_bear_fill":    "rgba(239,83,80,0.18)",
    "ob_brk_fill":     "rgba(240,180,40,0.15)",
    "ob_bull_line":    "#2962ff",
    "ob_bear_line":    "#ef5350",
    "ob_brk_line":     "#f0b429",
    "bsl":             "#ef5350",
    "ssl":             "#26a69a",
    "eq_line":         "rgba(180,180,180,0.35)",
    "premium_fill":    "rgba(239,83,80,0.04)",
    "discount_fill":   "rgba(38,166,154,0.04)",
    "bg":              "#131722",
    "grid":            "rgba(42,46,57,0.4)",
    "grid_x":          "rgba(42,46,57,0.25)",
    "text":            "#d1d4dc",
    "subtext":         "#848e9c",
    "asia":            "rgba(100,100,180,0.04)",
    "london":          "rgba(41,98,255,0.06)",
    "ny_am":           "rgba(0,200,100,0.06)",
    "ny_pm":           "rgba(255,160,0,0.05)",
    "entry":           "#4dabff",
    "sl":              "#ef5350",
    "tp":              "#00c864",
    "price_up_bg":     "rgba(38,166,154,0.9)",
    "price_dn_bg":     "rgba(239,83,80,0.9)",
}

N_CANDLES = {
    "MN": 24, "W1": 52, "D1": 90,
    "H4": 100, "H1": 120, "M15": 150, "M5": 180, "M1": 200,
}

TF_LABELS = {
    "MN": "1M", "W1": "1W", "D1": "1D",
    "H4": "4H", "H1": "1H", "M15": "15m", "M5": "5m",
}

VERDICT_COLORS = {
    "EXECUTE":  "#00ff88",
    "WATCH":    "#f0b429",
    "NO_TRADE": "#ef5350",
    "BLOCKED":  "#848e9c",
}


# ════════════════════════════════════════════════════════════
# UTILITAIRES
# ════════════════════════════════════════════════════════════

def _safe_float(v, default=0.0) -> float:
    try:
        f = float(v)
        return f if f == f else default   # NaN check
    except Exception:
        return default


def _price_fmt(symbol: str, price: float) -> str:
    s = symbol.upper()
    if any(x in s for x in ["BTC", "ETH", "USTECH", "US500", "US30", "DE30", "UK100", "USOIL", "UKOIL"]):
        return f"{price:,.2f}"
    if "JPY" in s:
        return f"{price:.3f}"
    if any(x in s for x in ["XAU", "XAG"]):
        return f"{price:.2f}"
    return f"{price:.5f}"


def _to_df(candles: list) -> pd.DataFrame:
    """Liste de dicts → DataFrame OHLCV avec index DatetimeIndex UTC."""
    if not candles:
        return pd.DataFrame()
    df = pd.DataFrame(candles)
    df["time"] = pd.to_datetime(df["time"], utc=True)
    df = df.set_index("time").sort_index()
    df.columns = [c.capitalize() for c in df.columns]
    for col in ["Open", "High", "Low", "Close", "Volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _to_ny(df: pd.DataFrame) -> pd.DataFrame:
    """Convertit l'index UTC → heure New York."""
    try:
        import pytz
        ny = pytz.timezone("America/New_York")
        if df.index.tzinfo is None:
            df.index = df.index.tz_localize("UTC").tz_convert(ny)
        else:
            df.index = df.index.tz_convert(ny)
    except Exception:
        pass
    return df


def _norm_ts(ts, ref_tz=None):
    """Normalise un timestamp vers le tz de référence."""
    try:
        t = pd.to_datetime(ts)
        if t.tzinfo is None:
            t = t.tz_localize("UTC")
        if ref_tz is not None:
            t = t.tz_convert(ref_tz)
        return t
    except Exception:
        return None


# ════════════════════════════════════════════════════════════
# COUCHES D'ANNOTATIONS
# ════════════════════════════════════════════════════════════

def _layer_sessions(fig, df, tf):
    """COUCHE 1 — Fonds de sessions ICT colorées."""
    if tf in ("MN", "W1", "D1"):
        return
    try:
        unique_dates = pd.Series(df.index.date).unique()
        recent = unique_dates[-5:] if len(unique_dates) > 5 else unique_dates
        for d in recent:
            ds = str(d)
            pd_ = str(pd.Timestamp(d) - pd.Timedelta(days=1))
            fig.add_vrect(x0=f"{pd_} 20:00", x1=f"{ds} 02:00",
                          fillcolor=C["asia"],   line_width=0, layer="below")
            fig.add_vrect(x0=f"{ds} 02:00",   x1=f"{ds} 05:00",
                          fillcolor=C["london"], line_width=0, layer="below")
            fig.add_vrect(x0=f"{ds} 07:00",   x1=f"{ds} 10:00",
                          fillcolor=C["ny_am"],  line_width=0, layer="below")
            fig.add_vrect(x0=f"{ds} 13:00",   x1=f"{ds} 16:00",
                          fillcolor=C["ny_pm"],  line_width=0, layer="below")
    except Exception as e:
        logger.debug(f"Sessions: {e}")


def _layer_dealing_range(fig, df):
    """COUCHE 2 — Premium / EQ 50% / Discount."""
    try:
        swh    = float(df["High"].max())
        swl    = float(df["Low"].min())
        mid    = (swh + swl) / 2
        first  = df.index[0]
        last   = df.index[-1]

        fig.add_hrect(y0=mid, y1=swh, fillcolor=C["premium_fill"],  line_width=0, layer="below")
        fig.add_hrect(y0=swl, y1=mid, fillcolor=C["discount_fill"], line_width=0, layer="below")
        fig.add_shape(type="line", x0=first, y0=mid, x1=last, y1=mid,
                      line=dict(color=C["eq_line"], width=1, dash="dot"),
                      xref="x", yref="y", layer="below")
        fig.add_annotation(x=last, y=mid, text="  EQ 50%", showarrow=False,
                           font=dict(size=9, color="rgba(180,180,180,0.6)"),
                           xanchor="left", yanchor="middle",
                           xref="x", yref="y", xshift=4)
    except Exception as e:
        logger.debug(f"Dealing range: {e}")


def _layer_fvg(fig, df, structures):
    """COUCHE 3 — FVG (BISI / SIBI) avec zone + ligne CE."""
    fvgs = structures.get("fvg", []) if structures else []
    if not fvgs:
        return
    tz    = df.index.tzinfo
    start = df.index[0]
    last  = df.index[-1]

    for f in fvgs[-6:]:
        try:
            if not isinstance(f, dict):
                continue
            ts = _norm_ts(f.get("index") or f.get("time") or f.get("ts"), tz)
            if ts is None or ts < start:
                continue
            top = _safe_float(f.get("top") or f.get("high"))
            bot = _safe_float(f.get("bot") or f.get("low"))
            ce  = _safe_float(f.get("ce"), (top + bot) / 2)
            if top <= 0 or bot <= 0:
                continue
            is_bull = any(x in str(f.get("type", "")).upper() for x in ["BISI", "BULL"])
            fc  = C["fvg_bull_fill"] if is_bull else C["fvg_bear_fill"]
            lc  = C["fvg_bull_line"] if is_bull else C["fvg_bear_line"]
            lbl = "BISI FVG"        if is_bull else "SIBI FVG"

            fig.add_shape(type="rect", x0=ts, y0=bot, x1=last, y1=top,
                          fillcolor=fc, line=dict(color=lc, width=0.8, dash="dot"),
                          xref="x", yref="y", layer="above")
            fig.add_shape(type="line", x0=ts, y0=ce, x1=last, y1=ce,
                          line=dict(color=lc, width=0.6, dash="dash"),
                          xref="x", yref="y")
            fig.add_annotation(x=last, y=ce, text=f"  {lbl}", showarrow=False,
                               font=dict(size=8, color=lc),
                               xanchor="left", yanchor="middle",
                               xref="x", yref="y", xshift=4)
        except Exception as e:
            logger.debug(f"FVG: {e}")


def _layer_ob(fig, df, structures):
    """COUCHE 4 — Order Blocks (BULL / BEAR / BREAKER)."""
    obs = structures.get("ob", []) if structures else []
    if not obs:
        return
    tz    = df.index.tzinfo
    start = df.index[0]
    last  = df.index[-1]

    for b in obs[-4:]:
        try:
            if not isinstance(b, dict):
                continue
            ts = _norm_ts(b.get("index") or b.get("time") or b.get("ts"), tz)
            if ts is None or ts < start:
                continue
            ob_type  = str(b.get("type", "")).upper()
            is_bull  = "BULL" in ob_type
            is_brk   = "BREAKER" in ob_type or "BRK" in ob_type

            if is_brk:
                fc, lc, lbl = C["ob_brk_fill"], C["ob_brk_line"], ("BRK ↑" if is_bull else "BRK ↓")
            elif is_bull:
                fc, lc, lbl = C["ob_bull_fill"], C["ob_bull_line"], "BULL OB"
            else:
                fc, lc, lbl = C["ob_bear_fill"], C["ob_bear_line"], "BEAR OB"

            zone = b.get("refined_zone") or b.get("zone")
            if zone and len(zone) >= 2:
                z0, z1 = _safe_float(zone[0]), _safe_float(zone[1])
            else:
                z0 = _safe_float(b.get("low")  or b.get("bot"))
                z1 = _safe_float(b.get("high") or b.get("top"))
            if z0 <= 0 or z1 <= 0:
                continue

            fig.add_shape(type="rect", x0=ts, y0=z0, x1=last, y1=z1,
                          fillcolor=fc, line=dict(color=lc, width=1.2),
                          xref="x", yref="y", layer="above")
            fig.add_annotation(x=last, y=(z0 + z1) / 2, text=f"  {lbl}",
                               showarrow=False,
                               font=dict(size=9, color=lc, family="monospace"),
                               xanchor="left", yanchor="middle",
                               xref="x", yref="y",
                               bgcolor="rgba(6,9,14,0.6)", xshift=4)
        except Exception as e:
            logger.debug(f"OB: {e}")


def _layer_liquidity(fig, df, structures, bias_result):
    """COUCHE 5 — BSL / SSL / EQH / EQL."""
    first = df.index[0]
    last  = df.index[-1]

    # ── BSL / SSL ─────────────────────────────────────────────
    bsl = ssl = 0.0
    liq = structures.get("liq", {}) if structures else {}
    if isinstance(liq, dict):
        erl = liq.get("erl", {})
        if isinstance(erl, dict):
            bsl = _safe_float(erl.get("high"))
            ssl = _safe_float(erl.get("low"))

    # Fallback → day_high / day_low depuis bias_result
    if bsl <= 0 or ssl <= 0:
        pdz = (bias_result or {}).get("pd_zone", {})
        if isinstance(pdz, dict):
            if bsl <= 0: bsl = _safe_float(pdz.get("day_high"))
            if ssl <= 0: ssl = _safe_float(pdz.get("day_low"))

    # Fallback final → max/min df
    if bsl <= 0: bsl = float(df["High"].max())
    if ssl <= 0: ssl = float(df["Low"].min())

    try:
        fig.add_shape(type="line", x0=first, y0=bsl, x1=last, y1=bsl,
                      line=dict(color=C["bsl"], width=1.8, dash="dash"),
                      xref="x", yref="y")
        fig.add_annotation(x=last, y=bsl, text="  🔴 BSL", showarrow=False,
                           font=dict(size=10, color=C["bsl"], family="monospace"),
                           xanchor="left", yanchor="middle", xref="x", yref="y",
                           bgcolor="rgba(239,83,80,0.15)", bordercolor=C["bsl"],
                           borderwidth=1, xshift=4)
        fig.add_shape(type="line", x0=first, y0=ssl, x1=last, y1=ssl,
                      line=dict(color=C["ssl"], width=1.8, dash="dash"),
                      xref="x", yref="y")
        fig.add_annotation(x=last, y=ssl, text="  🟢 SSL", showarrow=False,
                           font=dict(size=10, color=C["ssl"], family="monospace"),
                           xanchor="left", yanchor="middle", xref="x", yref="y",
                           bgcolor="rgba(38,166,154,0.15)", bordercolor=C["ssl"],
                           borderwidth=1, xshift=4)
    except Exception as e:
        logger.debug(f"BSL/SSL: {e}")

    # ── EQH / EQL ─────────────────────────────────────────────
    if isinstance(liq, dict):
        for eq in liq.get("eqh", [])[:2]:
            try:
                if not isinstance(eq, dict) or eq.get("swept"):
                    continue
                p = _safe_float(eq.get("price"))
                if p <= 0: continue
                fig.add_shape(type="line", x0=first, y0=p, x1=last, y1=p,
                              line=dict(color="rgba(239,83,80,0.6)", width=1, dash="dot"),
                              xref="x", yref="y")
                fig.add_annotation(x=last, y=p, text="  EQH", showarrow=False,
                                   font=dict(size=8, color="rgba(239,83,80,0.8)"),
                                   xanchor="left", yanchor="middle",
                                   xref="x", yref="y", xshift=4)
            except Exception:
                pass
        for eq in liq.get("eql", [])[:2]:
            try:
                if not isinstance(eq, dict) or eq.get("swept"):
                    continue
                p = _safe_float(eq.get("price"))
                if p <= 0: continue
                fig.add_shape(type="line", x0=first, y0=p, x1=last, y1=p,
                              line=dict(color="rgba(38,166,154,0.6)", width=1, dash="dot"),
                              xref="x", yref="y")
                fig.add_annotation(x=last, y=p, text="  EQL", showarrow=False,
                                   font=dict(size=8, color="rgba(38,166,154,0.8)"),
                                   xanchor="left", yanchor="middle",
                                   xref="x", yref="y", xshift=4)
            except Exception:
                pass


def _layer_structure(fig, df, bias_result):
    """COUCHE 6 — Label MSS / BOS / CHoCH depuis bias_shift."""
    try:
        bs = (bias_result or {}).get("bias_shift", {})
        if not isinstance(bs, dict) or not bs.get("detected"):
            return
        stype     = bs.get("type", "")
        direction = bs.get("direction", "")
        if not stype:
            return
        color = "#00c864" if "BULL" in direction else "#ef5350"
        y_pos = float(df["High"].quantile(0.8)) if "BULL" in direction else float(df["Low"].quantile(0.2))
        x_pos = df.index[int(len(df) * 0.72)]
        fig.add_annotation(x=x_pos, y=y_pos, text=f"◀ {stype}",
                           showarrow=False,
                           font=dict(size=10, color=color, family="monospace"),
                           xref="x", yref="y",
                           bgcolor="rgba(6,9,14,0.8)",
                           bordercolor=color, borderwidth=1, borderpad=3)
    except Exception as e:
        logger.debug(f"Structure: {e}")


def _layer_entry_levels(fig, df, pair_data, symbol):
    """COUCHE 7 — Entry / SL / TP."""
    first = df.index[0]
    last  = df.index[-1]
    entry = _safe_float(pair_data.get("entry"))
    sl    = _safe_float(pair_data.get("sl"))
    tp    = _safe_float(pair_data.get("tp"))

    for val, color, label in [
        (entry, C["entry"], "▲ ENTRY"),
        (sl,    C["sl"],    "⛔ SL"),
        (tp,    C["tp"],    "🎯 TP"),
    ]:
        try:
            if val <= 0:
                continue
            fig.add_shape(type="line", x0=first, y0=val, x1=last, y1=val,
                          line=dict(color=color, width=1.5, dash="dash"),
                          xref="x", yref="y")
            fig.add_annotation(x=last, y=val,
                               text=f"  {label} {_price_fmt(symbol, val)}",
                               showarrow=False,
                               font=dict(size=9, color=color, family="monospace"),
                               xanchor="left", yanchor="middle",
                               xref="x", yref="y",
                               bgcolor="rgba(6,9,14,0.7)", xshift=4)
        except Exception:
            pass


def _layer_current_price(fig, df, symbol):
    """COUCHE 9 — Prix actuel avec badge coloré."""
    try:
        price = float(df["Close"].iloc[-1])
        # Tenter prix live MT5
        try:
            import MetaTrader5 as mt5
            tick = mt5.symbol_info_tick(symbol)
            if tick:
                price = float(tick.bid)
        except Exception:
            pass
        last_open = float(df["Open"].iloc[-1])
        first     = df.index[0]
        last      = df.index[-1]
        bg        = C["price_up_bg"] if price >= last_open else C["price_dn_bg"]
        fig.add_shape(type="line", x0=first, y0=price, x1=last, y1=price,
                      line=dict(color="rgba(255,255,255,0.85)", width=1.2),
                      xref="x", yref="y")
        fig.add_annotation(x=last, y=price,
                           text=f"  {_price_fmt(symbol, price)}  ",
                           showarrow=False,
                           font=dict(size=11, color="white", family="monospace"),
                           xanchor="left", yanchor="middle",
                           xref="x", yref="y",
                           bgcolor=bg, bordercolor="rgba(255,255,255,0.3)",
                           borderwidth=1, xshift=4)
    except Exception as e:
        logger.debug(f"Current price: {e}")


# ════════════════════════════════════════════════════════════
# FONCTION PRINCIPALE
# ════════════════════════════════════════════════════════════

def build_chart_from_pkl(pair_data: dict,
                         tf: str = "H1",
                         symbol: str = "") -> "go.Figure | None":
    """
    Construit le graphique Plotly ICT complet depuis pair_data du bridge.

    Args:
        pair_data : données d'une paire depuis get_dashboard_data_from_cache()
                    champs utilisés : candles, structures, bias_result (via bridge),
                                      entry, sl, tp, rr, best_score, verdict, direction
        tf        : timeframe affiché ("H1", "M15", "H4", "D1", "W1", "MN")
        symbol    : nom du symbole Exness (ex: "XAUUSDm")

    Returns:
        go.Figure prêt pour st.plotly_chart() ou None si Plotly absent
    """
    if not PLOTLY_OK:
        return None

    candles = pair_data.get("candles", [])

    # ── Figure vide si pas de données ────────────────────────
    if not candles:
        fig = go.Figure()
        fig.add_annotation(
            x=0.5, y=0.5, xref="paper", yref="paper",
            text="⏳ Aucune bougie — démarrez le bot pour charger les données",
            showarrow=False, font=dict(size=14, color=C["subtext"])
        )
        fig.update_layout(
            template="plotly_dark", height=420,
            paper_bgcolor=C["bg"], plot_bgcolor=C["bg"]
        )
        return fig

    # ── Préparer le DataFrame ─────────────────────────────────
    df = _to_df(candles)
    if df.empty:
        return go.Figure()
    df = _to_ny(df)
    df = df.tail(N_CANDLES.get(tf, 120)).copy()

    # ── Extraire les structures du kb5_result brut dans pair_data
    # Le bridge stocke structures depuis kb5_result["structures"]
    structures  = pair_data.get("structures", {})
    # Pour bias_result, on utilise ce que le bridge a parsé
    # On reconstruit un bias_result minimal depuis les champs disponibles
    bias_result = {
        "bias_shift": {},
        "pd_zone": {
            "day_high": float(df["High"].max()),
            "day_low":  float(df["Low"].min()),
        },
    }
    # Si le bridge a stocké des données plus riches, on les utilise
    br_raw = pair_data.get("_bias_raw", {})
    if br_raw:
        bias_result.update(br_raw)

    # ── Créer le graphique ────────────────────────────────────
    fig = go.Figure()

    _layer_sessions(fig, df, tf)
    _layer_dealing_range(fig, df)
    _layer_fvg(fig, df, structures)
    _layer_ob(fig, df, structures)
    _layer_liquidity(fig, df, structures, bias_result)
    _layer_structure(fig, df, bias_result)
    _layer_entry_levels(fig, df, pair_data, symbol)

    # ── Bougies (au-dessus de tout) ───────────────────────────
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df["Open"], high=df["High"],
        low=df["Low"],   close=df["Close"],
        name=symbol,
        increasing=dict(line=dict(color=C["bull"], width=1.5), fillcolor=C["bull"]),
        decreasing=dict(line=dict(color=C["bear"], width=1.5), fillcolor=C["bear"]),
        whiskerwidth=0.3,
    ))

    _layer_current_price(fig, df, symbol)

    # ── Pas de rangebreaks ───────────────────────────────────
    # Les rangebreaks Plotly créent des vides parasites avec le DST américain.
    # L'axe date natif gère les weekends proprement — petits espaces naturels.

    # ── Layout final style TradingView ───────────────────────
    tf_lbl    = TF_LABELS.get(tf, tf)
    score     = pair_data.get("best_score", 0)
    verdict   = pair_data.get("verdict", "NO_TRADE")
    direction = pair_data.get("direction", "NEUTRAL")
    sc_color  = VERDICT_COLORS.get(verdict, C["subtext"])
    bias_icon = "🟢" if "BULL" in direction else ("🔴" if "BEAR" in direction else "⚪")

    fig.update_layout(
        template="plotly_dark",
        height=600,
        margin=dict(l=10, r=140, b=30, t=44),
        xaxis_rangeslider_visible=False,
        showlegend=False,
        paper_bgcolor=C["bg"],
        plot_bgcolor=C["bg"],
        dragmode="pan",
        uirevision=symbol + tf,
        hovermode="x unified",
        title=dict(
            text=(
                f"<b>{symbol}</b>&nbsp;&nbsp;"
                f"<span style='color:{C['subtext']}'>{tf_lbl}</span>&nbsp;&nbsp;"
                f"{bias_icon}&nbsp;&nbsp;"
                f"<span style='color:{sc_color};font-size:0.85em'>"
                f"Score {score}/100 — {verdict}</span>"
            ),
            font=dict(size=13, color=C["text"]),
            x=0.01, y=0.99, xanchor="left", yanchor="top",
        ),
        yaxis=dict(
            gridcolor=C["grid"], side="right",
            fixedrange=False, zeroline=False,
            tickfont=dict(size=10, color=C["subtext"]),
        ),
        xaxis=dict(
            gridcolor=C["grid_x"],
            fixedrange=False, type="date",
            tickmode="auto", nticks=7, showgrid=True,
            tickfont=dict(size=10, color=C["subtext"]),
            tickformat="%d %b\n%H:%M" if tf not in ("MN", "W1", "D1") else "%b %Y",
        ),
        hoverlabel=dict(
            bgcolor="#1e222d", bordercolor="#2a2e39",
            font=dict(size=11, color=C["text"]),
        ),
    )

    return fig
