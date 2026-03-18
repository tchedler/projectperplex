"""
bot_settings.py — Interface de Configuration du Bot de Trading ICT
Page Streamlit pour configurer tous les paramètres du bot avant son lancement.
Toutes les configurations sont persistées dans data/bot_config.json.
"""
import json
import os
import sys
import subprocess
import streamlit as st

# Utiliser un chemin absolu pour le PID_FILE afin d'éviter les soucis de CWD
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PID_FILE = os.path.join(BASE_DIR, "data", "bot.pid")

def get_bot_pid():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                content = f.read().strip()
                return int(content) if content else None
        except Exception:
            pass
    return None

def is_bot_running():
    pid = get_bot_pid()
    if not pid:
        return False
    try:
        if os.name == "nt":
            # Use errors='ignore' or a specific encoding like 'cp1252' for French Windows
            output = subprocess.check_output(f'tasklist /FI "PID eq {pid}" /NH', shell=True).decode('utf-8', errors='ignore')
            return str(pid) in output
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False

def start_bot_process():
    if is_bot_running():
        return False
    creation_flags = 0
    if os.name == "nt":
        creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
    
    # Ensure root_dir is correct
    root_dir = BASE_DIR
    bot_runner_path = os.path.join(root_dir, "bot_runner.py")
    
    process = subprocess.Popen(
        [sys.executable, bot_runner_path],
        creationflags=creation_flags,
        cwd=root_dir,
        stdout=None, # Laisse le stream se faire vers le fichier log du bot
        stderr=None
    )
    
    os.makedirs(os.path.dirname(PID_FILE), exist_ok=True)
    with open(PID_FILE, "w") as f:
        f.write(str(process.pid))
    return True

def stop_bot_process():
    pid = get_bot_pid()
    if pid:
        try:
            if os.name == "nt":
                # Utilise taskkill /F /T pour être sûr de tuer les fils (threads/sous-processus)
                subprocess.run(f"taskkill /PID {pid} /F /T", shell=True, check=False)
            else:
                import signal
                os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
        finally:
            if os.path.exists(PID_FILE):
                os.remove(PID_FILE)
    return True


CONFIG_PATH = os.path.join(BASE_DIR, "data", "bot_config.json")

# ============================================================
# CONFIGURATION PAR DÉFAUT
# ============================================================
DEFAULT_CONFIG = {
    "profile":          "DAY_TRADE",
    "mode":             "PAPER",
    "symbol":           "XAUUSD",
    "symbols_watched":  ["XAUUSD"],
    "score_execute":    80,
    "score_limit":      65,
    "risk_pct":         1.0,
    "drawdown_max_pct": 5.0,
    "max_positions":    3,
    "trailing_sl":      True,
    "partial_tp":       True,
    "partial_tp_pct":   50,
    "stop_after_losses": True,
    "max_session_losses": 2,
    "max_session_trades": 3,
    "account_balance":  10000,
    "bot_active":       False,
    "disable_spread_check": False,
    "disable_killzone_check": False,
}

PROFILE_LABELS = {
    "SCALP":      "⚡ Scalp (M1–M5, Silver Bullet windows)",
    "DAY_TRADE":  "📊 Day Trade (M5–D1, London + NY) ← Recommandé",
    "SWING":      "🌊 Swing Trading (H2–W1, plusieurs jours)",
    "LONG_TERM":  "🏔️ Long Terme (D1–MN, positions mensuelles)",
}

MODE_LABELS = {
    "PAPER":      "📝 Paper Trading (simulation — aucun ordre réel)",
    "SEMI_AUTO":  "🔔 Semi-Automatique (alerte → vous validez)",
    "FULL_AUTO":  "🤖 Full Automatique (bot trade seul 24/7)",
}

# Symboles Exness MT5 Standard — vérifiés via interrogation MT5 (08/03/2026)
SYMBOL_LIST = [
    # Forex Majeurs
    "EURUSDm", "GBPUSDm", "USDJPYm", "USDCHFm", "USDCADm", "AUDUSDm", "NZDUSDm",
    # Forex Croix
    "GBPJPYm", "EURJPYm", "EURGBPm", "AUDJPYm", "CHFJPYm",
    # Indices US (ICT)
    "USTECm",   # Nasdaq 100 (US100) — NAS100m n'existe PAS chez Exness
    "US500m",   # S&P 500
    "US30m",    # Dow Jones
    # Indices Mondiaux
    "DE30m", "UK100m", "JP225m", "STOXX50m", "AUS200m", "FR40m",
    # Métaux
    "XAUUSDm", "XAGUSDm",
    # Énergie
    "USOILm", "UKOILm",
    # Crypto
    "BTCUSDm", "ETHUSDm",
    # Indice Dollar
    "DXYm",
]


