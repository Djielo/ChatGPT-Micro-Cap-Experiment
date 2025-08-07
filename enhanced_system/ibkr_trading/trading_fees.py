# Trading Fees Manager - Gestionnaire des Frais de Trading
"""
Gestionnaire centralisé des frais de trading IBKR
Utilisé pour paper trading ET live trading
Basé sur les vrais frais IBKR officiels
"""

import logging
from typing import Dict, Optional
from datetime import datetime

class TradingFeesManager:
    """
    Gestionnaire des frais de trading IBKR
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger.info("💰 Gestionnaire des frais de trading initialisé")
        
        # Frais IBKR officiels (source: interactivebrokers.com)
        self.IBKR_FEES = {
            # Commissions actions US
            'us_stocks': {
                'per_share': 0.005,  # 0,005 USD par action
                'min_per_order': 1.0,  # Minimum 1 USD par ordre
                'max_percentage': 0.01,  # Plafond 1% de la valeur
                'description': 'Actions US - IBKR Pro'
            },
            
            # Frais de change (si applicable)
            'fx_fees': {
                'usd_eur': 0.0002,  # 0,02% pour USD/EUR
                'description': 'Frais de change USD/EUR'
            },
            
            # Frais de garde
            'custody_fees': {
                'under_100k': 0.0,  # Gratuit sous 100k
                'over_100k': 0.0,   # À vérifier selon le compte
                'description': 'Frais de garde mensuels'
            },
            
            # Frais réglementaires
            'regulatory_fees': {
                'finra': 0.000119,  # FINRA Trading Activity Fee
                'sec': 0.0000229,   # SEC Fee (ventes uniquement)
                'description': 'Frais réglementaires US'
            }
        }
        
    def setup_logging(self):
        """Configure le logging"""
        self.logger = logging.getLogger('TradingFeesManager')
    
    def calculate_commission(self, 
                           shares: int, 
                           price_per_share: float, 
                           order_type: str = 'STOCK') -> Dict:
        """
        Calcule les commissions IBKR pour un ordre
        
        Args:
            shares: Nombre d'actions
            price_per_share: Prix par action
            order_type: Type d'ordre (STOCK, OPTION, etc.)
        
        Returns:
            Dict avec tous les frais détaillés
        """
        total_value = shares * price_per_share
        
        # Commission de base
        base_commission = shares * self.IBKR_FEES['us_stocks']['per_share']
        
        # Appliquer le minimum
        if base_commission < self.IBKR_FEES['us_stocks']['min_per_order']:
            commission = self.IBKR_FEES['us_stocks']['min_per_order']
        else:
            commission = base_commission
        
        # Appliquer le plafond (1% de la valeur) - MAIS RESPECTER LE MINIMUM
        max_commission = total_value * self.IBKR_FEES['us_stocks']['max_percentage']
        if commission > max_commission and max_commission >= self.IBKR_FEES['us_stocks']['min_per_order']:
            commission = max_commission
        
        # Frais réglementaires
        regulatory_fees = self._calculate_regulatory_fees(shares, price_per_share)
        
        # Frais de change (si applicable)
        fx_fees = self._calculate_fx_fees(total_value)
        
        total_fees = commission + regulatory_fees + fx_fees
        
        return {
            'order_value': total_value,
            'shares': shares,
            'price_per_share': price_per_share,
            'commission': round(commission, 2),
            'regulatory_fees': round(regulatory_fees, 2),
            'fx_fees': round(fx_fees, 2),
            'total_fees': round(total_fees, 2),
            'fees_percentage': round((total_fees / total_value) * 100, 3),
            'timestamp': datetime.now().isoformat()
        }
    
    def _calculate_regulatory_fees(self, shares: int, price_per_share: float) -> float:
        """Calcule les frais réglementaires"""
        # FINRA Trading Activity Fee (achats ET ventes)
        finra_fee = shares * price_per_share * self.IBKR_FEES['regulatory_fees']['finra']
        
        # SEC Fee (ventes uniquement - sera appliqué lors de la vente)
        sec_fee = 0.0  # Sera calculé lors de la vente
        
        return finra_fee
    
    def _calculate_fx_fees(self, total_value: float, from_currency: str = 'USD', to_currency: str = 'EUR') -> float:
        """Calcule les frais de change"""
        if from_currency == 'USD' and to_currency == 'EUR':
            return total_value * self.IBKR_FEES['fx_fees']['usd_eur']
        return 0.0
    
    def calculate_round_trip_fees(self, 
                                 shares: int, 
                                 buy_price: float, 
                                 sell_price: float) -> Dict:
        """
        Calcule les frais pour un aller-retour complet (achat + vente)
        """
        # Frais d'achat
        buy_fees = self.calculate_commission(shares, buy_price)
        
        # Frais de vente (incluant SEC fee)
        sell_fees = self.calculate_commission(shares, sell_price)
        sec_fee = shares * sell_price * self.IBKR_FEES['regulatory_fees']['sec']
        sell_fees['regulatory_fees'] += sec_fee
        sell_fees['total_fees'] += sec_fee
        
        # Total aller-retour
        total_round_trip = buy_fees['total_fees'] + sell_fees['total_fees']
        total_value = shares * (buy_price + sell_price)
        
        return {
            'buy_fees': buy_fees,
            'sell_fees': sell_fees,
            'total_round_trip_fees': round(total_round_trip, 2),
            'total_round_trip_percentage': round((total_round_trip / total_value) * 100, 3),
            'break_even_percentage': round((total_round_trip / (shares * buy_price)) * 100, 3)
        }
    
    def simulate_paper_trading_fees(self, 
                                   shares: int, 
                                   price_per_share: float, 
                                   is_paper: bool = True) -> Dict:
        """
        Simule les frais pour paper trading (même frais que le réel)
        """
        if is_paper:
            self.logger.info(f"📊 Simulation des frais paper trading: {shares} actions à ${price_per_share}")
        
        return self.calculate_commission(shares, price_per_share)
    
    def get_fee_summary(self) -> Dict:
        """Retourne un résumé des frais IBKR"""
        return {
            'commission_structure': self.IBKR_FEES['us_stocks'],
            'fx_structure': self.IBKR_FEES['fx_fees'],
            'regulatory_structure': self.IBKR_FEES['regulatory_fees'],
            'source': 'Interactive Brokers Official Pricing',
            'last_updated': datetime.now().isoformat()
        }

if __name__ == "__main__":
    print("🚀 Démarrage du gestionnaire de frais IBKR...")
    fees_manager = TradingFeesManager()
    print("Module de calcul des frais prêt") 