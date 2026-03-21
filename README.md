<div align="center">
  <img src="assets/logo.svg" alt="TRADEORACLE·AI" width="520"/>
  <br/><br/>

  [![CI](https://github.com/Turbo31150/TradeOracle/actions/workflows/ci.yml/badge.svg)](https://github.com/Turbo31150/TradeOracle/actions/workflows/ci.yml)
  [![License: MIT](https://img.shields.io/badge/License-MIT-00FF88?style=flat-square)](LICENSE)
  [![Python](https://img.shields.io/badge/Python-3.11+-FFD700?style=flat-square&logo=python&logoColor=black)](https://python.org)
  [![Gemini](https://img.shields.io/badge/Gemini-3-4285F4?style=flat-square&logo=google&logoColor=white)](#)
  [![MEXC](https://img.shields.io/badge/MEXC-800%2B_pairs-00FF88?style=flat-square)](#pipeline)
  [![MCP](https://img.shields.io/badge/MCP-enabled-FF8C00?style=flat-square)](#mcp)
  [![CI](https://img.shields.io/github/actions/workflow/status/Turbo31150/TradeOracle/ci.yml?branch=main&label=CI&style=flat-square)](https://github.com/Turbo31150/TradeOracle/actions)

  <br/>
  <p><strong>Agent de trading crypto autonome · Gemini 3 · Domino Pipeline · 800+ futures MEXC</strong></p>
  <p><em>Scan, analyse multi-IA, exécution autonome — le tout orchestré par un agent MCP vocal</em></p>

  [**Pipeline →**](#-pipeline-domino) · [**Signaux →**](#-types-de-signaux) · [**MCP →**](#-mcp-tools) · [**Installation →**](#-installation) · [**Config →**](#-configuration)
</div>

---

## Présentation

**TRADEORACLE·AI** est un agent de trading algorithmique autonome propulsé par **Gemini 3** (Google Cloud). Il scanne **800+ contrats futures MEXC**, génère des signaux via un pipeline multi-IA (Domino Pipeline), et exécute des trades en autonomie complète avec gestion TP/SL automatisée.

Construit pour le hackathon **Google Cloud Agent Development Kit**, il démontre comment un agent IA peut gérer l'intégralité d'une stratégie de trading — de la détection à l'exécution — sans intervention humaine.

---

## Architecture

```
TRADEORACLE·AI — Domino Pipeline
─────────────────────────────────────────────────────────────────
  MEXC Futures API (800+ paires)
         │
         ▼
  ┌─────────────────────────────┐
  │      Scanner Module          │  Scan toutes les 30s
  │  ATR · Volume · Momentum     │  Détection 5 types signaux
  │  RSI · Bollinger · FVG       │
  └──────────────┬──────────────┘
                 │ Signal candidat
                 ▼
  ┌─────────────────────────────┐
  │    Domino Pipeline           │  Analyse multi-IA parallèle
  │                             │
  │  Gemini 3.0 (analyse deep)  │  ← Poids 1.3
  │  Gemini Flash (validation)  │  ← Poids 1.0
  │  LM Studio local (hedge)    │  ← Poids 0.8
  └──────────────┬──────────────┘
                 │ Consensus IA
                 ▼
  ┌─────────────────────────────┐
  │   Execution Engine           │  Auto-trade ou alerte
  │  STRONG → trade immédiat    │  2+ votes consensus
  │  NORMAL → trade standard    │  1 vote
  │  SKIP   → pas d'action      │  0 vote
  └──────────────┬──────────────┘
                 │
                 ▼
  ┌─────────────────────────────┐
  │   TP/SL Manager              │
  │  TP1 +1.5% (33% position)  │
  │  TP2 +3.0% (75% position)  │
  │  TP3 +7.0% (100% sortie)   │
  │  SL  -1.2%                 │
  └──────────────┬──────────────┘
                 │
                 ▼
          Telegram notification
```

---

## Structure du projet

```
TradeOracle/
├── entrypoint.py           ← Point d'entrée principal agent
├── app.py                  ← Application FastAPI + WebSocket
├── requirements.txt        ← Dépendances Python
├── .env.example            ← Template configuration
├── agent/                  ← Cerveau de l'agent
│   ├── trading_agent.py    ← Agent principal Gemini 3
│   ├── consensus.py        ← Vote multi-IA
│   └── risk_manager.py     ← Gestion risques
├── pipeline/               ← Domino Pipeline
│   ├── scanner.py          ← Scan MEXC 800+ paires
│   ├── signals.py          ← Détection signaux
│   └── executor.py         ← Exécution ordres
├── mcp_server/             ← Server MCP outils
│   ├── server.py           ← Démarrage MCP
│   └── tools.py            ← 40+ tools déclarés
├── tools/                  ← Outils agent
│   ├── mexc_tools.py       ← API MEXC wrapper
│   ├── gemini_tools.py     ← Gemini integration
│   └── telegram_tools.py   ← Notifications
├── database/               ← Persistance
│   ├── models.py           ← SQLAlchemy models
│   └── db.py               ← Connection pool
├── config/                 ← Configuration
│   ├── settings.py         ← Paramètres trading
│   └── models_config.py    ← Config modèles IA
└── assets/                 ← Logo, médias
    └── logo.svg
```

---

## Types de signaux

| Signal | Description | Conditions |
|--------|-------------|------------|
| **BREAKOUT** | Cassure niveau résistance | Volume > 2× moyenne · ATR élevé |
| **REVERSAL** | Retournement tendance | RSI extrême + divergence |
| **BOUNCE** | Rebond support | Prix sur zone support clé |
| **MOMENTUM** | Continuation forte | Vague de momentum initiée |
| **FVG** | Fair Value Gap | Déséquilibre prix non comblé |

---

## Pipeline Domino

```python
# Paramètres du pipeline
MIN_SCORE    = 70       # Score minimum pour considérer un signal
MIN_VOLUME   = 1_000_000  # Volume minimum (1M USDT)
SCAN_PAIRS   = 800+     # Contrats futures MEXC scannés

# Consensus multi-IA
VOTE_STRONG  = 2+       # Trade immédiat (haute confiance)
VOTE_NORMAL  = 1        # Trade standard (confiance normale)
VOTE_SKIP    = 0        # Ignorer le signal

# TP/SL automatique
TP1_PCT = +1.5  ; TP1_CLOSE = 33%
TP2_PCT = +3.0  ; TP2_CLOSE = 75%
TP3_PCT = +7.0  ; TP3_CLOSE = 100%
SL_PCT  = -1.2
```

---

## MCP Tools

**40+ tools MCP** déclarés dans le serveur :

```python
# Exemples de tools disponibles
scan_market(symbol, timeframe)      # Scanner une paire
get_signal(symbol)                  # Obtenir signal IA
execute_trade(symbol, side, size)   # Exécuter un trade
get_positions()                     # Positions ouvertes
close_position(symbol)              # Fermer position
get_pnl(period)                     # PnL sur période
set_tp_sl(symbol, tp, sl)          # Configurer TP/SL
get_market_summary()                # Résumé marché
run_backtest(strategy, period)      # Backtest rapide
```

---

## Installation

```bash
git clone https://github.com/Turbo31150/TradeOracle.git
cd TradeOracle

pip install -r requirements.txt

cp .env.example .env
# Renseigner: GOOGLE_API_KEY, MEXC_API_KEY, TELEGRAM_BOT_TOKEN...

# Lancer l'agent
python entrypoint.py

# Ou en mode API
python app.py  # FastAPI sur :8080
```

---

## Configuration

```env
# Google Cloud / Gemini
GOOGLE_API_KEY=AIza...
GOOGLE_CLOUD_PROJECT=my-project

# MEXC Futures
MEXC_API_KEY=mx0v...
MEXC_SECRET_KEY=...
MEXC_BASE_URL=https://futures.mexc.com/api/v1

# Agent
MIN_SCORE=70
MIN_VOLUME=1000000
AUTO_TRADE=false          # true = exécution autonome

# Notifications
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# MCP Server
MCP_PORT=8090
```

---

<div align="center">

**Franc Delmas (Turbo31150)** · [github.com/Turbo31150](https://github.com/Turbo31150) · Toulouse, France

*TRADEORACLE·AI — Autonomous Crypto Trading Intelligence — MIT License*

</div>
