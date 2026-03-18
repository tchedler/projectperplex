# Command Center (Nouvelle Vitrine)

Ce dossier contient le squelette du **Command Center** : la future interface
principale de monitoring et de pilotage du bot.

## Objectif

- Remplacer progressivement les anciennes interfaces (War Room / Streamlit / Patron Dashboard)
- Regrouper le monitoring, les paramètres du bot, et les commandes de pilotage
- Fournir une API propre vers les données (scoring, structures ICT, positions, etc.)

## Usage

Pour l'instant, ce package est un stub et n'affiche qu'un message de démarrage :

```bash
python -m interface.command_center
```

## Prochaines étapes (à débattre)

- Choisir un framework (Dash, Streamlit, FastAPI + React, TUI, etc.)
- Concevoir la structure d'écran (vue globale, panel contrôle, log audit, etc.)
- Fournir une API de données pour éviter les accès directs aux caches
- Déplacer/mettre en quarantaine les anciennes interfaces (legacy)
