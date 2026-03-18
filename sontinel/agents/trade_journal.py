"""
TradeJournal — Journal des trades ICT avec SQLite
Enregistre chaque trade, ses résultats, et catégorise les erreurs
pour permettre l'apprentissage à partir des cas d'échec.
"""
import sqlite3
import json
import datetime
import os
import pytz
from dataclasses import asdict
from typing import List, Optional


# ============================================================
# CATÉGORIES D'ERREURS (Bible ICT - Discipline)
# ============================================================
ERROR_CATEGORIES = {
    "EARLY_ENTRY":      "Entré avant la confirmation du sweep ERL",
    "WRONG_BIAS":       "Trade pris contre le biais HTF",
    "BAD_TIMING":       "Trade hors Killzone ou Macro",
    "OVERTRADING":      "Dépassement du max de trades/session",
    "SL_TOO_TIGHT":     "Stop Loss trop serré (< ATR)",
    "INDUCEMENT":       "MSS sans sweep ERL précédent = inducement",
    "REVENGE_TRADE":    "Trade pris après une perte pour 'récupérer'",
    "NO_DISPLACEMENT":  "Entrée sans displacement confirmé",
    "WRONG_ZONE":       "Achat en premium ou vente en discount",
    "FRIDAY_TRADE":     "Trade pris vendredi après 14h NY",
    "NONE":             "Aucune erreur identifiée",
}


