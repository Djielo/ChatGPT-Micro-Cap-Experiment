# Core Orchestrator - Cerveau Central du Système
import asyncio
import logging
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import json

# Configuration
import sys
import os
sys.path.append(os.path.dirname(__file__))
from config import *

class TradingOrchestrator:
    """
    Orchestrateur central qui coordonne tous les modules du système de trading
    """
    
    def __init__(self):
        self.setup_logging()
        self.modules = {}
        self.communication = ModuleCommunication()
        self.load_modules()
        
    def setup_logging(self):
        """Configure le système de logging"""
        logging.basicConfig(
            level=getattr(logging, ORCHESTRATOR_LOG_LEVEL),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(ORCHESTRATOR_LOG_FILE, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('TradingOrchestrator')
        self.logger.info("Orchestrateur initialise")
    
    def load_modules(self):
        """Charge tous les modules indépendants"""
        try:
            # Charger HRM
            self.modules['hrm'] = self.load_hrm_module()
            self.logger.info("✅ Module HRM chargé")
            
            # Charger DeepSeek
            self.modules['deepseek'] = self.load_deepseek_module()
            self.logger.info("✅ Module DeepSeek chargé")
            
            # Charger IBKR
            self.modules['ibkr'] = self.load_ibkr_module()
            self.logger.info("✅ Module IBKR chargé")
            
        except Exception as e:
            self.logger.error(f"❌ Erreur lors du chargement des modules: {e}")
            raise
    
    def load_hrm_module(self):
        """Charge le module HRM"""
        try:
            sys.path.append(HRM_MODULE_PATH)
            from hrm_analyzer import HRMAnalyzer
            return HRMAnalyzer()
        except ImportError as e:
            self.logger.warning(f"Module HRM non disponible: {e}")
            return None
    
    def load_deepseek_module(self):
        """Charge le module DeepSeek"""
        try:
            import os
            original_cwd = os.getcwd()
            os.chdir(DEEPSEEK_MODULE_PATH)
            sys.path.append(DEEPSEEK_MODULE_PATH)
            from deepseek_analyzer import DeepSeekAnalyzer
            os.chdir(original_cwd)
            return DeepSeekAnalyzer()
        except ImportError as e:
            self.logger.warning(f"Module DeepSeek non disponible: {e}")
            return None
    
    def load_ibkr_module(self):
        """Charge le module IBKR"""
        try:
            sys.path.append(IBKR_MODULE_PATH)
            from ib_trader import IBTrader
            return IBTrader()
        except ImportError as e:
            self.logger.warning(f"Module IBKR non disponible: {e}")
            return None
    
    async def orchestrate_daily_analysis(self):
        """
        Orchestre l'analyse quotidienne complète
        """
        self.logger.info("🔄 Début de l'orchestration quotidienne")
        
        try:
            # 1. HRM analyse (indépendant)
            self.logger.info("🧠 HRM analyse le portefeuille...")
            hrm_analysis = await self.run_hrm_analysis()
            
            # 2. DeepSeek recherche (indépendant)
            self.logger.info("🔍 DeepSeek recherche les dernières données...")
            market_data = await self.run_deepseek_analysis()
            
            # 3. Orchestrateur combine et décide (cerveau central)
            self.logger.info("⚡ Orchestrateur combine les analyses...")
            final_decisions = self.make_final_decisions(hrm_analysis, market_data)
            
            # 4. IBKR exécute (indépendant)
            self.logger.info("🏦 IBKR exécute les trades...")
            await self.run_ibkr_execution(final_decisions)
            
            self.logger.info("✅ Orchestration quotidienne terminée avec succès!")
            return final_decisions
            
        except Exception as e:
            self.logger.error(f"❌ Erreur dans l'orchestration: {e}")
            raise
    
    async def run_hrm_analysis(self) -> Dict:
        """Exécute l'analyse HRM"""
        if self.modules.get('hrm'):
            try:
                return await self.modules['hrm'].analyze_portfolio()
            except Exception as e:
                self.logger.error(f"Erreur HRM: {e}")
                return {}
        else:
            self.logger.warning("Module HRM non disponible")
            return {}
    
    async def run_deepseek_analysis(self) -> Dict:
        """Exécute l'analyse DeepSeek"""
        if self.modules.get('deepseek'):
            try:
                return await self.modules['deepseek'].get_latest_market_data()
            except Exception as e:
                self.logger.error(f"Erreur DeepSeek: {e}")
                return {}
        else:
            self.logger.warning("Module DeepSeek non disponible")
            return {}
    
    async def run_ibkr_execution(self, decisions: Dict):
        """Exécute les trades via IBKR"""
        if self.modules.get('ibkr'):
            try:
                await self.modules['ibkr'].execute_trades(decisions)
            except Exception as e:
                self.logger.error(f"Erreur IBKR: {e}")
        else:
            self.logger.warning("Module IBKR non disponible")
    
    def make_final_decisions(self, hrm_analysis: Dict, market_data: Dict) -> Dict:
        """
        Logique de décision finale de l'orchestrateur
        Combine les insights de tous les modules
        """
        decisions = {}
        
        # Obtenir la liste des tickers du portefeuille original
        original_portfolio = self.load_original_portfolio()
        tickers = [row['Ticker'] for row in original_portfolio if row['Ticker'] != 'TOTAL']
        
        for ticker in tickers:
            hrm_decision = hrm_analysis.get(ticker, {})
            market_info = market_data.get(ticker, {})
            
            # Logique de combinaison intelligente
            final_decision = self.combine_insights(hrm_decision, market_info)
            decisions[ticker] = final_decision
            
            self.logger.info(f"Décision pour {ticker}: {final_decision}")
        
        return decisions
    
    def combine_insights(self, hrm_decision: Dict, market_info: Dict) -> Dict:
        """
        Combine les insights HRM et DeepSeek
        Logique de pondération et combinaison
        """
        # Extraire les scores de confiance
        confidence_hrm = hrm_decision.get('confidence', 0.5)
        confidence_market = market_info.get('sentiment_score', 0.5)
        
        # Logique de décision basée sur les deux sources
        if confidence_hrm > 0.7 and confidence_market > 0.6:
            return {
                'action': 'BUY', 
                'confidence': (confidence_hrm + confidence_market) / 2,
                'reason': 'Strong signals from both HRM and market data'
            }
        elif confidence_hrm < 0.3 or confidence_market < 0.4:
            return {
                'action': 'SELL', 
                'confidence': 1 - (confidence_hrm + confidence_market) / 2,
                'reason': 'Weak signals from analysis'
            }
        else:
            return {
                'action': 'HOLD', 
                'confidence': 0.5,
                'reason': 'Mixed signals, maintaining position'
            }
    
    def load_original_portfolio(self) -> list:
        """Charge le portefeuille du système original"""
        try:
            import pandas as pd
            df = pd.read_csv("MCExperiment_system/chatgpt_portfolio_update.csv")
            # Obtenir les dernières données pour chaque ticker
            latest_data = []
            for ticker in df['Ticker'].unique():
                if ticker != 'TOTAL':
                    ticker_data = df[df['Ticker'] == ticker].iloc[-1]
                    latest_data.append({
                        'Ticker': ticker,
                        'Shares': ticker_data['Shares'],
                        'Cost_Basis': ticker_data['Cost Basis'],
                        'Current_Price': ticker_data['Current Price']
                    })
            return latest_data
        except Exception as e:
            self.logger.error(f"Erreur chargement portefeuille: {e}")
            return []

class ModuleCommunication:
    """Gestion de la communication entre modules"""
    
    def __init__(self):
        self.message_queue = []
        self.logger = logging.getLogger('ModuleCommunication')
    
    def send_to_module(self, module_name: str, data: Dict):
        """Envoie des données à un module spécifique"""
        message = {
            'timestamp': datetime.now().isoformat(),
            'module': module_name,
            'data': data
        }
        self.message_queue.append(message)
        self.logger.debug(f"Message envoyé à {module_name}: {data}")
    
    def receive_from_module(self, module_name: str) -> list:
        """Reçoit les données d'un module spécifique"""
        messages = [msg for msg in self.message_queue if msg['module'] == module_name]
        self.logger.debug(f"Messages reçus de {module_name}: {len(messages)}")
        return messages

# Test de l'orchestrateur
async def test_orchestrator():
    """Test de l'orchestrateur"""
    orchestrator = TradingOrchestrator()
    await orchestrator.orchestrate_daily_analysis()

if __name__ == "__main__":
    asyncio.run(test_orchestrator()) 