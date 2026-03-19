"""
interface/bot_settings.py — Paramètres Bot Sentinel Pro KB5 (Version Finale Fusionnée)
========================================================================================
Meilleur des deux versions :
  - Structure 12 sections en expanders pliables (lisibilité)
  - Checklist concepts structurée avec compteur temps réel
  - Cartes profils visuelles avec RR/DD
  - pathlib pour les chemins (robustesse)
  - Gestion erreurs complète avec timeout
  - CSS dark mode professionnel
  - Test Telegram robuste avec timestamp
  - Boutons démarrer/arrêter désactivés selon état
"""

import os
import sys
import json
import logging
import subprocess
from pathlib import Path
from datetime import datetime

import streamlit as st

from dotenv import load_dotenv
import os
load_dotenv()

import MetaTrader5 as mt5
if mt5.initialize(path=os.getenv("MT5_PATH")):
    mt5.login(int(os.getenv("MT5_LOGIN")), 
              password=os.getenv("MT5_PASSWORD"),
              server=os.getenv("MT5_SERVER"))
    st.sidebar.success("✅ Exness MT5 Trial15 LIVE")
else:
    st.sidebar.warning("⚠️ MT5 Trial15 démo")
import google.generativeai as genai
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel(os.getenv("GEMINI_MODEL"))


logger = logging.getLogger(__name__)

# ── Chemins (pathlib — plus robuste) ────────────────────────
BASE_DIR    = Path(__file__).parent.parent
PID_FILE    = BASE_DIR / "data" / "bot.pid"
CONFIG_FILE = BASE_DIR / "data" / "bot_config.json"

# ── Imports optionnels ───────────────────────────────────────
try:
    from config.settings_manager import SCHOOLS, PROFILES, AVAILABLE_PAIRS
    SETTINGS_OK = True
except ImportError:
    SETTINGS_OK = False
    SCHOOLS, PROFILES, AVAILABLE_PAIRS = {}, {}, {}

# ============================================================
# CONSTANTES & LABELS
# ============================================================

PROFILE_LABELS = {
    "SCALP":      "⚡ Scalp (M1–M5, Silver Bullet)",
    "DAY_TRADE":  "📅 Day Trade (M5–D1, Londres + NY) ← Recommandé",
    "SWING":      "🌊 Swing Trading (S2–S1, plusieurs jours)",
    "LONG_TERM":  "🏔️ Long Terme (D1–MN, positions mensuelles)",
    "CUSTOM":     "🎛️ Custom (profil personnalisé)",
}

MODE_LABELS = {
    "PAPER":     "🟥 Paper Trading (simulation — aucun ordre réel)",
    "SEMI_AUTO": "🟨 Semi-Automatique (alerte + vous validez)",
    "FULL_AUTO": "🟩 Full Automatique (bot trade seul 24/7)",
}

SYMBOL_LIST = [
    "EURUSDm", "GBPUSDm", "USDJPYm", "USDCHFm", "USDCADm",
    "AUDUSDm", "NZDUSDm", "GBPJPYm", "EURJPYm", "EURGBPm",
    "USTECm",  "US500m",  "US30m",   "DE30m",   "UK100m",
    "XAUUSDm", "XAGUSDm", "USOILm",  "UKOILm",
    "BTCUSDm", "ETHUSDm", "DXYm",
]

