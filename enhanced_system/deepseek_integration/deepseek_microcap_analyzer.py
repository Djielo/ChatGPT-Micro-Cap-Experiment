# DeepSeek MicroCap Analyzer
"""
Analyseur micro-caps utilisant l'API DeepSeek pour générer le dataset HRM
Stratégie: DS analyse massivement → Dataset HRM → Transition progressive
"""

import asyncio
import aiohttp
import json
import logging
from typing import Dict, List, Any
from datetime import datetime
import yfinance as yf

# Configuration DeepSeek
DEEPSEEK_API_KEY = "sk-260c4a1a7bce4f17b504fa08cbb8127c"
DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"

class DeepSeekMicroCapAnalyzer:
    """
    Analyseur micro-caps utilisant DeepSeek
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger.info("🔍 DeepSeek MicroCap Analyzer initialisé")
        
        # Statistiques d'utilisation
        self.api_calls_made = 0
        self.tokens_used = 0
        self.total_cost = 0.0
        
    def setup_logging(self):
        """Configure le logging"""
        self.logger = logging.getLogger('DeepSeekMicroCapAnalyzer')
    
    async def analyze_microcap_with_deepseek(self, ticker_data: Dict) -> Dict:
        """
        Analyse une micro-cap avec DeepSeek
        
        Args:
            ticker_data: Données du ticker (yFinance)
        
        Returns:
            Analyse complète DeepSeek
        """
        try:
            # Créer le prompt structuré
            prompt = self.create_analysis_prompt(ticker_data)
            
            # Appel API DeepSeek
            async with aiohttp.ClientSession() as session:
                ds_response = await self.make_deepseek_call(session, prompt)
            
            # Parser la réponse
            analysis = self.parse_deepseek_response(ds_response, ticker_data)
            
            self.logger.info(f"✅ Analyse DS terminée pour {ticker_data.get('ticker', 'UNKNOWN')}")
            return analysis
            
        except Exception as e:
            self.logger.error(f"❌ Erreur analyse DS: {e}")
            return self.create_fallback_analysis(ticker_data)
    
    def create_analysis_prompt(self, ticker_data: Dict) -> str:
        """
        Crée le prompt optimisé pour DeepSeek selon la méthodologie MicroCapExperiment
        """
        ticker = ticker_data.get('ticker', 'UNKNOWN')
        
        prompt = f"""Tu es un analyste financier expert en micro-caps, spécialisé dans l'identification d'opportunités à fort potentiel.

MISSION : Analyse la micro-cap {ticker} et donne une recommandation d'investissement.

DONNÉES FINANCIÈRES :
- Ticker: {ticker}
- Prix actuel: ${ticker_data.get('price_at_analysis', 0):.2f}
- Variation 7j: {ticker_data.get('price_change_pct', 0):.1f}%
- Market Cap: ${ticker_data.get('market_cap', 0):,}
- Secteur: {ticker_data.get('sector', 'Unknown')}
- Volume moyen 7j: {ticker_data.get('volume_avg_7d', 0):,}
- Volume actuel: {ticker_data.get('volume_current', 0):,}
- PE Ratio: {ticker_data.get('pe_ratio', 'N/A')}
- Beta: {ticker_data.get('beta', 'N/A')}
- Short Ratio: {ticker_data.get('short_ratio', 'N/A')}
- Cash/Share: ${ticker_data.get('cash_per_share', 0):.2f}

CRITÈRES D'ANALYSE (style MicroCapExperiment) :
1. CATALYSEURS : Y a-t-il des événements identifiables (FDA, earnings, contrats) dans les 6 mois ?
2. VALORISATION : La société est-elle sous-évaluée vs sa trésorerie/pipeline ?
3. MOMENTUM : Volume, performance récente, potentiel squeeze ?
4. RISQUE/RENDEMENT : Potentiel asymétrique (2x-10x) vs risques ?

RÉPONSE REQUISE (format JSON) :
{{
    "decision": "BUY|SELL|HOLD",
    "confidence": 0.0-1.0,
    "target_price_6m": 0.00,
    "catalyseurs": ["liste des catalyseurs identifiés"],
    "thesis": "Thèse d'investissement en 2-3 phrases",
    "risk_factors": ["principaux risques"],
    "conviction_level": "haute|modérée|spéculative",
    "reasoning_steps": [
        "Étape 1 de raisonnement",
        "Étape 2 de raisonnement", 
        "Étape 3 de raisonnement"
    ]
}}

