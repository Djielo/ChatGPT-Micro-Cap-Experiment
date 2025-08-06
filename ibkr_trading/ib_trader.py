# IBKR Trading Module
import asyncio
import logging
import threading
import time
from typing import Dict, List, Any
from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract
from ibapi.order import Order

# Configuration
from config import *

class IBTrader(EWrapper, EClient):
    """
    Module IBKR pour l'exécution automatisée des trades
    """
    
    def __init__(self):
        EClient.__init__(self, self)
        self.setup_logging()
        self.connected = False
        self.orders = []
        self.positions = {}
        self.logger.info("🏦 Module IBKR initialisé")
        
    def setup_logging(self):
        """Configure le logging pour le module IBKR"""
        self.logger = logging.getLogger('IBTrader')
    
    def connect_to_ib(self):
        """
        Connexion à Interactive Brokers
        """
        try:
            self.logger.info(f"🔌 Connexion à IBKR sur {IB_HOST}:{IB_PORT}")
            self.connect(IB_HOST, IB_PORT, IB_CLIENT_ID)
            
            # Démarrer le thread de connexion
            self.thread = threading.Thread(target=self.run)
            self.thread.start()
            
            # Attendre la connexion
            time.sleep(2)
            
            if self.connected:
                self.logger.info("✅ Connecté à IBKR avec succès")
            else:
                self.logger.warning("⚠️ Connexion IBKR en attente...")
                
        except Exception as e:
            self.logger.error(f"❌ Erreur connexion IBKR: {e}")
    
    def nextValidId(self, orderId: int):
        """Callback appelé quand la connexion est établie"""
        self.connected = True
        self.logger.info(f"✅ Connexion IBKR établie, Order ID: {orderId}")
    
    def error(self, reqId: int, errorCode: int, errorString: str):
        """Callback pour les erreurs"""
        self.logger.error(f"❌ Erreur IBKR {errorCode}: {errorString}")
    
    def orderStatus(self, orderId: int, status: str, filled: float, remaining: float, avgFillPrice: float, permId: int, clientId: int, whyHeld: str, mktCapPrice: float):
        """Callback pour le statut des ordres"""
        self.logger.info(f"📊 Ordre {orderId}: {status}, Rempli: {filled}, Restant: {remaining}")
    
    async def execute_trades(self, decisions: Dict[str, Dict]):
        """
        Exécute les trades basés sur les décisions
        """
        if not self.connected:
            self.connect_to_ib()
        
        self.logger.info("🏦 Début de l'exécution des trades")
        
        try:
            executed_trades = []
            
            for ticker, decision in decisions.items():
                action = decision.get('action', 'HOLD')
                confidence = decision.get('confidence', 0.5)
                
                if action != 'HOLD':
                    self.logger.info(f"📈 Exécution {action} pour {ticker} (confiance: {confidence})")
                    
                    # Simuler l'exécution (pour l'instant)
                    trade_result = await self.execute_single_trade(ticker, action, decision)
                    executed_trades.append(trade_result)
                    
                    # Log du trade
                    self.log_trade(ticker, action, decision)
            
            self.logger.info(f"✅ Exécution terminée: {len(executed_trades)} trades")
            return executed_trades
            
        except Exception as e:
            self.logger.error(f"❌ Erreur dans l'exécution des trades: {e}")
            return []
    
    async def execute_single_trade(self, ticker: str, action: str, decision: Dict) -> Dict:
        """
        Exécute un trade individuel
        """
        try:
            # Créer le contrat
            contract = self.create_contract(ticker)
            
            # Créer l'ordre
            order = self.create_order(action, decision)
            
            # Simuler l'exécution (pour l'instant)
            # En production, vous utiliseriez: self.placeOrder(orderId, contract, order)
            
            trade_result = {
                'ticker': ticker,
                'action': action,
                'status': 'SIMULATED',
                'confidence': decision.get('confidence', 0.5),
                'reason': decision.get('reason', ''),
                'timestamp': time.time()
            }
            
            self.logger.info(f"📊 Trade simulé: {ticker} {action}")
            return trade_result
            
        except Exception as e:
            self.logger.error(f"Erreur exécution trade {ticker}: {e}")
            return {
                'ticker': ticker,
                'action': action,
                'status': 'ERROR',
                'error': str(e)
            }
    
    def create_contract(self, ticker: str) -> Contract:
        """
        Crée un contrat IBKR pour un ticker
        """
        contract = Contract()
        contract.symbol = ticker
        contract.secType = "STK"
        contract.exchange = "SMART"
        contract.currency = "USD"
        return contract
    
    def create_order(self, action: str, decision: Dict) -> Order:
        """
        Crée un ordre IBKR
        """
        order = Order()
        order.action = action
        order.orderType = DEFAULT_ORDER_TYPE
        order.totalQuantity = self.calculate_position_size(decision)
        order.tif = DEFAULT_TIF
        
        # Ajouter stop-loss si nécessaire
        if decision.get('confidence', 0.5) < 0.4:
            order.auxPrice = self.calculate_stop_loss(decision)
        
        return order
    
    def calculate_position_size(self, decision: Dict) -> int:
        """
        Calcule la taille de position basée sur la confiance
        """
        confidence = decision.get('confidence', 0.5)
        
        # Logique de position sizing
        if confidence > 0.8:
            return 100  # Position importante
        elif confidence > 0.6:
            return 50   # Position moyenne
        else:
            return 25   # Position petite
    
    def calculate_stop_loss(self, decision: Dict) -> float:
        """
        Calcule le stop-loss basé sur le pourcentage configuré
        """
        # Simulation - en production, vous calculeriez le vrai prix
        return 0.0
    
    def log_trade(self, ticker: str, action: str, decision: Dict):
        """
        Enregistre le trade dans les logs
        """
        log_entry = {
            'timestamp': time.time(),
            'ticker': ticker,
            'action': action,
            'confidence': decision.get('confidence', 0.5),
            'reason': decision.get('reason', ''),
            'status': 'EXECUTED'
        }
        
        self.orders.append(log_entry)
        self.logger.info(f"📝 Trade loggé: {ticker} {action}")
    
    def get_portfolio_summary(self) -> Dict:
        """
        Retourne un résumé du portefeuille
        """
        return {
            'total_positions': len(self.positions),
            'total_orders': len(self.orders),
            'connection_status': 'Connected' if self.connected else 'Disconnected'
        }

# Test du module IBKR
async def test_ib_trader():
    """Test du module IBKR"""
    trader = IBTrader()
    
    # Simuler des décisions de trading
    test_decisions = {
        'ABEO': {'action': 'BUY', 'confidence': 0.75, 'reason': 'Strong signals'},
        'CADL': {'action': 'HOLD', 'confidence': 0.5, 'reason': 'Mixed signals'}
    }
    
    results = await trader.execute_trades(test_decisions)
    print("IBKR Trading Results:", results)

if __name__ == "__main__":
    asyncio.run(test_ib_trader()) 