# ── Checklist concepts (clés courtes pour usage dans le code) ─
CONCEPTS = {
    "📐 ICT Core": {
        "fvg":           ("Fair Value Gap (FVG)",         "BISI/SIBI — zones de déséquilibre de prix"),
        "ob":            ("Order Block (OB)",              "Bullish / Bearish / Breaker Blocks institutionnels"),
        "liquidity":     ("Liquidity Sweep",               "PDH/PDL, EQH/EQL, Turtle Soup — prise de liquidité"),
        "mss":           ("Market Structure Shift (MSS)",  "Cassure de structure FORTE avec momentum"),
        "choch":         ("Change of Character (CHoCH)",   "Premier signe de retournement LTF"),
        "smt":           ("SMT Divergence",                "Corrélation intermarché inversée (EUR vs GBP)"),
        "bos":           ("BOS — Break of Structure",      "Cassure de structure directionnelle confirmée"),
        "amd":           ("AMD / Power of 3",              "Accumulation → Manipulation → Distribution"),
        "silver_bullet": ("Silver Bullet ICT",             "Fenêtres 10h–11h / 14h–15h NY haute probabilité"),
        "macros_ict":    ("Macros ICT",                    "Fenêtres algorithmiques de 20–27 min"),
        "midnight_open": ("Midnight Open",                 "Pivot institutionnel 00h00 UTC"),
        "ote":           ("OTE Fibonacci 62–79%",          "Zone d'entrée optimale ICT"),
        "irl":           ("IRL — Internal Liquidity",      "Cibles TP internes (FVG ouverts + Swing internes)"),
        "pd_zone":       ("Premium / Discount",            "Entrée en Discount (BULL) ou Premium (BEAR)"),
        "cbdr":          ("CBDR",                          "Central Bank Dealers Range (17h–20h EST)"),
        "cisd":          ("CISD",                          "Change in State of Delivery (M5/M1)"),
    },
    "🔷 SMC": {
        "inducement":    ("Inducement (IDM)",              "Piège liquidité interne avant le vrai mouvement"),
        "equal_hl":      ("Equal Highs / Equal Lows",      "Faux supports/résistances — pools de liquidité"),
        "ob_smc":        ("Order Blocks SMC",              "Zones d'offre et demande institutionnelles"),
        "fvg_smc":       ("FVG / Imbalances SMC",          "Déséquilibres de prix vision SMC"),
        "bpr":           ("Balanced Price Range (BPR)",    "Chevauchement de deux FVG opposés"),
        "pd_smc":        ("Premium/Discount SMC",          "Positionnement par rapport au range 50%"),
        "choch_smc":     ("CHoCH SMC",                     "Retournement précoce vision Smart Money"),
    },
    "📊 Price Action": {
        "engulfing":     ("Bougie Engulfing",              "Engulfing Bullish/Bearish — confirmation direction"),
        "trendlines":    ("Lignes de Tendance",            "Trendlines validées (3 touches minimum)"),
        "round_numbers": ("Chiffres Ronds",                "Niveaux .00 / .20 / .50 / .80 psychologiques"),
        "pin_bar":       ("Pin Bar / Doji",                "Mèches de rejet longues — retournement"),
        "inside_bar":    ("Inside Bar",                    "Consolidation avant expansion directionnelle"),
        "sr_levels":     ("Support / Résistance",          "Niveaux S/R classiques multi-timeframes"),
    },
    "🌍 Macro & Institutionnel": {
        "cot":           ("COT & Saisonnalité",            "Biais institutionnel mensuel (Large Speculators)"),
        "perplexity":    ("Perplexity Pro (Macro temps réel)", "Contexte FOMC/CPI/NFP via IA en temps réel"),
        "news_filter":   ("Filtre News ForexFactory",      "Bloquer trades avant NFP/FOMC/CPI"),
        "htf_bias":      ("Biais HTF obligatoire",         "Ne trader QUE dans la direction HTF confirmée"),
    },
    "📅 Sessions & Timing": {
        "session_london":("Session Londres",               "07h–16h UTC — session la plus liquide"),
        "session_ny":    ("Session New York",              "13h–22h UTC — fort volume institutionnel"),
        "session_asia":  ("Session Asie",                  "00h–09h UTC — range, accumulation"),
        "overlap_lnny":  ("Overlap Londres+NY",            "13h–16h UTC — RECOMMANDÉ, meilleurs setups"),
        "sb_london":     ("Silver Bullet London",          "03h–04h NY — haute probabilité"),
        "sb_am":         ("Silver Bullet AM",              "10h–11h NY — matin New York"),
        "sb_pm":         ("Silver Bullet PM",              "14h–15h NY — après-midi New York"),
    },
}

# Profils rapides
PROFIL_CONCEPTS = {
    "ICT Pur": [
        "fvg","ob","liquidity","mss","choch","smt","bos","amd",
        "silver_bullet","macros_ict","midnight_open","ote","irl",
        "pd_zone","cbdr","session_london","session_ny","overlap_lnny",
        "htf_bias","news_filter",
    ],
    "SMC+ICT": [
        "fvg","ob","liquidity","mss","choch","smt","bos","amd",
        "silver_bullet","ote","irl","pd_zone","inducement","equal_hl",
        "ob_smc","fvg_smc","bpr","session_london","session_ny",
        "overlap_lnny","htf_bias","news_filter",
    ],
    "PA": [
        "fvg","ob","liquidity","mss","ote","pd_zone","engulfing",
        "trendlines","round_numbers","pin_bar","sr_levels",
        "session_london","session_ny","htf_bias",
    ],
    "Tout": [c for cat in CONCEPTS.values() for c in cat.keys()],
}

# KillSwitches
KS_LIST = [
    ("KS1", "Spread excessif",        "Bloqué si spread trop large"),
    ("KS2", "Volatilité extrême",     "Bloqué si ATR spike × 3"),
    ("KS3", "News haute impact",       "Bloqué ±30 min autour d'une news"),
    ("KS4", "Hors Killzone ICT",       "Avertissement si hors session"),
    ("KS5", "Drawdown journalier max", "Bloqué si DD du jour dépassé"),
    ("KS6", "Contre-tendance HTF",     "Bloqué si biais HTF opposé"),
    ("KS7", "Trop de positions",       "Bloqué si max positions atteint"),
    ("KS8", "Corrélation exposée",    "Avertissement corrélation excessive"),
    ("KS9", "Phase Accumulation",      "Bloqué si marché en range sans impulsion"),
]

