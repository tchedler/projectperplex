import os
import sys
from datetime import datetime

print("[BOOT] audit_script.py started.")
# Import the orchestrator from the main application
try:
    print("[BOOT] Importing ProOrchestrator from main...")
    from main import ProOrchestrator
    print("[BOOT] Import successful.")
except Exception as e:
    print(f"[BOOT] Import failed: {e}")
    sys.exit(1)

def main():
    # Symbol can be overridden via env var for testing
    symbol = os.getenv("AUDIT_SYMBOL", "XAUUSD")
    print(f"[START] Starting audit for {symbol}...")
    orch = ProOrchestrator(symbol)
    print(f"[DEBUG] Orchestrator initialized.")

    # Fetch a timeframe that is used for most analyses (M15)
    print(f"[DEBUG] Fetching M15 data...")
    df = orch._fetch_pro("M15")
    if df is None:
        print("[INFO] Fetch returned None. Using dummy data for audit.")
        # Create a dummy DataFrame with minimal required columns for downstream analysis
        import numpy as np
        import pandas as pd
        dates = pd.date_range(end=datetime.utcnow(), periods=30, freq='T')
        data = {
            "Open": np.random.rand(30) * 100,
            "High": np.random.rand(30) * 100 + 1,
            "Low": np.random.rand(30) * 100 - 1,
            "Close": np.random.rand(30) * 100,
        }
        df = pd.DataFrame(data, index=dates)
    else:
        print(f"[DEBUG] Data fetched: {len(df)} rows.")

    # Run the various ICT analyses
    print(f"[DEBUG] Running TemporalClock audit...")
    clock = orch.time_ac.get_audit()
    print(f"[DEBUG] Running SMCSpecialist analysis...")
    smc = orch.smc_ac.analyze(df, clock=clock)
    print(f"[DEBUG] Running LiquidityTracker analysis...")
    liq = orch.liq_ac.analyze(df)
    print(f"[DEBUG] Running ExecutionPrecision analysis...")
    exe = orch.exe_ac.analyze(df, smc, liq)
    print(f"[DEBUG] Running MMXMLogic model...")
    mmxm = orch.mmxm_ac.get_model(df, clock, smc, liq)
    print(f"[DEBUG] Running CorrelationSMT analysis...")
    smt = orch.smt_ac.analyze_smt(df)
    print(f"[DEBUG] All analyses completed.")

    # ------------------------------------------------------------------
    # Compute a compliance score (mirrors the logic used in dashboard_v8)
    # ------------------------------------------------------------------
    score = 0
    if clock.get('killzone') != "NONE":
        score += 10
    if clock.get('macro') != "NONE":
        score += 10
    if smc.get('is_displaced'):
        score += 20
    prot_low = smc.get('protected_levels', {}).get('low', {}).get('status')
    prot_high = smc.get('protected_levels', {}).get('high', {}).get('status')
    if prot_low == "PROTECTED" or prot_high == "PROTECTED":
        score += 10
    if smt.get('smt_divergence'):
        score += 15
    eq_zone = exe.get('equilibrium', {}).get('zone')
    if eq_zone == "DISCOUNT" and "BULL" in clock.get('killzone', ''):
        score += 15
    if eq_zone == "PREMIUM" and "BEAR" in clock.get('killzone', ''):
        score += 15
    if mmxm.get('silver_bullet') != "INACTIVE":
        score += 20
    score = min(score, 100)

    # ------------------------------------------------------------------
    # Verify that the chart generation routine works without raising
    # ------------------------------------------------------------------
    try:
        fig = orch.build_chart_pro(df, smc, liq, exe, mmxm, "M15")
        chart_ok = True
        chart_err = ""
    except Exception as e:
        chart_ok = False
        chart_err = str(e)

    # ------------------------------------------------------------------
    # Write a markdown report with the findings
    # ------------------------------------------------------------------
    report_path = os.path.abspath("audit_report.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# ICT Graph Audit Report\n\n")
        f.write(f"**Symbol:** {symbol}\n")
        f.write(f"**Generated:** {datetime.utcnow().isoformat()} UTC\n\n")
        f.write("## Overall Compliance Score\n")
        f.write(f"**Score:** {score}/100\n\n")
        f.write("### Component Checklist\n")
        f.write(f"- Killzone/Macro present: {'✅' if clock.get('killzone') != 'NONE' or clock.get('macro') != 'NONE' else '❌'}\n")
        f.write(f"- SMC displacement detected: {'✅' if smc.get('is_displaced') else '❌'}\n")
        f.write(f"- Protected levels status: {'✅' if prot_low == 'PROTECTED' or prot_high == 'PROTECTED' else '❌'}\n")
        f.write(f"- SMT divergence: {'✅' if smt.get('smt_divergence') else '❌'}\n")
        f.write(f"- Execution equilibrium zone: {'✅' if exe.get('equilibrium') else '❌'}\n")
        f.write(f"- MMXM silver bullet active: {'✅' if mmxm.get('silver_bullet') != 'INACTIVE' else '❌'}\n")
        f.write(f"- Chart generation success: {'✅' if chart_ok else f'❌ ({chart_err})'}\n")

    print(f"[INFO] Audit completed – report written to {report_path}")

if __name__ == "__main__":
    main()
