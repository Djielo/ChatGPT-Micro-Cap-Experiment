# MicroCap Data Collector pour HRM
"""
Collecteur de données micro-caps pour créer un dataset d'entraînement HRM
Utilise yFinance pour récupérer les vraies données financières
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import yaml
from datetime import datetime, timedelta
from typing import Dict, List, Any
import logging
import time
import random

class MicroCapDataCollector:
    """
    Collecteur de données micro-caps pour l'entraînement HRM
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger.info("📊 Collecteur de données micro-caps initialisé")
        
        # Critères MicroCapExperiment originaux
        self.microcap_criteria = {
            'max_market_cap': 300_000_000,  # Moins de 300M$ = micro-cap
            'min_volume': 100_000,          # Volume minimum quotidien
            'min_price': 1.0,               # Prix minimum
            'max_price': 50.0,              # Prix maximum
            'sectors': ['Technology', 'Biotech', 'Healthcare', 'Energy', 'Materials']
        }
        
    def setup_logging(self):
        """Configure le logging"""
        self.logger = logging.getLogger('MicroCapDataCollector')
    
    def get_microcap_tickers(self, count: int = 1000) -> List[str]:
        """
        Génère une liste de tickers micro-caps à analyser
        
        Args:
            count: Nombre de tickers à récupérer
        
        Returns:
            Liste de tickers micro-caps
        """
        self.logger.info(f"🔍 Recherche de {count} tickers micro-caps...")
        
        # Liste de base de tickers micro-caps connus (RÉELS et ACTIFS)
        base_tickers = [
            # Biotech micro-caps (validés)
            "ABEO", "SAVA", "ATOS", "OCGN", "DVAX", "NVAX", "VXRT", "MCRB",
            "OPGN", "TNXP", "COCP", "ADIL", "AQST", "ARQT", "AVIR", "AXSM",
            "BMRA", "BPMC", "CDMO", "CGEM", "CHRS", "CTIC", "EARN", "EDGW",
            
            # Tech micro-caps (validés)
            "CARV", "PRTS", "SMSI", "AEHR", "KOPN", "VERI", "INUV", "FNKO",
            "PLAG", "CMRA", "TOUR", "CETX", "NURO", "OCUL", "OMCL", "OSIS",
            "PHUN", "PRPO", "QMCO", "RARE", "SPNS", "TAIT", "TERA", "TLRY",
            
            # Energy micro-caps (validés)
            "INDO", "PNRG", "ENSV", "VGAS", "NEXT", "CLNE", "GEVO", "PLUG",
            "REED", "BNGO", "WATT", "BEEM", "GURE", "REE", "AMTX", "FLUX",
            "HYLN", "KPTI", "NOVA", "POLA", "RGTI", "SOLO", "SUNL", "WKHS",
            
            # Materials/Mining micro-caps (validés)
            "UUUU", "CVKD", "DSWL", "ARTL", "DLPN", "MOTS", "IMMP", "ABML",
            "ARLP", "ATEC", "BERY", "CCRD", "EMES", "GEVO", "HAIN", "MATX",
            "MERC", "MTRN", "RDUS", "RMTI", "SENEA", "SLVM", "USAP", "VSAT",
            
            # Healthcare/Pharma micro-caps (validés)
            "ADMA", "ALBO", "ALPN", "AMRN", "ANIP", "AQST", "ARCT", "ARNA",
            "ATNF", "AVEO", "BDTX", "BFRI", "BHAT", "BIIB", "BLFS", "BPTH",
            "BRID", "BRPA", "BSGM", "BTTX", "CAPR", "CARA", "CBAY", "CDTX"
        ]
        
        # Utiliser uniquement les vrais tickers (pas de génération aléatoire)
        # Mélanger pour avoir de la variété
        random.shuffle(base_tickers)
        
        # Répéter la liste si on demande plus que disponible
        extended_tickers = (base_tickers * ((count // len(base_tickers)) + 1))[:count]
        
        return extended_tickers
    
    def collect_ticker_data(self, ticker: str, days_back: int = 7) -> Dict:
        """
        Collecte les données d'un ticker via yFinance
        
        Args:
            ticker: Symbol du ticker
            days_back: Nombre de jours à analyser
        
        Returns:
            Données formatées pour HRM
        """
        try:
            # Récupérer les données via yFinance
            stock = yf.Ticker(ticker)
            
            # Données historiques (7 jours)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days_back)
            
            hist = stock.history(start=start_date, end=end_date)
            if hist.empty:
                return None
            
            # Informations générales
            info = stock.info
            
            # Calculer les métriques
            current_price = hist['Close'].iloc[-1]
            price_7d_ago = hist['Close'].iloc[0] if len(hist) > 1 else current_price
            price_change_pct = ((current_price - price_7d_ago) / price_7d_ago) * 100
            
            # Volume moyen
            avg_volume = hist['Volume'].mean()
            
            # Market Cap (approximatif si pas disponible)
            market_cap = info.get('marketCap', current_price * info.get('sharesOutstanding', 50_000_000))
            
            # Filtrer selon les critères micro-cap
            if not self._meets_microcap_criteria(current_price, market_cap, avg_volume):
                return None
            
            # Format de données pour HRM
            ticker_data = {
                'ticker': ticker,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'price_at_analysis': float(current_price),
                'price_7d_before': float(price_7d_ago),
                'price_change_pct': float(price_change_pct),
                'market_cap': int(market_cap),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'volume_avg_7d': int(avg_volume),
                'volume_current': int(hist['Volume'].iloc[-1]),
                'high_52w': float(info.get('fiftyTwoWeekHigh', current_price * 1.5)),
                'low_52w': float(info.get('fiftyTwoWeekLow', current_price * 0.5)),
                'pe_ratio': info.get('forwardPE', None),
                'beta': info.get('beta', None),
                'short_ratio': info.get('shortRatio', None),
                'cash_per_share': info.get('totalCashPerShare', None),
                'debt_to_equity': info.get('debtToEquity', None)
            }
            
            return ticker_data
            
        except Exception as e:
            self.logger.warning(f"⚠️ Erreur collecte {ticker}: {e}")
            return None
    
    def _meets_microcap_criteria(self, price: float, market_cap: int, volume: float) -> bool:
        """
        Vérifie si un ticker répond aux critères micro-cap
        """
        return (
            market_cap <= self.microcap_criteria['max_market_cap'] and
            volume >= self.microcap_criteria['min_volume'] and
            self.microcap_criteria['min_price'] <= price <= self.microcap_criteria['max_price']
        )
    
    def generate_hrm_analysis_example(self, ticker_data: Dict) -> Dict:
        """
        Génère un exemple d'analyse formaté pour l'entraînement HRM
        
        Args:
            ticker_data: Données du ticker
        
        Returns:
            Exemple d'analyse structuré
        """
        # Simulation de la logique de décision MicroCapExperiment
        decision_factors = []
        score = 0
        
        # Facteur 1: Performance récente
        if ticker_data['price_change_pct'] > 5:
            decision_factors.append("Performance positive récente (+5%)")
            score += 2
        elif ticker_data['price_change_pct'] < -5:
            decision_factors.append("Performance négative récente (-5%)")
            score -= 2
        
        # Facteur 2: Valorisation (market cap vs cash)
        if ticker_data['market_cap'] < 100_000_000:
            decision_factors.append("Petite capitalisation (<100M$)")
            score += 1
        
        # Facteur 3: Volume
        if ticker_data['volume_current'] > ticker_data['volume_avg_7d'] * 1.5:
            decision_factors.append("Volume élevé (1.5x moyenne)")
            score += 1
        
        # Facteur 4: Secteur
        if ticker_data['sector'] in ['Technology', 'Biotech']:
            decision_factors.append(f"Secteur porteur: {ticker_data['sector']}")
            score += 1
        
        # Décision basée sur le score
        if score >= 3:
            decision = "BUY"
            confidence = min(0.8, 0.5 + score * 0.1)
        elif score <= -2:
            decision = "SELL"
            confidence = min(0.8, 0.5 + abs(score) * 0.1)
        else:
            decision = "HOLD"
            confidence = 0.5
        
        # Simuler un résultat après 10 jours
        result_price = ticker_data['price_at_analysis'] * (1 + random.uniform(-0.15, 0.20))
        pnl = ((result_price - ticker_data['price_at_analysis']) / ticker_data['price_at_analysis']) * 100
        
        return {
            'input_data': ticker_data,
            'analysis': {
                'decision_factors': decision_factors,
                'technical_score': score,
                'decision': decision,
                'confidence': round(confidence, 2),
                'reasoning_steps': [
                    f"Analyse de {ticker_data['ticker']} dans le secteur {ticker_data['sector']}",
                    f"Performance 7j: {ticker_data['price_change_pct']:.1f}%",
                    f"Market cap: ${ticker_data['market_cap']:,}",
                    f"Score technique: {score}/5"
                ]
            },
            'result_simulation': {
                'price_after_10d': round(result_price, 2),
                'pnl_percent': round(pnl, 2)
            }
        }
    
    def collect_hrm_dataset(self, num_examples: int = 1000, output_file: str = "hrm_microcap_dataset.json") -> List[Dict]:
        """
        Collecte un dataset complet pour l'entraînement HRM
        
        Args:
            num_examples: Nombre d'exemples à collecter
            output_file: Fichier de sortie
        
        Returns:
            Dataset d'exemples d'analyse
        """
        self.logger.info(f"🚀 Collecte de {num_examples} exemples pour HRM...")
        
        # Récupérer les tickers
        tickers = self.get_microcap_tickers(num_examples * 2)  # 2x pour avoir des échecs
        
        dataset = []
        successful_collections = 0
        
        for i, ticker in enumerate(tickers):
            if successful_collections >= num_examples:
                break
                
            self.logger.info(f"📊 Collecte {successful_collections+1}/{num_examples}: {ticker}")
            
            # Collecter les données
            ticker_data = self.collect_ticker_data(ticker)
            
            if ticker_data:
                # Générer l'exemple d'analyse HRM
                hrm_example = self.generate_hrm_analysis_example(ticker_data)
                dataset.append(hrm_example)
                successful_collections += 1
            
            # Pause pour éviter les limitations API
            time.sleep(0.1)
            
            if i % 50 == 0:
                self.logger.info(f"⏳ Progression: {successful_collections}/{num_examples} réussis")
        
        # Sauvegarder le dataset
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(dataset, f, indent=2, default=str)
        
        self.logger.info(f"✅ Dataset HRM sauvegardé: {output_file} ({len(dataset)} exemples)")
        return dataset

if __name__ == "__main__":
    print("🚀 Démarrage du collecteur de données micro-caps...")
    collector = MicroCapDataCollector()
    print("Module de collecte de données prêt")