# BehaviourShield
BS_LIST = [
    ("stop_hunt",     "Stop Hunt Detection",     "Détecte et bloque les entrées sur des stop hunts"),
    ("fake_breakout", "Fake Breakout Filter",    "Filtre les fausses cassures sans displacement"),
    ("liquidity_grab","Liquidity Grab Filter",   "Bloque si prise de liquidité en cours"),
    ("news_spike",    "News Spike Filter",       "Bloque pendant les spikes de news haute impact"),
    ("overextension", "Overextension Filter",    "Bloque si prix trop étiré (ATR × 3+)"),
    ("revenge_trade", "Revenge Trade Blocker",   "Bloque après 2 pertes consécutives rapides"),
    ("duplicate",     "Duplicate Order Blocker", "Empêche plusieurs ordres sur la même paire"),
    ("staleness",     "Staleness Filter",        "Rejette les signaux vieux de plus de 3 bougies"),
]

# ============================================================
# CONTRÔLE DU BOT (pathlib + gestion erreurs robuste)
# ============================================================

def get_bot_pid() -> int | None:
    if PID_FILE.exists():
        try:
            return int(PID_FILE.read_text().strip())
        except (ValueError, IOError):
            return None
    return None

def is_bot_running() -> bool:
    pid = get_bot_pid()
    if not pid:
        return False
    try:
        if os.name == "nt":
            output = subprocess.check_output(
                f'tasklist /FI "PID eq {pid}" /NH',
                shell=True, timeout=5
            ).decode("utf-8", errors="ignore")
            return str(pid) in output
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False

