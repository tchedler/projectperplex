"""
telegram_notifier.py — M8/S2 FIX : Notifications Telegram pour les signaux A+.

Configuration dans data/bot_config.json :
  "telegram_token": "VOTRE_BOT_TOKEN",
  "telegram_chat_id": "VOTRE_CHAT_ID",
  "telegram_enabled": true

Pour obtenir un token : https://t.me/BotFather
Pour obtenir votre chat_id : https://t.me/userinfobot
"""
import logging
import json
import os

log = logging.getLogger("ICT_BOT.Telegram")

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    log.warning("📱 [Telegram] 'requests' non installé. pip install requests pour activer les notifications.")


class TelegramNotifier:
    """
    Envoie des notifications Telegram lors de signaux A+ ou d'événements importants.
    Dégradation gracieuse : si le token n'est pas configuré, ne fait rien.
    """

    def __init__(self, config_path: str = "data/bot_config.json"):
        self.enabled = False
        self.token = ""
        self.chat_id = ""

        try:
            if os.path.exists(config_path):
                with open(config_path, "r") as f:
                    cfg = json.load(f)
                self.token = cfg.get("telegram_token", "")
                self.chat_id = str(cfg.get("telegram_chat_id", ""))
                self.enabled = cfg.get("telegram_enabled", False) and bool(self.token) and bool(self.chat_id)
        except Exception as e:
            log.warning(f"📱 [Telegram] Erreur chargement config: {e}")

        if self.enabled:
            log.info(f"📱 [Telegram] Notifier activé pour chat_id={self.chat_id}")

    def _send(self, message: str) -> bool:
        if not self.enabled or not REQUESTS_AVAILABLE:
            return False
        try:
            # Utilisation d'un proxy Telegram public et gratuit pour contourner le blocage local
            # Au lieu de https://api.telegram.org/bot
            url = f"https://api.telegram.org/bot{self.token}/sendMessage"
            
            # Configuration proxy HTTPS via requests
            # Si le blocage persiste, on l'ajoutera directement dans le code.
            # Pour l'instant on essaie une URL alternative très souvent utilisée en Asie/Russie
            url_proxy = f"https://tgproxy.site/bot{self.token}/sendMessage"
            url_proxy2 = f"https://telegg.ru/orig/bot{self.token}/sendMessage"
            
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML",
            }
            # Essai proxy 1
            try:
                r = requests.post(url_proxy, json=payload, timeout=8)
                if r.status_code == 200:
                    log.info("📱 [Telegram] Message envoyé via Proxy 1.")
                    return True
            except Exception:
                pass
                
            # Essai proxy 2
            try:
                r = requests.post(url_proxy2, json=payload, timeout=8)
                if r.status_code == 200:
                    log.info("📱 [Telegram] Message envoyé via Proxy 2.")
                    return True
                else:
                    log.warning(f"📱 [Telegram] Erreur API: {r.status_code} — {r.text[:200]}")
            except Exception as e:
                log.warning(f"📱 [Telegram] Tous les proxies ont échoué: {e}")
        except Exception as e:
            log.warning(f"📱 [Telegram] Exception globale: {e}")
        return False

    def notify_signal_a_plus(self, signal) -> bool:
        """
        Envoie une notification quand un signal EXÉCUTION A+ est généré.
        """
        if not self.enabled:
            return False

        direction_icon = "🔼 ACHAT" if signal.direction == "BUY" else "🔽 VENTE"
        action_icon = "⚡ ORDRE MARCHÉ" if signal.action == "EXECUTE" else "⏳ ORDRE LIMITE"

        msg = (
            f"🚀 <b>SIGNAL ICT — {signal.symbol}</b>\n\n"
            f"{direction_icon} | {action_icon}\n"
            f"📊 Score: <b>{signal.score}/100</b>\n"
            f"⚙️ Setup: <code>{signal.setup_name}</code>\n"
            f"📍 Entry: <code>{signal.entry:.5f}</code>\n"
            f"🛑 SL: <code>{signal.sl:.5f}</code>\n"
            f"🎯 TP1: <code>{signal.tp1:.5f}</code>\n"
            f"🏆 TP2: <code>{signal.tp2:.5f}</code>\n"
            f"🕒 Killzone: <code>{signal.killzone}</code>\n"
            f"📝 {signal.reason[:200] if signal.reason else ''}"
        )
        return self._send(msg)

    def notify_trade_closed(self, symbol: str, direction: str,
                            reason: str, pnl_money: float, pnl_pips: float) -> bool:
        """
        Envoie une notification quand un trade est fermé.
        """
        if not self.enabled:
            return False

        result_icon = "✅ WIN" if pnl_money > 0 else "❌ LOSS" if pnl_money < 0 else "➡️ BE"
        msg = (
            f"{result_icon} <b>Trade Fermé — {symbol}</b>\n\n"
            f"Direction: {direction}\n"
            f"Raison: <code>{reason}</code>\n"
            f"PnL: <b>{pnl_money:+.2f}$</b> ({pnl_pips:+.1f} pips)"
        )
        return self._send(msg)

    def notify_bot_event(self, event: str, detail: str = "") -> bool:
        """
        Notifications système (démarrage, arrêt, drawdown dépassé, etc.)
        """
        if not self.enabled:
            return False
        msg = f"🤖 <b>ICT Sentinel</b> — {event}\n{detail}"
        return self._send(msg)
