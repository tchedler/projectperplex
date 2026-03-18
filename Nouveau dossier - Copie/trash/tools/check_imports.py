import sys
import os

# FIX: Python 3.14 incompatibility with protobuf C-extension metaclasses
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"
import logging
from pathlib import Path

# Ajouter le dossier parent (racine du projet) au PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CheckImports")

def check_all() -> bool:
    """Verifie que tous les modules peuvent etre importes sans erreur."""
    try:
        # Gateway
        from gateway.mt5_connector import MT5Connector
        from gateway.tick_receiver import TickReceiver
        
        # Analysis
        from analysis.kb5_engine import KB5Engine
        from analysis.killswitch_engine import KillSwitchEngine
        from analysis.bias_detector import BiasDetector

        # UI
        import streamlit
        import rich
        import colorlog
        
        # Execution
        from execution.order_manager import OrderManager
        
        # Supervisor
        from supervisor.supervisor import Supervisor
        
        logger.info("CheckImports — Tous les modules critiques sont importables ✅")
        return True
    except Exception as e:
        logger.error(f"CheckImports — Erreur d'import : {e}")
        return False

if __name__ == "__main__":
    if check_all():
        sys.exit(0)
    else:
        sys.exit(1)
