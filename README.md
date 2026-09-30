# SAINT BOT

A modular demo-first MT5 trading system.

## Components
- DASHBOARD: mobile-first control panel.
- MT5_ENGINE: MQL5 execution and position management.
- SAINT_AI_ENGINE: explainable multi-factor decision layer.
- SIGNAL_ENGINE: signal formatting.
- RISK_ENGINE: account/risk checks.
- server.py: central local API.

## First run
1. Install Python 3.
2. From the SAINT-BOT root:
   `python -m pip install -r requirements.txt`
3. Start:
   `python server.py`
4. Open:
   `http://127.0.0.1:5000`
5. Compile `MT5_ENGINE/SAINT_BOT.mq5` in MetaEditor.
6. Attach it to XAUUSD.c on a DEMO account.
7. The EA currently has `DemoOnlyGuard=true`.

## MT5 remote-control note
The current EA includes the architecture placeholder for remote control, but trade execution is local to MT5. A production multi-account VPS deployment requires authenticated HTTPS, per-account terminal management, secrets handling and explicit WebRequest allow-listing.

## Safety
No trading strategy guarantees profit. Test with Strategy Tester and demo accounts before considering live use.
