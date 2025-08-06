# HRM Financial Analyzer Module
import asyncio
import logging
from typing import Dict, List, Any
import pandas as pd
import numpy as np

# Configuration
import sys
import os
sys.path.append(os.path.dirname(__file__))
from config import *

# Import de l'intégrateur HRM financier
from financial_hrm_integration import FinancialHRMIntegrator

class HRMAnalyzer:
    """
    Module HRM pour l'analyse hiérarchique des micro-caps
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger.info("🧠 Module HRM initialisé")
        
        # Initialiser l'intégrateur HRM financier
        self.hrm_integrator = FinancialHRMIntegrator()
        
        # Simulation du modèle HRM (à remplacer par votre vrai HRM)
        self.model_loaded = self.load_hrm_model()
        
    def setup_logging(self):
        """Configure le logging pour le module HRM"""
        self.logger = logging.getLogger('HRMAnalyzer')
    
    def load_hrm_model(self) -> bool:
        """
        Charge le modèle HRM
        Pour l'instant, simulation - à remplacer par votre vrai HRM
        """
        try:
            # Simulation du chargement du modèle HRM
            self.logger.info("📥 Chargement du modèle HRM...")
            
            # Ici vous intégreriez votre vrai HRM
            # self.model = load_hrm_model(HRM_MODEL_PATH)
            
            self.logger.info("✅ Modèle HRM chargé avec succès")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur chargement modèle HRM: {e}")
            return False
    
    async def analyze_portfolio(self) -> Dict[str, Dict]:
        """
        Analyse hiérarchique du portefeuille
        Retourne les décisions pour chaque ticker
        """
        self.logger.info("🔍 Début de l'analyse HRM du portefeuille")
        
        try:
            # Charger le portefeuille original
            portfolio_data = self.load_portfolio_data()
            
            # Analyser chaque ticker
            analysis_results = {}
            
            for ticker_data in portfolio_data:
                ticker = ticker_data['Ticker']
                self.logger.info(f"🧠 Analyse HRM pour {ticker}")
                
                # Analyse hiérarchique complète
                analysis = await self.analyze_microcap(ticker_data)
                analysis_results[ticker] = analysis
            
            self.logger.info(f"✅ Analyse HRM terminée pour {len(analysis_results)} tickers")
            return analysis_results
            
        except Exception as e:
            self.logger.error(f"❌ Erreur dans l'analyse HRM: {e}")
            return {}
    
    async def analyze_microcap(self, ticker_data: Dict) -> Dict:
        """
        Analyse hiérarchique d'une micro-cap
        Utilise l'intégrateur HRM financier
        """
        ticker = ticker_data['Ticker']
        
        try:
            # Utiliser l'intégrateur HRM pour l'analyse hiérarchique
            hrm_analysis = self.hrm_integrator.analyze_microcap_hierarchical(ticker_data)
            
            # Extraire les résultats
            hierarchical_analysis = hrm_analysis.get('hierarchical_analysis', {})
            decision = hrm_analysis.get('decision', {})
            
            return {
                'ticker': ticker,
                'macro_analysis': macro_analysis,
                'sector_analysis': sector_analysis,
                'company_analysis': company_analysis,
                'trade_decision': trade_decision,
                'confidence': trade_decision.get('confidence', 0.5),
                'timestamp': pd.Timestamp.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"Erreur analyse {ticker}: {e}")
            return {
                'ticker': ticker,
                'confidence': 0.0,
                'error': str(e)
            }
    
    async def analyze_macro_environment(self, ticker_data: Dict) -> Dict:
        """
        Niveau 1: Analyse macro-économique
        """
        # Simulation d'analyse macro avec HRM
        # Ici vous utiliseriez votre vrai HRM pour l'analyse macro
        
        return {
            'economic_conditions': 'stable',
            'interest_rates': 'neutral',
            'market_sentiment': 'positive',
            'confidence': 0.7
        }
    
    async def analyze_sector_trends(self, ticker_data: Dict) -> Dict:
        """
        Niveau 2: Analyse sectorielle
        """
        ticker = ticker_data['Ticker']
        
        # Simulation d'analyse sectorielle avec HRM
        # Ici vous utiliseriez votre vrai HRM pour l'analyse sectorielle
        
        return {
            'sector': 'biotechnology',
            'sector_trend': 'bullish',
            'competition_level': 'medium',
            'regulatory_environment': 'favorable',
            'confidence': 0.8
        }
    
    async def analyze_company_fundamentals(self, ticker_data: Dict) -> Dict:
        """
        Niveau 3: Analyse d'entreprise
        """
        ticker = ticker_data['Ticker']
        
        # Simulation d'analyse d'entreprise avec HRM
        # Ici vous utiliseriez votre vrai HRM pour l'analyse fondamentale
        
        return {
            'financial_health': 'good',
            'growth_potential': 'high',
            'management_quality': 'excellent',
            'risk_level': 'medium',
            'confidence': 0.75
        }
    
    async def make_trading_decision(self, macro: Dict, sector: Dict, company: Dict) -> Dict:
        """
        Niveau 4: Décision de trading finale
        Combine toutes les analyses pour prendre une décision
        """
        # Logique de décision basée sur les analyses hiérarchiques
        macro_confidence = macro.get('confidence', 0.5)
        sector_confidence = sector.get('confidence', 0.5)
        company_confidence = company.get('confidence', 0.5)
        
        # Calcul du score de confiance global
        overall_confidence = (macro_confidence + sector_confidence + company_confidence) / 3
        
        # Logique de décision
        if overall_confidence > CONFIDENCE_THRESHOLD_HIGH:
            action = 'BUY'
            reason = 'Strong hierarchical analysis signals'
        elif overall_confidence < CONFIDENCE_THRESHOLD_LOW:
            action = 'SELL'
            reason = 'Weak hierarchical analysis signals'
        else:
            action = 'HOLD'
            reason = 'Mixed hierarchical analysis signals'
        
        return {
            'action': action,
            'confidence': overall_confidence,
            'reason': reason,
            'macro_score': macro_confidence,
            'sector_score': sector_confidence,
            'company_score': company_confidence
        }
    
    def load_portfolio_data(self) -> List[Dict]:
        """
        Charge les données du portefeuille original
        """
        try:
            df = pd.read_csv("MCExperiment_system/chatgpt_portfolio_update.csv")
            
            # Obtenir les dernières données pour chaque ticker
            portfolio_data = []
            for ticker in df['Ticker'].unique():
                if ticker != 'TOTAL':
                    ticker_data = df[df['Ticker'] == ticker].iloc[-1]
                    portfolio_data.append({
                        'Ticker': ticker,
                        'Shares': ticker_data['Shares'],
                        'Cost_Basis': ticker_data['Cost Basis'],
                        'Current_Price': ticker_data['Current Price'],
                        'PnL': ticker_data['PnL']
                    })
            
            return portfolio_data
            
        except Exception as e:
            self.logger.error(f"Erreur chargement portefeuille: {e}")
            return []

# Test du module HRM
async def test_hrm_analyzer():
    """Test du module HRM"""
    analyzer = HRMAnalyzer()
    results = await analyzer.analyze_portfolio()
    print("HRM Analysis Results:", results)

if __name__ == "__main__":
    asyncio.run(test_hrm_analyzer()) 