# ============================================================
# CHARGEMENT / SAUVEGARDE CONFIG
# ============================================================
def load_config() -> dict:
    os.makedirs("data", exist_ok=True)
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r") as f:
                stored = json.load(f)
            # Merge avec les valeurs par défaut (nouveaux paramètres)
            return {**DEFAULT_CONFIG, **stored}
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(config: dict):
    os.makedirs("data", exist_ok=True)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


# ============================================================
# PAGE PRINCIPALE
# ============================================================
def render_bot_settings():
    """Affiche la page de configuration complète du bot."""

    st.html("""
        <h2 style='color:#2962ff; font-family: Outfit, sans-serif;'>
            ⚙️ Paramètres du Bot de Trading ICT
        </h2>
        <p style='color:#848e9c;'>
            Configurez votre agent de trading avant de le lancer.
            Toutes les modifications sont sauvegardées automatiquement.
        </p>
    """)

    # Récupération silencieuse du solde MT5 pour le champ Capital
    real_balance = None
    try:
        import MetaTrader5 as mt5
        if mt5.initialize():
            acc_info = mt5.account_info()
            if acc_info:
                real_balance = float(acc_info.balance)
    except Exception:
        pass

    config = load_config()

    # ============================================================
    # SECTION A — PROFIL & MODE
    # ============================================================
    st.markdown("---")
    st.markdown("### 🎯 Section A — Profil & Mode de Trading")

    col1, col2 = st.columns(2)
    with col1:
        profile_options = list(PROFILE_LABELS.keys())
        profile_labels  = list(PROFILE_LABELS.values())
        cur_idx = profile_options.index(config["profile"]) if config["profile"] in profile_options else 1

        profile_sel = st.radio(
            "Profil de trading",
            options=profile_options,
            index=cur_idx,
            format_func=lambda k: PROFILE_LABELS[k],
            key="bot_profile"
        )
        config["profile"] = profile_sel

    with col2:
        mode_options = list(MODE_LABELS.keys())
        cur_mode_idx = mode_options.index(config["mode"]) if config["mode"] in mode_options else 0

        mode_sel = st.radio(
            "Mode d'opération",
            options=mode_options,
            index=cur_mode_idx,
            format_func=lambda k: MODE_LABELS[k],
            key="bot_mode"
        )
        config["mode"] = mode_sel

        if mode_sel == "FULL_AUTO":
            st.html(
                "<div style='border:1px solid #ef5350; border-radius:8px; padding:12px; background:#2a1515;'>"
                "<b style='color:#ef5350;'>⛔ ATTENTION — MODE FULL AUTO</b><br>"
                "Le bot va placer des ordres <b>RÉELS</b> sur votre compte MT5 "
                "sans aucune confirmation humaine.<br>"
                "Assurez-vous d'avoir :<br>"
                "• Testé en mode <b>Paper</b> puis <b>Semi-Auto</b> d'abord<br>"
                "• Configuré un <b>drawdown max</b> raisonnable (§ B ci-dessous)<br>"
                "• Réglé un <b>stop-loss</b> sur votre compte au niveau du broker"
                "</div>"
            )
            config["full_auto_confirmed"] = st.checkbox(
                "✅ Je comprends les risques et confirme le mode FULL AUTO",
                value=config.get("full_auto_confirmed", False),
                key="full_auto_confirm"
            )


    # Symboles
    st.markdown("#### 🌐 Instruments surveillés")
    
    # FIX : s'assurer que les symboles sauvegardés existent dans la nouvelle liste Exness
    saved_symbols = config.get("symbols_watched", ["XAUUSDm"])
    valid_default_symbols = [s for s in saved_symbols if s in SYMBOL_LIST]
    if not valid_default_symbols:
        valid_default_symbols = [SYMBOL_LIST[0]]  # Premier symbole disponible (EURUSDm)

    # FIX CRITIQUE: Streamlit conserve l'ancien état dans session_state qui provoque un crash si l'option n'existe plus
    if "bot_symbols" in st.session_state:
        state_symbols = st.session_state["bot_symbols"]
        if any(s not in SYMBOL_LIST for s in state_symbols):
            del st.session_state["bot_symbols"]  # Forcer la réinitialisation sur default

    symbols_sel = st.multiselect(
        "Sélectionnez le ou les instruments à trader",
        options=SYMBOL_LIST,
        default=valid_default_symbols,
        key="bot_symbols"
    )
    config["symbols_watched"] = symbols_sel if symbols_sel else ["XAUUSDm"]
    config["symbol"] = config["symbols_watched"][0]

    # ============================================================
    # SECTION B — SEUILS & GESTION DU RISQUE
    # ============================================================
    st.markdown("---")
    st.markdown("### 💰 Section B — Seuils & Gestion du Risque")

    col3, col4, col5 = st.columns(3)
    with col3:
        score_exec = st.slider(
            "Score min EXECUTE (ordre au marché)",
            min_value=70, max_value=100, value=config["score_execute"], step=1,
            key="score_execute",
            help="Score ICT minimum pour placer un ordre immédiat"
        )
        config["score_execute"] = score_exec

        score_lim = st.slider(
            "Score min LIMIT ORDER (ordre en attente)",
            min_value=50, max_value=score_exec - 1, value=min(config["score_limit"], score_exec - 1), step=1,
            key="score_limit",
            help="Score ICT minimum pour placer un ordre limite à l'OTE 70.5%"
        )
        config["score_limit"] = score_lim

    with col4:
        risk_pct = st.slider(
            "% Risque par trade",
            min_value=0.1, max_value=5.0, value=config["risk_pct"], step=0.1,
            format="%0.1f%%",
            key="risk_pct",
            help="Pourcentage du capital risqué sur chaque trade"
        )
        config["risk_pct"] = risk_pct

        dd_max = st.slider(
            "Drawdown max par session (%)",
            min_value=1.0, max_value=20.0, value=config["drawdown_max_pct"], step=0.5,
            format="%0.1f%%",
            key="drawdown_max",
            help="Le bot s'arrête si ce drawdown est atteint dans la session"
        )
        config["drawdown_max_pct"] = dd_max

    with col5:
        # M15 FIX : Capital dynamique depuis MT5
        default_bal = config.get("account_balance", 10000)
        
        if real_balance and real_balance > 0:
            help_text = f"Solde MT5 actuel : {real_balance:.2f} $. Vous pouvez le diminuer pour limiter l'exposition du bot."
            # Mettre à jour par défaut au solde réel, sauf si l'utilisateur a délibérément réduit le risque en dessous
            if default_bal == 10000 or default_bal > real_balance:
                default_bal = int(real_balance)
        else:
            help_text = "Utilisé pour calculer la taille de position (connectez MT5 pour voir le solde réel)"

        balance = st.number_input(
            "Capital du compte ($)",
            min_value=10, max_value=10000000, value=int(default_bal), step=100,
            key="account_balance",
            help=help_text
        )
        config["account_balance"] = balance

        max_pos = st.slider(
            "Max positions simultanées",
            min_value=1, max_value=10, value=config["max_positions"], step=1,
            key="max_positions"
        )
        config["max_positions"] = max_pos

    # ============================================================
    # SECTION C — GESTION DES POSITIONS
    # ============================================================
    st.markdown("---")
    st.markdown("### 📈 Section C — Gestion des Positions")

    col6, col7 = st.columns(2)
    with col6:
        trailing_sl = st.toggle(
            "✅ Trailing Stop Loss ICT actif",
            value=config["trailing_sl"],
            key="trailing_sl",
            help="Suit les swings ICT (SWL/SWH M15) pour déplacer le SL"
        )
        config["trailing_sl"] = trailing_sl

        partial_tp = st.toggle(
            "✅ Partial Take Profit actif",
            value=config["partial_tp"],
            key="partial_tp",
            help="Ferme 50% de la position à TP1, puis déplace SL au breakeven"
        )
        config["partial_tp"] = partial_tp

        if partial_tp:
            partial_pct = st.slider(
                "% Partial TP (du Dealing Range)",
                min_value=25, max_value=75, value=config["partial_tp_pct"], step=5,
                key="partial_pct"
            )
            config["partial_tp_pct"] = partial_pct

    with col7:
        stop_losses = st.toggle(
            "✅ Stop après N pertes consécutives",
            value=config["stop_after_losses"],
            key="stop_losses",
            help="Bible ICT : s'arrêter après 2 pertes consécutives"
        )
        config["stop_after_losses"] = stop_losses

        if stop_losses:
            max_losses = st.slider(
                "Nombre de pertes consécutives max",
                min_value=1, max_value=5, value=config["max_session_losses"], step=1,
                key="max_losses"
            )
            config["max_session_losses"] = max_losses

        max_trades_sess = st.slider(
            "Max trades par session",
            min_value=1, max_value=10, value=config["max_session_trades"], step=1,
            key="max_trades_session",
            help="Bible ICT : maximum 3 trades par session"
        )
        config["max_session_trades"] = max_trades_sess

    st.markdown("---")
    st.markdown("### 🔓 Section Spéciale — Actifs 24/7 (Cryptos & Indices Volatils)")
    st.info("Ces options permettent de contourner les règles strictes d'ICT (prévues pour le Forex) afin d'autoriser le bot à trader le Bitcoin ou l'Ethereum n'importe quand et avec un spread plus large.")
    col8, col9 = st.columns(2)
    with col8:
        disable_killzones = st.toggle(
            "🔓 Autoriser le trading HORS Killzones (24/7)",
            value=config.get("disable_killzone_check", False),
            key="disable_killzone",
            help="Ignore les sessions de Londres/NY. Le bot tradera dès qu'un setup est valide, même la nuit ou le week-end (Idéal pour Cryptos)."
        )
        config["disable_killzone_check"] = disable_killzones
        
    with col9:
        disable_spread = st.toggle(
            "🔓 Désactiver le blocage de Spread Max",
            value=config.get("disable_spread_check", False),
            key="disable_spread",
            help="Ne bloque plus les trades si le spread excède 50 pips. Utile pour les cryptos ou les moments de forte volatilité."
        )
        config["disable_spread_check"] = disable_spread

    # ============================================================
    # RÉCAPITULATIF
    # ============================================================
    st.markdown("---")
    st.markdown("### 📋 Récapitulatif de la Configuration")

    col_r1, col_r2, col_r3 = st.columns(3)
    with col_r1:
        st.info(f"**Profil :** {config['profile']}\n\n**Mode :** {config['mode']}\n\n**Symboles :** {', '.join(config['symbols_watched'])}")
    with col_r2:
        st.info(f"**Score EXECUTE :** ≥ {config['score_execute']}\n\n**Score LIMIT :** ≥ {config['score_limit']}\n\n**Risque/trade :** {config['risk_pct']}%")
    with col_r3:
        st.info(f"**Trailing SL :** {'Oui' if config['trailing_sl'] else 'Non'}\n\n**Partial TP :** {'Oui' if config['partial_tp'] else 'Non'}\n\n**Max trades :** {config['max_session_trades']}/session")

    # Sauvegarde automatique
    save_config(config)
    st.success("✅ Configuration sauvegardée automatiquement")

# ============================================================
    # SECTION D — CONTRÔLES (REMPLACEMENT FIX)
    # ============================================================
    st.markdown("---")
    st.markdown("### 🎮 Section D — Lancement du Bot")

    col_btn1, col_btn2, col_btn3 = st.columns([2, 2, 3])

    bot_active = is_bot_running()
    st.session_state["bot_is_running"] = bot_active

    with col_btn1:
        if st.button("🟢 DÉMARRER LE BOT", use_container_width=True, disabled=bot_active, key="btn_start_final"):
            if start_bot_process():
                st.session_state["bot_is_running"] = True
                st.toast("🚀 Bot démarré avec succès !")
                import time
                time.sleep(1)
                st.rerun()

    with col_btn2:
        if st.button("🔴 ARRÊTER LE BOT", type="primary", use_container_width=True, disabled=not bot_active, key="btn_stop_final"):
            stop_bot_process()
            st.session_state["bot_is_running"] = False
            st.toast("⏹️ Bot arrêté.")
            import time
            time.sleep(1)
            st.rerun()

    with col_btn3:
        if bot_active:
            st.success("🟢 BOT EN LIGNE")
        else:
            st.warning("⚫ BOT HORS LIGNE")
    return config