class TradeJournal:
    """
    Journal de trading complet :
    - SQLite pour la persistance des trades
    - Catégorisation automatique des erreurs
    - Rapports post-session
    - Export JSON pour analyse
    """

    DB_VERSION = "1.0"

    def __init__(self, db_path: str = "data/trades.db"):
        self.db_path = db_path
        self.tz      = pytz.timezone("America/New_York")

        # Créer le dossier data/ si nécessaire
        os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)

        self._init_db()

    # ============================================================
    # INITIALISATION DE LA BASE DE DONNÉES
    # ============================================================
    def _init_db(self):
        """Crée les tables si elles n'existent pas."""
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    ticket          INTEGER,
                    symbol          TEXT,
                    direction       TEXT,
                    entry           REAL,
                    sl              REAL,
                    sl_final        REAL,
                    tp1             REAL,
                    tp2             REAL,
                    lot_size        REAL,
                    score           REAL,
                    confidence      TEXT,
                    setup_name      TEXT,
                    htf_bias        TEXT,
                    structure_mode  TEXT,
                    po3_phase       TEXT,
                    killzone        TEXT,
                    macro           TEXT,
                    timeframe       TEXT,
                    open_time       TEXT,
                    close_time      TEXT,
                    close_price     REAL,
                    close_reason    TEXT,
                    pnl_pips        REAL,
                    pnl_money       REAL,
                    status          TEXT,
                    partial_done    INTEGER,
                    paper_mode      INTEGER,
                    error_category  TEXT,
                    lesson_learned  TEXT,
                    notes           TEXT,
                    context_json    TEXT,
                    created_at      TEXT
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS failure_cases (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    trade_id        INTEGER,
                    error_type      TEXT,
                    error_desc      TEXT,
                    context_json    TEXT,
                    lesson_learned  TEXT,
                    date            TEXT,
                    FOREIGN KEY(trade_id) REFERENCES trades(id)
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_reports (
                    id          INTEGER PRIMARY KEY AUTOINCREMENT,
                    date        TEXT UNIQUE,
                    total_trades INTEGER,
                    win_count   INTEGER,
                    loss_count  INTEGER,
                    be_count    INTEGER,
                    win_rate    REAL,
                    avg_r       REAL,
                    total_pnl   REAL,
                    max_drawdown REAL,
                    top_errors  TEXT,
                    report_json TEXT,
                    created_at  TEXT
                )
            """)

            conn.commit()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    # ============================================================
    # ENREGISTREMENT D'UN TRADE (OUVERTURE)
    # ============================================================
    def log_trade_open(self, pos) -> int:
        """
        Enregistre l'ouverture d'un trade.
        Retourne l'ID de la ligne créée.
        """
        signal = pos.signal
        now    = datetime.datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S")

        context = {
            "entry": signal.entry,
            "sl":    signal.sl,
            "tp1":   signal.tp1,
            "tp2":   signal.tp2,
            "setup": signal.setup_name,
            "score": signal.score,
            "reason": signal.reason,
        }

        with self._connect() as conn:
            cursor = conn.execute("""
                INSERT INTO trades (
                    ticket, symbol, direction, entry, sl, tp1, tp2,
                    lot_size, score, confidence, setup_name,
                    htf_bias, po3_phase, killzone, macro, timeframe,
                    open_time, status, partial_done, paper_mode,
                    error_category, context_json, created_at
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                pos.ticket, signal.symbol, signal.direction,
                signal.entry, signal.sl, signal.tp1, signal.tp2,
                signal.lot_size, signal.score, signal.confidence,
                signal.setup_name, signal.htf_bias, signal.po3_phase,
                signal.killzone, signal.macro, signal.timeframe,
                pos.open_time.strftime("%Y-%m-%d %H:%M:%S"),
                "OPEN", int(pos.partial_done), int(pos.paper),
                "NONE", json.dumps(context), now
            ))
            conn.commit()
            return cursor.lastrowid

    # ============================================================
    # ENREGISTREMENT DE FERMETURE
    # ============================================================
    def log_trade_close(self, pos) -> None:
        """Met à jour le trade avec les données de fermeture."""
        close_time = pos.close_time.strftime("%Y-%m-%d %H:%M:%S") if pos.close_time else ""
        status = self._determine_status(pos)
        error  = self._auto_categorize_error(pos)

        with self._connect() as conn:
            conn.execute("""
                UPDATE trades SET
                    sl_final      = ?,
                    close_time    = ?,
                    close_price   = ?,
                    close_reason  = ?,
                    pnl_pips      = ?,
                    pnl_money     = ?,
                    status        = ?,
                    partial_done  = ?,
                    error_category = ?
                WHERE ticket = ?
            """, (
                pos.current_sl, close_time, pos.close_price,
                pos.close_reason, pos.pnl_pips, pos.pnl_money,
                status, int(pos.partial_done), error, pos.ticket
            ))
            conn.commit()

        # Si c'est une perte, créer un cas d'échec
        if status == "LOSS" and error != "NONE":
            self._log_failure_case(pos, error, status)

    def log_partial_tp(self, pos, price: float) -> None:
        """Enregistre la prise de profit partielle."""
        with self._connect() as conn:
            conn.execute("""
                UPDATE trades SET partial_done = 1 WHERE ticket = ?
            """, (pos.ticket,))
            conn.commit()

    # ============================================================
    # CATÉGORISATION AUTOMATIQUE DES ERREURS
    # ============================================================
    def _determine_status(self, pos) -> str:
        if pos.close_reason == "TP2":
            return "WIN"
        elif pos.close_reason == "TP1":
            return "WIN"
        elif pos.close_reason == "SL":
            if pos.partial_done:
                return "BREAKEVEN"   # TP1 pris + SL sur breakeven
            return "LOSS"
        elif pos.close_reason == "MANUAL":
            return "MANUAL"
        return "UNKNOWN"

    def _auto_categorize_error(self, pos) -> str:
        """
        Tente d'identifier automatiquement la catégorie d'erreur pour les pertes.
        """
        signal = pos.signal
        if pos.close_reason != "SL" or pos.partial_done:
            return "NONE"

        # Vérifications sur les conditions d'entrée
        if signal.killzone == "NONE" and signal.macro == "NONE":
            return "BAD_TIMING"
        if "BEAR" in signal.htf_bias and signal.direction == "BUY":
            return "WRONG_BIAS"
        if "BULL" in signal.htf_bias and signal.direction == "SELL":
            return "WRONG_BIAS"
        if signal.score < 65:
            return "EARLY_ENTRY"
        if signal.po3_phase and "ACCUMULATION" in signal.po3_phase:
            return "EARLY_ENTRY"

        return "NONE"

    def _log_failure_case(self, pos, error: str, status: str) -> None:
        """Crée un cas d'échec détaillé dans la table failure_cases."""
        desc = ERROR_CATEGORIES.get(error, "")
        context = pos.signal.to_dict()
        now = datetime.datetime.now(self.tz).strftime("%Y-%m-%d %H:%M:%S")

        # Leçon automatique
        lessons = {
            "EARLY_ENTRY":     "Attendre confirmation Sweep ERL + MSS avant entrée.",
            "WRONG_BIAS":      "Toujours trader dans le sens du biais HTF dominante.",
            "BAD_TIMING":      "Entrer UNIQUEMENT en Killzone ou pendant une Macro.",
            "INDUCEMENT":      "Vérifier Boolean_Sweep_ERL avant tout trade.",
            "WRONG_ZONE":      "Acheter en Discount, vendre en Premium. Toujours.",
        }
        lesson = lessons.get(error, "Revoir les conditions d'entrée ICT.")

        # Trouver l'id du trade
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id FROM trades WHERE ticket = ?", (pos.ticket,)
            ).fetchone()
            trade_id = row[0] if row else None

            conn.execute("""
                INSERT INTO failure_cases
                (trade_id, error_type, error_desc, context_json, lesson_learned, date)
                VALUES (?,?,?,?,?,?)
            """, (trade_id, error, desc, json.dumps(context), lesson, now))
            conn.commit()

    # ============================================================
    # REQUÊTES ET RAPPORTS
    # ============================================================
    def get_all_trades(self, limit: int = 200) -> List[dict]:
        """Retourne les N derniers trades."""
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trades ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            cols = [d[0] for d in conn.execute("SELECT * FROM trades LIMIT 0").description]
            return [dict(zip(cols, row)) for row in rows]

    def get_active_trades(self) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM trades WHERE status = 'OPEN' ORDER BY id DESC"
            ).fetchall()
            if not rows:
                return []
            cols = [d[0] for d in conn.execute("SELECT * FROM trades LIMIT 0").description]
            return [dict(zip(cols, row)) for row in rows]

    def get_closed_trades(self, limit: int = 100) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                """SELECT * FROM trades WHERE status NOT IN ('OPEN')
                   ORDER BY id DESC LIMIT ?""", (limit,)
            ).fetchall()
            if not rows:
                return []
            cols = [d[0] for d in conn.execute("SELECT * FROM trades LIMIT 0").description]
            return [dict(zip(cols, row)) for row in rows]

    def get_failure_cases(self, limit: int = 50) -> List[dict]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM failure_cases ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
            if not rows:
                return []
            cols = [d[0] for d in conn.execute("SELECT * FROM failure_cases LIMIT 0").description]
            return [dict(zip(cols, row)) for row in rows]

    def get_session_stats(self, date: str = None) -> dict:
        """
        Calcule les statistiques de session.
        date : format 'YYYY-MM-DD', défaut = aujourd'hui.
        """
        if date is None:
            date = datetime.date.today().isoformat()

        with self._connect() as conn:
            rows = conn.execute("""
                SELECT status, pnl_money, pnl_pips, error_category
                FROM trades
                WHERE DATE(open_time) = ? AND status NOT IN ('OPEN')
            """, (date,)).fetchall()

        if not rows:
            return {"date": date, "no_data": True}

        total   = len(rows)
        wins    = sum(1 for r in rows if r[0] == "WIN")
        losses  = sum(1 for r in rows if r[0] == "LOSS")
        be      = sum(1 for r in rows if r[0] == "BREAKEVEN")
        pnl     = sum(r[1] for r in rows if r[1])
        pips    = sum(r[2] for r in rows if r[2])
        wr      = (wins / total * 100) if total > 0 else 0
        avg_r   = pnl / total if total > 0 else 0

        # Top erreurs
        errors  = [r[3] for r in rows if r[3] and r[3] != "NONE"]
        from collections import Counter
        top_err = dict(Counter(errors).most_common(3))

        return {
            "date":         date,
            "total_trades": total,
            "win_count":    wins,
            "loss_count":   losses,
            "be_count":     be,
            "win_rate":     round(wr, 1),
            "total_pnl":    round(pnl, 2),
            "total_pips":   round(pips, 1),
            "avg_per_trade": round(avg_r, 2),
            "top_errors":   top_err,
        }

    def generate_session_report(self, date: str = None) -> str:
        """Génère un rapport post-session lisible."""
        stats = self.get_session_stats(date)
        if stats.get("no_data"):
            return "Aucun trade enregistré pour cette session."

        lines = [
            f"📅 RAPPORT DE SESSION — {stats['date']}",
            f"━" * 45,
            f"  Trades : {stats['total_trades']} | ✅ {stats['win_count']} | ❌ {stats['loss_count']} | ➡️ {stats['be_count']}",
            f"  Win Rate : {stats['win_rate']}%",
            f"  PnL Total : {stats['total_pnl']:+.2f}$",
            f"  Pips : {stats['total_pips']:+.1f}",
            f"━" * 45,
        ]
        if stats["top_errors"]:
            lines.append("  ⚠️ Erreurs fréquentes :")
            for err, count in stats["top_errors"].items():
                lines.append(f"    • {err} : {count}x — {ERROR_CATEGORIES.get(err, '')}")

        return "\n".join(lines)