def start_bot_process() -> bool:
    if is_bot_running():
        return False
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000) if os.name == "nt" else 0
    env   = os.environ.copy()
    env["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
    env["PYTHONPATH"] = str(BASE_DIR)
    try:
        proc = subprocess.Popen(
            [sys.executable, str(BASE_DIR / "main.py")],
            creationflags=flags,
            cwd=str(BASE_DIR),
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        PID_FILE.write_text(str(proc.pid))
        return True
    except Exception as e:
        logger.error(f"Erreur démarrage bot : {e}")
        return False

def stop_bot_process() -> bool:
    pid = get_bot_pid()
    if not pid:
        return False
    try:
        if os.name == "nt":
            subprocess.run(
                f"taskkill /PID {pid} /F /T",
                shell=True, timeout=5, check=False
            )
        else:
            import signal
            os.kill(pid, signal.SIGTERM)
    except Exception as e:
        logger.error(f"Erreur arrêt bot : {e}")
    finally:
        if PID_FILE.exists():
            PID_FILE.unlink()
    return True

# ============================================================
# CONFIG JSON
# ============================================================

DEFAULT_CONFIG = {
    "profile": "DAY_TRADE", "op_mode": "PAPER", "mode": "PAPER",
    "symbols_watched": ["XAUUSDm", "EURUSDm", "GBPUSDm"],
    "score_execute": 80, "score_limit": 65,
    "risk_pct": 0.5, "drawdown_max_pct": 3.0, "drawdown_max_week_pct": 6.0,
    "max_positions": 3, "max_session_trades": 3, "max_session_losses": 2,
    "trailing_sl": True, "partial_tp": True, "partial_tp_pct": 50,
    "rr_min": 2.0, "rr_target": 3.0,
    "require_killzone": True, "require_erl": True,
    "require_mss": True, "require_choch": False,
    "disable_spread_check": False, "disable_killzone_check": False,
    "stop_after_losses": True, "account_balance": 463,
    "telegram_enabled": True, "telegram_token": "", "telegram_chat_id": "",
    "llm_provider": "Gemini", "llm_api_key": "",
    "perplexity_enabled": False, "perplexity_api_key": "",
    "cot_enabled": True, "bot_active": False, "full_auto_confirmed": False,
    "disabled_ks": [],
    "active_concepts": list(PROFIL_CONCEPTS["ICT Pur"]),
    "sessions_actives": ["session_london", "session_ny", "overlap_lnny"],
    "behaviour_shield": {
        "stop_hunt": True, "fake_breakout": True, "liquidity_grab": True,
        "news_spike": True, "overextension": True, "revenge_trade": True,
        "duplicate": True, "staleness": True,
    },
    "time_filters": {
        "friday_pm": True, "monday_morning": True, "before_news": True,
    },
}

def load_config() -> dict:
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_FILE.exists():
        try:
            data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            for k, v in DEFAULT_CONFIG.items():
                if k not in data:
                    data[k] = v
            return data
        except Exception as e:
            logger.error(f"Erreur lecture config : {e}")
    return dict(DEFAULT_CONFIG)

def save_config(cfg: dict) -> None:
    try:
        CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_FILE.write_text(
            json.dumps(cfg, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as e:
        logger.error(f"Erreur sauvegarde config : {e}")

# ============================================================
# TEST TELEGRAM (robuste avec timeout)
# ============================================================

def test_telegram(token: str, chat_id: str) -> tuple[bool, str]:
    if not token or not chat_id:
        return False, "Token ou Chat ID manquant"
    try:
        import requests
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": f"🧪 SENTINEL KB5 connecté ✅\nTest : {datetime.now().strftime('%H:%M:%S')}",
                "parse_mode": "HTML",
            },
            timeout=10,
        )
        if 200 <= resp.status_code < 300:
            return True, "Message envoyé ✅"
        return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)[:60]

# ============================================================
# CSS DARK MODE PROFESSIONNEL
# ============================================================

def _inject_css():
    st.markdown("""
    <style>
    .stApp { background-color: #0d1117; color: #d1d4dc; }
    [data-testid="stSidebar"] { background-color: #010409; }
    .stButton > button { border-radius: 8px; font-weight: bold; }
    .stToggle > label { font-weight: bold; color: #00d4ff; }
    .stCheckbox > label { color: #d1d4dc; }
    div[data-testid="stExpander"] {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 8px;
    }
    div[data-testid="stExpander"] summary {
        color: #00ff88;
        font-weight: bold;
    }
    .stSlider > div { color: #d1d4dc; }
    .stSelectbox > div { background: #161b22; }
    </style>
    """, unsafe_allow_html=True)

# ============================================================
# RENDU PRINCIPAL
# ============================================================

def render_bot_settings():
    _inject_css()

    st.markdown("## ⚙️ Paramètres du Bot de Trading ICT/SMC")
    st.markdown("Configurez votre agent avant de le lancer. Toutes les modifications sont sauvegardées automatiquement.")

    cfg = load_config()

    # ════════════════════════════════════════════════════════
    # SECTION A — Profil & Mode
    # ════════════════════════════════════════════════════════
    with st.expander("🎯 Section A — Profil & Mode de trading", expanded=True):

        # Cartes profils préconçus
        st.markdown("**Profils préconçus**")
        PROF_INFO = {
            "ICT Pur":     ("ICT officiel strict", "Score≥80 | RR 2.5x | DD 2%",  80, 2.5, 2.0, 3),
            "SMC+ICT":     ("SMC + ICT combinés",  "Score≥75 | RR 2.0x | DD 3%",  75, 2.0, 3.0, 5),
            "Conservateur":("Risque minimal",       "Score≥85 | RR 3.0x | DD 1.5%",85, 3.0, 1.5, 2),
            "Agressif":    ("Prop firm / max trades","Score≥70 | RR 1.5x | DD 5%", 70, 1.5, 5.0, 5),
            "Custom":      ("100% personnalisé",    "Via checklist ci-dessous",     None, None, None, None),
        }
        p_cols = st.columns(5)
        cur_profile = cfg.get("profile", "DAY_TRADE")
        for i, (pname, (desc, spec, sc, rr, dd, mx)) in enumerate(PROF_INFO.items()):
            with p_cols[i]:
                is_active = (cur_profile == pname)
                border    = "2px solid #00ff88" if is_active else "1px solid #30363d"
                st.html(
                    f"<div style='border:{border};border-radius:8px;padding:10px;"
                    f"background:#0f1117;min-height:90px;'>"
                    f"<b style='color:{'#00ff88' if is_active else '#fff'};font-size:0.85rem;'>"
                    f"{pname}</b><br>"
                    f"<small style='color:#aaa;font-size:0.75rem;'>{desc}</small><br>"
                    f"<small style='color:#4dabff;font-size:0.72rem;'>{spec}</small></div>"
                )
                if not is_active:
                    if st.button("Appliquer", key=f"prof_{pname}", use_container_width=True):
                        cfg["profile"] = pname
                        if pname in PROFIL_CONCEPTS:
                            cfg["active_concepts"] = list(PROFIL_CONCEPTS[pname])
                        if sc:    cfg["score_execute"] = sc
                        if rr:    cfg["rr_min"]         = rr
                        if dd:    cfg["drawdown_max_pct"]= dd
                        if mx:    cfg["max_positions"]   = mx
                        save_config(cfg)
                        st.rerun()
                else:
                    st.success("✅ Actif")

        st.markdown("---")
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**Profil de trading**")
            p_opts = list(PROFILE_LABELS.keys())
            p_idx  = p_opts.index(cfg.get("profile", "DAY_TRADE")) \
                     if cfg.get("profile") in p_opts else 1
            p_sel  = st.radio("Profil", p_opts, index=p_idx,
                              format_func=lambda k: PROFILE_LABELS[k],
                              key="a_profile", label_visibility="collapsed")
            cfg["profile"] = p_sel

        with col2:
            st.markdown("**Mode d'opération**")
            m_opts = list(MODE_LABELS.keys())
            m_idx  = m_opts.index(cfg.get("op_mode", "PAPER")) \
                     if cfg.get("op_mode") in m_opts else 0
            m_sel  = st.radio("Mode", m_opts, index=m_idx,
                              format_func=lambda k: MODE_LABELS[k],
                              key="a_mode", label_visibility="collapsed")
            cfg["op_mode"] = m_sel
            cfg["mode"]    = m_sel
            if m_sel == "FULL_AUTO":
                st.error(
                    "⚠️ **FULL AUTO** — Ordres RÉELS sans confirmation !\n\n"
                    "• Testez en **Paper** puis **Semi-Auto** d'abord\n"
                    "• Configurez un **drawdown max** raisonnable"
                )
                cfg["full_auto_confirmed"] = st.checkbox(
                    "✅ Je comprends et confirme le mode FULL AUTO",
                    value=cfg.get("full_auto_confirmed", False),
                    key="a_full_auto"
                )

        st.markdown("**🌐 Instruments de surveillance**")
        saved_syms = [s for s in cfg.get("symbols_watched", []) if s in SYMBOL_LIST] or ["XAUUSDm"]
        if "a_symbols" in st.session_state:
            if any(s not in SYMBOL_LIST for s in st.session_state.get("a_symbols", [])):
                del st.session_state["a_symbols"]
        syms = st.multiselect("Instruments", SYMBOL_LIST, default=saved_syms, key="a_symbols")
        cfg["symbols_watched"] = syms or ["XAUUSDm"]
        cfg["symbol"]          = cfg["symbols_watched"][0]

    # ════════════════════════════════════════════════════════
    # SECTION B — CHECKLIST PERSONNALISÉE
    # ════════════════════════════════════════════════════════
    with st.expander("🎛️ Section B — Checklist Personnalisée (Concepts actifs)", expanded=False):
        st.markdown("Cochez uniquement les concepts que vous voulez que le bot utilise. "
                    "**Le scoring ne comptera QUE les concepts cochés.**")

        # Boutons profil rapide
        b1, b2, b3, b4 = st.columns(4)
        if b1.button("🔄 Tout activer",  key="b_all", use_container_width=True):
            cfg["active_concepts"] = list(PROFIL_CONCEPTS["Tout"])
            save_config(cfg); st.rerun()
        if b2.button("⚡ ICT Pur",       key="b_ict", use_container_width=True):
            cfg["active_concepts"] = list(PROFIL_CONCEPTS["ICT Pur"])
            save_config(cfg); st.rerun()
        if b3.button("🔷 SMC+ICT",       key="b_smc", use_container_width=True):
            cfg["active_concepts"] = list(PROFIL_CONCEPTS["SMC+ICT"])
            save_config(cfg); st.rerun()
        if b4.button("📊 Price Action",  key="b_pa",  use_container_width=True):
            cfg["active_concepts"] = list(PROFIL_CONCEPTS["PA"])
            save_config(cfg); st.rerun()

        st.markdown("")
        active_concepts = list(cfg.get("active_concepts", PROFIL_CONCEPTS["ICT Pur"]))
        new_active = []

        for cat_name, concepts in CONCEPTS.items():
            n_cat    = len(concepts)
            n_active = sum(1 for k in concepts if k in active_concepts)
            with st.expander(f"{cat_name} — {n_active}/{n_cat} actifs", expanded=False):
                c1, c2 = st.columns(2)
                for j, (key, (label, desc)) in enumerate(concepts.items()):
                    col = c1 if j % 2 == 0 else c2
                    if col.checkbox(f"**{label}**", value=(key in active_concepts),
                                    key=f"b_{key}", help=desc):
                        new_active.append(key)

        if st.button("💾 Sauvegarder mon profil Custom", key="b_save",
                     type="primary", use_container_width=True):
            cfg["active_concepts"] = new_active
            cfg["profile"]         = "CUSTOM"
            save_config(cfg)
            st.success(f"✅ {len(new_active)} concepts actifs sauvegardés !")
        else:
            cfg["active_concepts"] = new_active

        total = sum(len(v) for v in CONCEPTS.values())
        pct   = int(len(new_active) / total * 100) if total else 0
        color = "#00ff88" if pct >= 60 else ("#f0b429" if pct >= 30 else "#ef5350")
        st.html(
            f"<div style='background:rgba(41,98,255,0.12);border:1px solid #2962ff44;"
            f"border-radius:8px;padding:10px;margin-top:8px;text-align:center;'>"
            f"<b style='color:{color};'>{len(new_active)} / {total} concepts actifs</b>"
            f" ({pct}%)</div>"
        )

    # ════════════════════════════════════════════════════════
    # SECTION C — Seuils & Risque
    # ════════════════════════════════════════════════════════
    with st.expander("💰 Section C — Seuils & Gestion du Risque", expanded=False):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.markdown("**🎯 Scoring**")
            sc_exec = st.slider("Score EXECUTE", 70, 100, cfg.get("score_execute", 80), key="c_exec")
            sc_lim  = st.slider("Score WATCH",   55, 95,  cfg.get("score_limit",   65), key="c_lim")
            cfg["score_execute"] = sc_exec
            cfg["score_limit"]   = sc_lim
            st.markdown(
                f"<div style='height:20px;border-radius:4px;overflow:hidden;display:flex;'>"
                f"<div style='flex:{sc_lim};background:#ef5350;'></div>"
                f"<div style='flex:{sc_exec-sc_lim};background:#f0b429;'></div>"
                f"<div style='flex:{100-sc_exec};background:#00ff88;'></div>"
                f"</div>",
                unsafe_allow_html=True
            )
            st.caption("🔴 No Trade | 🟠 Watch | 🟢 Execute")

        with col2:
            st.markdown("**📊 Capital & Risque**")
            cfg["account_balance"]       = st.number_input(
                "Capital ($)", 10, 1000000, int(cfg.get("account_balance", 463)), key="c_bal")
            cfg["risk_pct"]              = st.slider(
                "Risque / trade (%)", 0.1, 5.0, float(cfg.get("risk_pct", 0.5)), 0.1, key="c_risk")
            cfg["drawdown_max_pct"]      = st.slider(
                "DD max / jour (%)", 0.5, 10.0, float(cfg.get("drawdown_max_pct", 3.0)), 0.5, key="c_dd")
            cfg["drawdown_max_week_pct"] = st.slider(
                "DD max / semaine (%)", 1.0, 20.0, float(cfg.get("drawdown_max_week_pct", 6.0)), 0.5, key="c_ddw")

        with col3:
            st.markdown("**⚖️ Risk/Reward & Positions**")
            cfg["rr_min"]        = st.slider(
                "RR minimum", 0.5, 10.0, float(cfg.get("rr_min", 2.0)), 0.5, key="c_rr")
            cfg["rr_target"]     = st.slider(
                "RR cible", 0.5, 15.0, float(cfg.get("rr_target", 3.0)), 0.5, key="c_rrt")
            cfg["max_positions"] = st.slider(
                "Max positions", 1, 20, int(cfg.get("max_positions", 3)), key="c_pos")
            rr_c = "#10b981" if cfg["rr_min"] >= 2.0 else ("#f59e0b" if cfg["rr_min"] >= 1.5 else "#ef4444")
            st.html(
                f"<div style='background:{rr_c}22;border-left:3px solid {rr_c};"
                f"padding:8px;border-radius:4px;'>"
                f"RR min : <b style='color:{rr_c};'>{cfg['rr_min']:.1f}x</b>"
                f" | Cible : <b style='color:{rr_c};'>{cfg['rr_target']:.1f}x</b></div>"
            )

    # ════════════════════════════════════════════════════════
    # SECTION D — Gestion des Positions
    # ════════════════════════════════════════════════════════
    with st.expander("📋 Section D — Gestion des Positions", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            cfg["trailing_sl"] = st.toggle(
                "✅ Trailing Stop Loss ICT", cfg.get("trailing_sl", True), key="d_tsl")
            cfg["partial_tp"]  = st.toggle(
                "✅ TP Partiel (IRL → ERL)",  cfg.get("partial_tp", True), key="d_ptp")
            if cfg["partial_tp"]:
                cfg["partial_tp_pct"] = st.slider(
                    "% TP partiel", 10, 90, int(cfg.get("partial_tp_pct", 50)), key="d_ptpp")
        with col2:
            cfg["stop_after_losses"]  = st.toggle(
                "✅ Stop après N pertes consécutives",
                cfg.get("stop_after_losses", True), key="d_sal")
            if cfg["stop_after_losses"]:
                cfg["max_session_losses"] = st.slider(
                    "Pertes max consécutives", 1, 10,
                    int(cfg.get("max_session_losses", 2)), key="d_msl")
            cfg["max_session_trades"] = st.slider(
                "Max trades / session", 1, 20,
                int(cfg.get("max_session_trades", 3)), key="d_mst")

    # ════════════════════════════════════════════════════════
    # SECTION E — Filtres Globaux ICT
    # ════════════════════════════════════════════════════════
    with st.expander("🔒 Section E — Filtres Globaux ICT", expanded=False):
        st.caption("Ces filtres s'appliquent AVANT le scoring. Condition non remplie = trade refusé.")
        c1, c2 = st.columns(2)
        with c1:
            cfg["require_killzone"] = st.checkbox(
                "🕐 Killzone ICT obligatoire", cfg.get("require_killzone", True), key="e_kz",
                help="Refuser tous les trades en dehors d'une Killzone")
            cfg["require_erl"]      = st.checkbox(
                "💧 ERL sweepé obligatoire",   cfg.get("require_erl", True), key="e_erl",
                help="Le bot ne trade que si une prise de liquidité externe a eu lieu")
        with c2:
            cfg["require_mss"]      = st.checkbox(
                "📐 MSS confirmé obligatoire", cfg.get("require_mss", True), key="e_mss",
                help="Exiger un Market Structure Shift frais")
            cfg["require_choch"]    = st.checkbox(
                "⚡ CHoCH confirmé obligatoire", cfg.get("require_choch", False), key="e_choch",
                help="Exiger un Change of Character LTF avant d'entrer")
        c3, c4 = st.columns(2)
        with c3:
            cfg["disable_killzone_check"] = st.toggle(
                "🔓 Trading HORS Killzones (24/7)",
                cfg.get("disable_killzone_check", False), key="e_247")
        with c4:
            cfg["disable_spread_check"] = st.toggle(
                "🔓 Désactiver blocage Spread Max",
                cfg.get("disable_spread_check", False), key="e_spr")

    # ════════════════════════════════════════════════════════
    # SECTION F — KillSwitches
    # ════════════════════════════════════════════════════════
    with st.expander("🔴 Section F — KillSwitches individuels (9 règles de sécurité)", expanded=False):
        st.caption("⚠️ Désactiver un KillSwitch = prendre un risque supplémentaire.")
        disabled_ks  = set(cfg.get("disabled_ks", []))
        new_disabled = set()
        cols = st.columns(3)
        for i, (ks_id, label, desc) in enumerate(KS_LIST):
            with cols[i % 3]:
                if st.toggle(f"🚫 {ks_id} — {label}",
                             value=(ks_id in disabled_ks),
                             key=f"f_{ks_id}", help=desc):
                    new_disabled.add(ks_id)
        cfg["disabled_ks"] = list(new_disabled)
        if new_disabled:
            st.warning(f"⚠️ {len(new_disabled)} KS désactivé(s) : {', '.join(sorted(new_disabled))}")
        else:
            st.success("✅ Tous les KillSwitches actifs — protection maximale")

    # ════════════════════════════════════════════════════════
    # SECTION G — BehaviourShield
    # ════════════════════════════════════════════════════════
    with st.expander("🛡️ Section G — BehaviourShield (8 filtres anti-manipulation)", expanded=False):
        st.caption("Filtres appliqués avant chaque ordre pour protéger contre les comportements à risque.")
        bs   = cfg.get("behaviour_shield", DEFAULT_CONFIG["behaviour_shield"])
        cols = st.columns(2)
        for i, (key, label, desc) in enumerate(BS_LIST):
            with cols[i % 2]:
                bs[key] = st.toggle(f"✅ {label}", value=bs.get(key, True),
                                    key=f"g_{key}", help=desc)
        cfg["behaviour_shield"] = bs

        st.markdown("**⏰ Filtres temporels**")
        tf = cfg.get("time_filters", DEFAULT_CONFIG["time_filters"])
        t1, t2, t3 = st.columns(3)
        tf["friday_pm"]      = t1.checkbox("🚫 Vendredi PM (>14h NY)",
                                           tf.get("friday_pm", True), key="g_fri")
        tf["monday_morning"] = t2.checkbox("🚫 Lundi matin (<10h NY)",
                                           tf.get("monday_morning", True), key="g_mon")
        tf["before_news"]    = t3.checkbox("🚫 Avant NFP/FOMC (2h avant)",
                                           tf.get("before_news", True), key="g_nws")
        cfg["time_filters"] = tf

    # ════════════════════════════════════════════════════════
    # SECTION H — Sessions & Timing
    # ════════════════════════════════════════════════════════
    with st.expander("📅 Section H — Sessions & Timing", expanded=False):
        st.caption("Sessions dans lesquelles le bot est autorisé à trader.")
        SESS = [
            ("session_london", "🇬🇧 Session Londres",   "07h–16h UTC"),
            ("session_ny",     "🇺🇸 Session New York",  "13h–22h UTC"),
            ("session_asia",   "🇯🇵 Session Asie",      "00h–09h UTC"),
            ("overlap_lnny",   "🔥 Overlap Londres+NY", "13h–16h UTC — RECOMMANDÉ"),
            ("sb_london",      "⭐ Silver Bullet London","03h–04h NY"),
            ("sb_am",          "⭐ Silver Bullet AM",    "10h–11h NY"),
            ("sb_pm",          "⭐ Silver Bullet PM",    "14h–15h NY"),
        ]
        sessions = set(cfg.get("sessions_actives", ["session_london","session_ny","overlap_lnny"]))
        new_sess  = set()
        cols = st.columns(2)
        for i, (key, label, desc) in enumerate(SESS):
            with cols[i % 2]:
                if st.checkbox(f"{label} — {desc}", value=(key in sessions), key=f"h_{key}"):
                    new_sess.add(key)
        cfg["sessions_actives"] = list(new_sess)
        if not new_sess:
            st.warning("⚠️ Aucune session — le bot ne pourra pas trader.")

    # ════════════════════════════════════════════════════════
    # SECTION I — Macro & Institutionnel
    # ════════════════════════════════════════════════════════
    with st.expander("🌍 Section I — Macro & Institutionnel", expanded=False):
        c1, c2 = st.columns(2)
        with c1:
            cfg["cot_enabled"] = st.toggle("📊 COT & Saisonnalité",
                                  cfg.get("cot_enabled", True), key="i_cot",
                                  help="Biais institutionnel mensuel (Large Speculators)")
        with c2:
            cfg["perplexity_enabled"] = st.toggle("🔍 Perplexity Pro (Macro temps réel)",
                                         cfg.get("perplexity_enabled", False), key="i_perp",
                                         help="Enrichit le narratif avec FOMC/CPI/NFP en temps réel")
        if cfg["perplexity_enabled"]:
            cfg["perplexity_api_key"] = st.text_input(
                "🔑 Clé API Perplexity",
                value=cfg.get("perplexity_api_key", ""),
                type="password", key="i_pkey",
                help="https://www.perplexity.ai/settings/api"
            )

    # ════════════════════════════════════════════════════════
    # SECTION J — IA Narratif War Room
    # ════════════════════════════════════════════════════════
    with st.expander("🧠 Section J — IA (Narratif War Room)", expanded=False):
        PROVIDERS = ["Gemini", "Groq", "Grok (x.ai)", "OpenAI"]
        c1, c2 = st.columns(2)
        with c1:
            cur = cfg.get("llm_provider", "Gemini")
            cfg["llm_provider"] = st.selectbox(
                "🗣️ Fournisseur IA", PROVIDERS,
                index=PROVIDERS.index(cur) if cur in PROVIDERS else 0,
                key="j_prov")
        with c2:
            cfg["llm_api_key"] = st.text_input(
                "🔑 Clé API", value=cfg.get("llm_api_key", ""),
                type="password", key="j_key")
        st.caption("💡 Vos clés Gemini et Groq sont déjà dans votre fichier .env.")

    # ════════════════════════════════════════════════════════
    # SECTION K — Telegram
    # ════════════════════════════════════════════════════════
    with st.expander("📱 Section K — Notifications Telegram", expanded=False):
        c1, c2, c3 = st.columns(3)
        with c1:
            cfg["telegram_enabled"] = st.toggle(
                "✅ Activer Telegram", cfg.get("telegram_enabled", True), key="k_on")
        with c2:
            cfg["telegram_token"] = st.text_input(
                "Token Bot", cfg.get("telegram_token", ""),
                type="password", key="k_tok")
        with c3:
            cfg["telegram_chat_id"] = st.text_input(
                "Chat ID", cfg.get("telegram_chat_id", ""), key="k_cid")
        if st.button("🧪 Tester la connexion Telegram", key="k_test"):
            ok, msg = test_telegram(cfg["telegram_token"], cfg["telegram_chat_id"])
            (st.success if ok else st.error)(f"{'✅' if ok else '❌'} {msg}")

    # ════════════════════════════════════════════════════════
    # SECTION L — Récapitulatif + Lancement
    # ════════════════════════════════════════════════════════
    st.markdown("---")
    st.markdown("### 📄 Récapitulatif de la Configuration")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(f"**Profil :** `{cfg['profile']}`")
        st.markdown(f"**Mode :** `{cfg['op_mode']}`")
        st.markdown(f"**Symboles :** {len(cfg['symbols_watched'])}")
    with col2:
        st.markdown(f"**Score EXECUTE :** `≥ {cfg['score_execute']}`")
        st.markdown(f"**Score WATCH :** `≥ {cfg['score_limit']}`")
        st.markdown(f"**Risque/trade :** `{cfg['risk_pct']} %`")
    with col3:
        st.markdown(f"**SL Trailing :** {'✅' if cfg['trailing_sl'] else '❌'}")
        st.markdown(f"**TP Partiel :** {'✅' if cfg['partial_tp'] else '❌'}")
        st.markdown(f"**Concepts actifs :** `{len(cfg.get('active_concepts', []))}`")

    save_config(cfg)
    st.success("✅ Configuration sauvegardée automatiquement")

    st.markdown("---")
    st.markdown("### 🚀 Lancement du Bot")

    running = is_bot_running()
    status_c = "#10b981" if running else "#ef4444"
    status_t = "🟢 ACTIF" if running else "🔴 ARRÊTÉ"
    st.html(
        f"<div style='text-align:center;padding:16px;border-radius:8px;"
        f"background:{status_c}22;border:2px solid {status_c};margin-bottom:12px;'>"
        f"<h3 style='color:{status_c};margin:0;'>BOT {status_t}</h3>"
        f"<small style='color:#848e9c;'>{datetime.now().strftime('%H:%M:%S')}</small></div>"
    )

    col_s, col_t, col_st = st.columns(3)
    with col_s:
        if st.button("▶️ DÉMARRER LE BOT", type="primary",
                     use_container_width=True, disabled=running):
            if cfg["op_mode"] == "FULL_AUTO" and not cfg.get("full_auto_confirmed"):
                st.error("⚠️ Confirmez d'abord le mode FULL AUTO dans la Section A.")
            else:
                if start_bot_process():
                    st.success("🟢 Bot démarré !")
                else:
                    st.error("❌ Erreur démarrage.")
                st.rerun()
    with col_t:
        if st.button("⏹️ ARRÊTER LE BOT", type="secondary",
                     use_container_width=True, disabled=not running):
            stop_bot_process()
            st.success("⚫ Bot arrêté.")
            st.rerun()
    with col_st:
        if running:
            st.success("🟢 BOT EN LIGNE")
        else:
            st.info("⚫ Bot arrêté")
