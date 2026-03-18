"""
constants.py — M6 FIX : Source unique de vérité pour les constantes de trading.
Référencé par trading_judge.py et order_manager.py pour éviter les duplications.
"""

# =============================================================================
# PIP SIZES PAR INSTRUMENT
# =============================================================================
# Un "pip" est l'unité minimale de fluctuation du prix affecté à chaque symbole.
# Note broker-dépendant : certains brokers utilisent 5 décimales pour les paires Forex
# (ex: EURUSD à 1.10000 → 1 pip = 0.0001, pas 0.00001).

PIP_SIZE: dict[str, float] = {
    # Paires Forex majeures
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "AUDUSD": 0.0001,
    "NZDUSD": 0.0001,
    "USDCAD": 0.0001,
    "USDCHF": 0.0001,
    # Paires JPY
    "USDJPY": 0.01,
    "GBPJPY": 0.01,
    "EURJPY": 0.01,
    "AUDJPY": 0.01,
    # Or / Métaux
    # I7 FIX : Pour XAUUSD, 1 pip = 0.01$ (spécs standard, peut varier par broker)
    # Vérifiez symbol_info().trade_tick_size sur MT5 pour votre broker.
    "XAUUSD": 0.01,
    "XAGUSD": 0.001,
    # Indices
    "NAS100": 0.25,
    "US30":   1.0,
    "US500":  0.25,
    # Crypto
    "BTCUSD": 1.0,
    "ETHUSD": 0.1,
}

# =============================================================================
# VALEUR D'UN PIP PAR LOT (en USD)
# =============================================================================
# Formula standard : pip_value = (pip_size / current_price) × contract_size
# Pour XAUUSD : 1 lot = 100 oz. Pip = 0.01$ → valeur = 100 × 0.01 = 1$/pip/lot
# MAIS cela dépend des spécs réelles de votre broker → toujours préférer mt5.symbol_info()

PIP_VALUE_PER_LOT: dict[str, float] = {
    "EURUSD": 10.0,
    "GBPUSD": 10.0,
    "AUDUSD": 10.0,
    "NZDUSD": 10.0,
    "USDCAD": 7.69,   # ~10 / taux USDCAD
    "USDCHF": 10.0,
    "USDJPY": 6.90,   # ~100 / taux USDJPY
    "GBPJPY": 6.90,
    "EURJPY": 6.90,
    "AUDJPY": 6.90,
    # I7 FIX : 100 oz × 0.01$/pip = 1$/pip/lot en théorie standard broker
    # Certains brokers calculent différemment → vérifiez avec symbol_info_tick()
    "XAUUSD": 1.0,
    "XAGUSD": 5.0,
    "NAS100": 1.0,
    "US30":   1.0,
    "US500":  1.0,
    "BTCUSD": 1.0,
    "ETHUSD": 0.1,
}

# =============================================================================
# MAGIC NUMBER
# =============================================================================
# Identifiant unique du bot pour filtrer les positions sur MT5
BOT_MAGIC_NUMBER: int = 20260001

# =============================================================================
# TIMEFRAMES ICT — Ordre logique
# =============================================================================
TF_ORDER_HTF = ["MN", "W1", "D1"]    # Timeframes hauts (biais global)
TF_ORDER_MTF = ["H4", "H1"]          # Timeframes moyens (structure locale)
TF_ORDER_LTF = ["M15", "M5", "M1"]   # Timeframes bas (déclencheur + entrée)
TF_ORDER_ALL = TF_ORDER_HTF + TF_ORDER_MTF + TF_ORDER_LTF
