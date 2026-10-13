"""
Meme Hunter - Specialized Autonomous Agents Package (Sprint 30 & 31)
Multi-Agent DAG Signal & Governance Architecture.
"""

from portfolio.agents.base_agent import BaseSignalAgent, AgentProposal
from portfolio.agents.regime_agent import RegimeHMMAgent
from portfolio.agents.technical_agent import TechnicalMicroAgent
from portfolio.agents.sentiment_agent import SentimentAgent
from portfolio.agents.risk_manager_agent import RiskManagerAgent, RiskVerdict

__all__ = [
    "BaseSignalAgent",
    "AgentProposal",
    "RegimeHMMAgent",
    "TechnicalMicroAgent",
    "SentimentAgent",
    "RiskManagerAgent",
    "RiskVerdict",
]
