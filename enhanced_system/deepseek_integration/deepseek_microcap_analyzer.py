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
import os
from .config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, REQUEST_TIMEOUT, RATE_LIMIT_DELAY, MAX_RETRIES

class DeepSeekMicroCapAnalyzer:
    """
    Analyseur micro-caps utilisant DeepSeek
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger.info("🔍 DeepSeek MicroCap Analyzer initialisé")
        if not DEEPSEEK_API_KEY:
            raise RuntimeError("DEEPSEEK_API_KEY manquante. Définissez-la dans vos variables d'environnement.")
        
        # Statistiques d'utilisation
        self.api_calls_made = 0
        self.tokens_used = 0
        self.total_cost = 0.0
        
    def setup_logging(self):
        """Configure le logging"""
        self.logger = logging.getLogger('DeepSeekMicroCapAnalyzer')
    
    def _calculate_min_confidence_for_market_cap(self, market_cap: float) -> float:
        """
        Calcule la confidence minimum requise selon la market cap
        Échelle glissante : Plus petite MC = Plus haute confidence requise
        avec une variation de 5% de confiance quelque soit la market cap
        
        50-120M MC  => 80-77% confidence
        121-190M MC => 76-73% confidence  
        191-260M MC => 72-69% confidence
        261-300M MC => 68-65% confidence
        
        Args:
            market_cap: Market cap en USD
        
        Returns:
            Confidence minimum requise (0.0-1.0)
        """
        # Convertir en millions pour faciliter les calculs
        mc_millions = market_cap / 1_000_000
        
        # Interpolation linéaire continue sur toute la plage 50M-300M
        # 50M => 80%, 300M => 65% (pente continue)
        if 50 <= mc_millions <= 300:
            # Calcul linéaire simple : y = mx + b
            # 50M => 0.80, 300M => 0.65
            # Pente = (0.65 - 0.80) / (300 - 50) = -0.15 / 250 = -0.0006
            slope = (0.65 - 0.80) / (300 - 50)
            min_confidence = 0.80 + slope * (mc_millions - 50)
        else:
            # Hors range, retourner une valeur par défaut élevée
            min_confidence = 0.85  # Très restrictif pour hors range
        
        return round(min_confidence, 3)
    
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
        Crée le prompt optimisé pour DeepSeek avec le framework super-prompt
        """
        ticker = ticker_data.get('ticker', 'UNKNOWN')
        
        prompt = f"""RÔLE
Tu es un expert en analyse financière micro-caps avec 15+ ans d'expérience en investissement spéculatif.
Tu disposes des compétences suivantes :
- Analyse fondamentale approfondie (bilans, cashflow, catalyseurs)
- Détection de signaux techniques précoces (volume, momentum, sentiment)
- Évaluation des risques asymétriques et potentiels de croissance explosive
- Connaissance sectorielle spécialisée (biotech, tech, énergie, mining)
- Identification de catalyseurs temporels (FDA, earnings, contrats, M&A)

Le contexte d'investissement est celui de micro-caps OPTIMALES (50M$ avec 80% de confiance minimum - 300M$ avec 65% de confiance mini) avec recherche d'opportunités 
asymétriques à haute conviction (65%-80% confidence). Nous ciblons des entreprises avec suffisamment de liquidité 
pour éviter les penny stocks, mais assez petites pour capturer la volatilité profitable. Style d'analyse inspiré du projet "MicroCapExperiment" 
qui a généré +40% de performance en identifiant des catalyseurs précoces et des valorisations décotées.

CRITÈRES DE SÉLECTION STRICTS :
- Market Cap: OBLIGATOIREMENT entre 50M$ et 300M$
- Confidence: UNIQUEMENT entre 0.65 et 0.80 (high conviction trades)
- Liquidité: Volume quotidien > 100,000 actions
- Éviter: Penny stocks (<$1), sociétés en faillite, OTC markets

TÂCHES
Je souhaite une analyse complète et une recommandation d'investissement pour la micro-cap {ticker}, 
en déterminant si elle présente une opportunité d'achat, de vente, ou de position neutre, 
avec un niveau de conviction justifié et un prix cible 15 jours.

FORMAT DE RÉPONSE ATTENDU
Structure JSON stricte avec :
- decision: Action claire (BUY/SELL/HOLD)
- confidence: Score numérique 0.0-1.0 basé sur la solidité des arguments
- target_price_15j: Prix objectif réaliste dans 15 jours
- catalyseurs: Liste concrète d'événements identifiables dans les 15 jours
- thesis: Thèse d'investissement synthétique en 2-3 phrases percutantes
- risk_factors: Risques spécifiques et quantifiables
- conviction_level: Niveau de conviction (haute/modérée/spéculative)
- reasoning_steps: Processus de raisonnement étape par étape

POINTS DE VIGILANCE
Assure-toi de justifier ta réponse en te basant sur des métriques financières concrètes.
Ta réponse ne doit surtout pas :
- Donner des recommandations génériques sans analyse spécifique au ticker
- Ignorer les risques ou présenter uniquement les aspects positifs
- Proposer des prix cibles irréalistes non justifiés par les fondamentaux
- Omettre l'analyse de la situation de trésorerie et du runway financier
- Négliger l'analyse sectorielle et concurrentielle spécifique

CONTEXTE
Données financières actuelles pour {ticker} :
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

EXEMPLES
Exemple de catalyseurs forts : "FDA approval Phase 2 attendue Q1 2025", "Earnings Q4 avec guidance positive", "Contrat gouvernemental $50M en négociation"
Exemple de thesis BUY : "{ticker} bénéficie d'un pipeline robuste en oncologie avec 3 candidats en Phase 2, valorisation décotée à 2x P/E vs peers à 8x, catalyseur FDA imminent."
Exemple de risk_factors : "Dilution potentielle si levée de fonds nécessaire", "Concurrence accrue dans le segment", "Dépendance à un client unique"

Analyse maintenant {ticker} selon ce framework rigoureux."""

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
                'model': 'deepseek-chat',  # Chat model plus stable pour JSON
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
            
            # Validation des critères stricts
            confidence = float(analysis.get('confidence', 0.5))
            market_cap = ticker_data.get('market_cap', 0)
            price = ticker_data.get('price_at_analysis', 0)
            volume = ticker_data.get('volume_current', 0)
            
            # Calcul de la confidence minimum requise selon la market cap
            min_confidence_required = self._calculate_min_confidence_for_market_cap(market_cap)
            
            # Calcul de la plage acceptable (±5% de flexibilité)
            min_confidence_flexible = max(0.60, min_confidence_required - 0.05)  # Min absolu 60%
            max_confidence_flexible = 1.0  # Pas de limite haute (85-90% = excellent!)
            
            # Vérifications de qualité avec échelle glissante et flexibilité
            quality_check = {
                'market_cap_valid': 50_000_000 <= market_cap <= 300_000_000,
                'confidence_valid': min_confidence_flexible <= confidence <= max_confidence_flexible,
                'confidence_required_base': min_confidence_required,
                'confidence_required_flexible': min_confidence_flexible,
                'confidence_actual': confidence,
                'confidence_margin': abs(confidence - min_confidence_required),
                'price_valid': price >= 1.0,  # Éviter penny stocks
                'volume_valid': volume >= 100_000,  # Liquidité suffisante
                'meets_criteria': False
            }
            
            # Marquer comme valide seulement si TOUS les critères sont respectés
            quality_check['meets_criteria'] = all([
                quality_check['market_cap_valid'],
                quality_check['confidence_valid'],
                quality_check['price_valid'],
                quality_check['volume_valid']
            ])
            
            # Structurer pour le dataset HRM
            structured_analysis = {
                'input_data': ticker_data,
                'deepseek_analysis': {
                    'decision': analysis.get('decision', 'HOLD'),
                    'confidence': confidence,
                    'target_price_15j': float(analysis.get('target_price_15j', 0)),
                    'catalyseurs': analysis.get('catalyseurs', []),
                    'thesis': analysis.get('thesis', ''),
                    'risk_factors': analysis.get('risk_factors', []),
                    'conviction_level': analysis.get('conviction_level', 'modérée'),
                    'reasoning_steps': analysis.get('reasoning_steps', [])
                },
                'quality_check': quality_check,
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
                'target_price_15j': ticker_data.get('price_at_analysis', 0),
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
        high_quality_analyses = 0
        total_attempts = 0
        rejected_analyses = {
            'market_cap': 0,
            'confidence': 0,
            'price': 0,
            'volume': 0,
            'other': 0
        }
        
        for i, ticker in enumerate(tickers):
            if high_quality_analyses >= target_count:
                break
            
            total_attempts += 1
            self.logger.info(f"📊 Analyse DS {total_attempts}: {ticker} (Acceptées: {high_quality_analyses}/{target_count})")
            
            try:
                # Récupérer les données yFinance
                ticker_data = await self.get_ticker_data(ticker)
                
                if ticker_data:
                    # Pré-filtrage des données de base
                    market_cap = ticker_data.get('market_cap', 0)
                    price = ticker_data.get('price_at_analysis', 0)
                    volume = ticker_data.get('volume_current', 0)
                    
                    # Vérification rapide AVANT l'analyse coûteuse
                    if not (50_000_000 <= market_cap <= 300_000_000):
                        rejected_analyses['market_cap'] += 1
                        self.logger.warning(f"⚠️ {ticker} rejeté: Market cap ${market_cap:,} hors range 50M-300M")
                        continue
                    
                    if price < 1.0:
                        rejected_analyses['price'] += 1
                        self.logger.warning(f"⚠️ {ticker} rejeté: Penny stock ${price:.2f}")
                        continue
                    
                    if volume < 100_000:
                        rejected_analyses['volume'] += 1
                        self.logger.warning(f"⚠️ {ticker} rejeté: Volume faible {volume:,}")
                        continue
                    
                    # Analyse DeepSeek (coûteuse, donc après pré-filtrage)
                    analysis = await self.analyze_microcap_with_deepseek(ticker_data)
                    
                    # Vérification finale de la qualité
                    quality_check = analysis.get('quality_check', {})
                    if quality_check.get('meets_criteria', False):
                        dataset.append(analysis)
                        high_quality_analyses += 1
                        confidence = analysis['deepseek_analysis']['confidence']
                        min_base = quality_check.get('confidence_required_base', 0.65)
                        margin = quality_check.get('confidence_margin', 0)
                        
                        if confidence >= min_base:
                            self.logger.info(f"✅ {ticker} accepté: Confidence {confidence:.2f} >= {min_base:.2f} (parfait!)")
                        else:
                            self.logger.info(f"✅ {ticker} accepté: Confidence {confidence:.2f} (marge ±5%, base {min_base:.2f})")
                    else:
                        # Analyser pourquoi rejeté
                        if not quality_check.get('confidence_valid', True):
                            rejected_analyses['confidence'] += 1
                            confidence = analysis['deepseek_analysis']['confidence']
                            min_flexible = quality_check.get('confidence_required_flexible', 0.60)
                            self.logger.warning(f"⚠️ {ticker} rejeté: Confidence {confidence:.2f} < {min_flexible:.2f} (min avec marge)")
                        else:
                            rejected_analyses['other'] += 1
                            self.logger.warning(f"⚠️ {ticker} rejeté: Autres critères")
                
                # Pause pour respecter les rate limits
                await asyncio.sleep(0.5)
                
                # Log de progression
                if i % 50 == 0:
                    cost_info = f"${self.total_cost:.4f} ({self.tokens_used:,} tokens)"
                    self.logger.info(f"⏳ Progression: {successful_analyses}/{target_count} - Coût: {cost_info}")
                
            except Exception as e:
                self.logger.error(f"Erreur analyse {ticker}: {e}")
                continue
        
        # Statistiques finales détaillées
        final_cost = f"${self.total_cost:.4f}"
        acceptance_rate = (high_quality_analyses / max(total_attempts, 1)) * 100
        
        self.logger.info(f"✅ Analyse massive terminée!")
        self.logger.info(f"📊 RÉSULTATS: {high_quality_analyses} analyses HIGH-QUALITY acceptées")
        self.logger.info(f"💰 Coût total: {final_cost}")
        self.logger.info(f"📈 Taux d'acceptation: {acceptance_rate:.1f}% ({high_quality_analyses}/{total_attempts})")
        
        self.logger.info(f"❌ REJETS par critère:")
        self.logger.info(f"  Market Cap (50M-300M): {rejected_analyses['market_cap']}")
        self.logger.info(f"  Confidence (65-80%): {rejected_analyses['confidence']}")
        self.logger.info(f"  Prix (>$1): {rejected_analyses['price']}")
        self.logger.info(f"  Volume (>100k): {rejected_analyses['volume']}")
        self.logger.info(f"  Autres: {rejected_analyses['other']}")
        
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

if __name__ == "__main__":
    print("🚀 Démarrage de l'analyseur DeepSeek pour micro-caps...")
    analyzer = DeepSeekMicroCapAnalyzer()
    print("Module d'analyse DeepSeek prêt")