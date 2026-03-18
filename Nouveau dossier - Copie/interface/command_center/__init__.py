"""Nouvelle interface "Command Center" (Moniteur + Centre de Commande).

Ce package est destiné à héberger la nouvelle vitrine UI qui remplacera
les anciens dashboards (War Room, Streamlit, Patron Dashboard).

Objectifs :
- Fournir un point d'entrée unique pour le monitoring et le pilotage du bot
- Permettre d'activer / désactiver facilement les anciennes interfaces
- Garder le moteur (analyse, scoring, execution) intact

Pour l'instant, ce package est une coquille et servira de base à la nouvelle UI.
"""

from .command_center import run

__all__ = ["run"]