Analyse maintenant {ticker} selon ces critères."""

        return prompt
    
    async def make_deepseek_call(self, session: aiohttp.ClientSession, prompt: str) -> Dict:
        """
        Appel API DeepSeek réel
        """
        try:
            headers = {
                'Authorization': f'Bearer {DEEPSEEK_API_KEY}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': 'deepseek-reasoner',  # Modèle de raisonnement
                'messages': [
                    {
                        'role': 'user',
                        'content': prompt
                    }
                ],
                'max_tokens': 1500,
                'temperature': 0.3,  # Plus déterministe pour l'analyse financière
                'response_format': {'type': 'json_object'}
            }
            
            async with session.post(f"{DEEPSEEK_BASE_URL}/chat/completions", 
                                  json=payload, headers=headers) as response:
                if response.status == 200:
                    result = await response.json()
                    
                    # Statistiques
                    self.api_calls_made += 1
                    tokens = result.get('usage', {}).get('total_tokens', 0)
                    self.tokens_used += tokens
                    self.total_cost += self.calculate_cost(tokens)
                    
                    return {
                        'content': result['choices'][0]['message']['content'],
                        'status': 'success',
                        'tokens': tokens
                    }
                else:
                    error_text = await response.text()
                    self.logger.error(f"Erreur API DeepSeek: {response.status} - {error_text}")
                    return {
                        'content': None,
                        'status': 'error',
                        'error': error_text
                    }
                    
        except Exception as e:
            self.logger.error(f"Erreur connexion DeepSeek: {e}")
            return {
                'content': None,
                'status': 'error',
                'error': str(e)
            }
    
    def calculate_cost(self, tokens: int) -> float:
        """
        Calcule le coût approximatif (tarif heures normales)
        """
        # Estimation pour deepseek-reasoner
        input_cost = 0.55 / 1000000  # USD par token input
        output_cost = 2.19 / 1000000  # USD par token output
        
        # Approximation 60% input, 40% output
        estimated_cost = (tokens * 0.6 * input_cost) + (tokens * 0.4 * output_cost)
        return estimated_cost
    
    def parse_deepseek_response(self, ds_response: Dict, ticker_data: Dict) -> Dict:
        """
        Parse la réponse DeepSeek et structure pour HRM
        """
        if ds_response.get('status') != 'success' or not ds_response.get('content'):
            return self.create_fallback_analysis(ticker_data)
        
        try:
            # Parser le JSON retourné par DeepSeek
            analysis = json.loads(ds_response['content'])
            
            # Structurer pour le dataset HRM
            structured_analysis = {
                'input_data': ticker_data,
                'deepseek_analysis': {
                    'decision': analysis.get('decision', 'HOLD'),
                    'confidence': float(analysis.get('confidence', 0.5)),
                    'target_price_6m': float(analysis.get('target_price_6m', 0)),
                    'catalyseurs': analysis.get('catalyseurs', []),
                    'thesis': analysis.get('thesis', ''),
                    'risk_factors': analysis.get('risk_factors', []),
                    'conviction_level': analysis.get('conviction_level', 'modérée'),
                    'reasoning_steps': analysis.get('reasoning_steps', [])
                },
                'api_stats': {
                    'tokens_used': ds_response.get('tokens', 0),
                    'timestamp': datetime.now().isoformat()
                }
            }
            
            return structured_analysis
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Erreur parsing JSON DeepSeek: {e}")
            return self.create_fallback_analysis(ticker_data)
    
    def create_fallback_analysis(self, ticker_data: Dict) -> Dict:
        """
        Analyse de fallback si DeepSeek échoue
        """
        return {
            'input_data': ticker_data,
            'deepseek_analysis': {
                'decision': 'HOLD',
                'confidence': 0.5,
                'target_price_6m': ticker_data.get('price_at_analysis', 0),
                'catalyseurs': ['Analyse automatique indisponible'],
                'thesis': 'Analyse technique de base seulement',
                'risk_factors': ['API DeepSeek temporairement indisponible'],
                'conviction_level': 'modérée',
                'reasoning_steps': ['Fallback: données techniques uniquement']
            },
            'api_stats': {
                'tokens_used': 0,
                'timestamp': datetime.now().isoformat(),
                'status': 'fallback'
            }
        }
    
    async def mass_analyze_microcaps(self, tickers: List[str], target_count: int = 1000) -> List[Dict]:
        """
        Analyse massive de micro-caps pour créer le dataset HRM
        
        Args:
            tickers: Liste de tickers à analyser
            target_count: Nombre cible d'analyses
        
        Returns:
            Dataset complet pour HRM
        """
        self.logger.info(f"🚀 Début analyse massive: {target_count} tickers cibles")
        
        dataset = []
        successful_analyses = 0
        
        for i, ticker in enumerate(tickers):
            if successful_analyses >= target_count:
                break
            
            self.logger.info(f"📊 Analyse DS {successful_analyses+1}/{target_count}: {ticker}")
            
            try:
                # Récupérer les données yFinance
                ticker_data = await self.get_ticker_data(ticker)
                
                if ticker_data:
                    # Analyse DeepSeek
                    analysis = await self.analyze_microcap_with_deepseek(ticker_data)
                    dataset.append(analysis)
                    successful_analyses += 1
                
                # Pause pour respecter les rate limits
                await asyncio.sleep(0.5)
                
                # Log de progression
                if i % 50 == 0:
                    cost_info = f"${self.total_cost:.4f} ({self.tokens_used:,} tokens)"
                    self.logger.info(f"⏳ Progression: {successful_analyses}/{target_count} - Coût: {cost_info}")
                
            except Exception as e:
                self.logger.error(f"Erreur analyse {ticker}: {e}")
                continue
        
        # Statistiques finales
        final_cost = f"${self.total_cost:.4f}"
        self.logger.info(f"✅ Analyse massive terminée: {len(dataset)} analyses - Coût total: {final_cost}")
        
        return dataset
    
    async def get_ticker_data(self, ticker: str) -> Dict:
        """
        Récupère les données d'un ticker via yFinance (asynchrone)
        """
        try:
            # Exécuter yFinance dans un thread séparé
            loop = asyncio.get_event_loop()
            ticker_data = await loop.run_in_executor(None, self._fetch_ticker_sync, ticker)
            return ticker_data
        except Exception as e:
            self.logger.error(f"Erreur yFinance {ticker}: {e}")
            return None
    
    def _fetch_ticker_sync(self, ticker: str) -> Dict:
        """
        Récupération synchrone des données ticker (pour thread executor)
        """
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            hist = stock.history(period="7d")
            
            if hist.empty:
                return None
            
            current_price = hist['Close'].iloc[-1]
            price_7d_ago = hist['Close'].iloc[0] if len(hist) > 1 else current_price
            price_change_pct = ((current_price - price_7d_ago) / price_7d_ago) * 100
            
            return {
                'ticker': ticker,
                'date': datetime.now().strftime('%Y-%m-%d'),
                'price_at_analysis': float(current_price),
                'price_7d_before': float(price_7d_ago),
                'price_change_pct': float(price_change_pct),
                'market_cap': info.get('marketCap', 0),
                'sector': info.get('sector', 'Unknown'),
                'industry': info.get('industry', 'Unknown'),
                'volume_avg_7d': int(hist['Volume'].mean()),
                'volume_current': int(hist['Volume'].iloc[-1]),
                'pe_ratio': info.get('forwardPE', None),
                'beta': info.get('beta', None),
                'short_ratio': info.get('shortRatio', None),
                'cash_per_share': info.get('totalCashPerShare', None),
                'debt_to_equity': info.get('debtToEquity', None)
            }
            
        except Exception as e:
            raise e
    
    def get_analysis_stats(self) -> Dict:
        """
        Retourne les statistiques d'utilisation
        """
        return {
            'api_calls_made': self.api_calls_made,
            'tokens_used': self.tokens_used,
            'total_cost_usd': round(self.total_cost, 4),
            'avg_tokens_per_call': round(self.tokens_used / max(self.api_calls_made, 1), 0),
            'avg_cost_per_call': round(self.total_cost / max(self.api_calls_made, 1), 4)
        }

# Test de l'analyseur DeepSeek
async def test_deepseek_analyzer():
    """Test de l'analyseur DeepSeek"""
    analyzer = DeepSeekMicroCapAnalyzer()
    
    # Test avec quelques tickers
    test_tickers = ["ABEO", "SAVA", "GEVO"]
    
    dataset = await analyzer.mass_analyze_microcaps(test_tickers, target_count=3)
    
    print(f"📊 Dataset créé: {len(dataset)} analyses")
    print(f"💰 Statistiques: {analyzer.get_analysis_stats()}")
    
    if dataset:
        print("🧪 Exemple d'analyse:")
        print(json.dumps(dataset[0], indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(test_deepseek_analyzer())