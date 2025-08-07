# Enhanced Trading System V2 - Système Intégré DS → HRM
"""
Système de trading amélioré avec transition progressive DeepSeek → HRM
Phase 1: DS pour dataset (1000+ tickers)
Phase 2: Entraînement HRM
Phase 3: Transition progressive 90/10 → 0/100
"""

import asyncio
import logging
import json
from datetime import datetime
from typing import Dict, List, Any
import sys
import os

# Ajouter les chemins des modules
sys.path.append('deepseek_integration')
sys.path.append('hrm_ai')
sys.path.append('core_orchestrator')
sys.path.append('ibkr_trading')

# Imports des modules
from deepseek_microcap_analyzer import DeepSeekMicroCapAnalyzer
from hrm_financial_trainer import HRMFinancialTrainer
from transition_manager import TransitionManager
from financial_hrm_integration import FinancialHRMIntegrator

class EnhancedTradingSystemV2:
    """
    Système de trading amélioré avec transition DeepSeek → HRM
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger.info("🚀 Enhanced Trading System V2 initialisé")
        
        # Initialiser les composants
        self.deepseek_analyzer = DeepSeekMicroCapAnalyzer()
        self.hrm_trainer = HRMFinancialTrainer("hrm_ai/hrm_real_dataset_50.json")
        self.hrm_integrator = FinancialHRMIntegrator()
        self.transition_manager = TransitionManager()
        
        # État du système
        self.phase = "dataset_creation"  # dataset_creation, training, transition
        self.dataset_target = 1000
        self.current_dataset_size = 0
        
    def setup_logging(self):
        """Configure le logging global"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('enhanced_system_v2.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('EnhancedTradingSystemV2')
    
    async def run_phase_1_dataset_creation(self, target_size: int = 1000) -> bool:
        """
        PHASE 1: Création du dataset avec DeepSeek
        
        Args:
            target_size: Nombre d'analyses cibles
        
        Returns:
            True si succès
        """
        self.logger.info(f"📊 PHASE 1: Création dataset - Objectif: {target_size} analyses")
        
        try:
            # Liste de tickers micro-caps (à étendre selon besoin)
            from microcap_data_collector import MicroCapDataCollector
            collector = MicroCapDataCollector()
            tickers = collector.get_microcap_tickers(target_size * 2)  # 2x pour les échecs
            
            # Analyse massive avec DeepSeek
            dataset = await self.deepseek_analyzer.mass_analyze_microcaps(
                tickers, target_count=target_size
            )
            
            # Sauvegarder le dataset
            dataset_file = f"deepseek_dataset_{len(dataset)}.json"
            with open(dataset_file, 'w', encoding='utf-8') as f:
                json.dump(dataset, f, indent=2, default=str)
            
            self.current_dataset_size = len(dataset)
            
            # Statistiques
            stats = self.deepseek_analyzer.get_analysis_stats()
            self.logger.info(f"✅ PHASE 1 terminée: {len(dataset)} analyses - Coût: ${stats['total_cost_usd']}")
            
            return len(dataset) >= target_size * 0.8  # 80% du target = succès
            
        except Exception as e:
            self.logger.error(f"❌ Erreur PHASE 1: {e}")
            return False
    
    def run_phase_2_hrm_training(self, dataset_file: str = None) -> bool:
        """
        PHASE 2: Entraînement HRM avec le dataset DeepSeek
        
        Args:
            dataset_file: Fichier dataset à utiliser
        
        Returns:
            True si succès
        """
        self.logger.info("🧠 PHASE 2: Entraînement HRM")
        
        try:
            # Charger le dataset DeepSeek
            if dataset_file is None:
                # Chercher le dernier dataset créé
                import glob
                dataset_files = glob.glob("deepseek_dataset_*.json")
                if not dataset_files:
                    self.logger.error("❌ Aucun dataset DeepSeek trouvé")
                    return False
                dataset_file = max(dataset_files)  # Le plus récent
            
            self.logger.info(f"📥 Chargement dataset: {dataset_file}")
            
            # Adapter le dataset DeepSeek pour HRM
            hrm_dataset = self._convert_deepseek_to_hrm_format(dataset_file)
            
            # Préparer l'entraînement HRM
            self.hrm_trainer.dataset = hrm_dataset
            hrm_training_data = self.hrm_trainer.prepare_hrm_format()
            
            if hrm_training_data:
                self.logger.info(f"✅ PHASE 2 terminée: {hrm_training_data['num_examples']} exemples prêts")
                return True
            else:
                return False
                
        except Exception as e:
            self.logger.error(f"❌ Erreur PHASE 2: {e}")
            return False
    
    def _convert_deepseek_to_hrm_format(self, dataset_file: str) -> List[Dict]:
        """
        Convertit le dataset DeepSeek au format HRM
        """
        with open(dataset_file, 'r', encoding='utf-8') as f:
            deepseek_dataset = json.load(f)
        
        hrm_dataset = []
        
        for ds_example in deepseek_dataset:
            # Convertir format DeepSeek → Format HRM
            input_data = ds_example['input_data']
            ds_analysis = ds_example['deepseek_analysis']
            
            hrm_example = {
                'input_data': input_data,
                'analysis': {
                    'decision': ds_analysis['decision'],
                    'confidence': ds_analysis['confidence'],
                    'reasoning_steps': ds_analysis['reasoning_steps'],
                    'decision_factors': ds_analysis.get('catalyseurs', []),
                    'technical_score': self._convert_confidence_to_score(ds_analysis['confidence'])
                },
                'result_simulation': {
                    'price_after_10d': ds_analysis['target_price_6m'],
                    'pnl_percent': 0.0  # À calculer selon target vs prix actuel
                }
            }
            
            hrm_dataset.append(hrm_example)
        
        return hrm_dataset
    
    def _convert_confidence_to_score(self, confidence: float) -> int:
        """
        Convertit la confidence DeepSeek en score technique HRM
        """
        if confidence >= 0.8:
            return 4
        elif confidence >= 0.6:
            return 2
        elif confidence >= 0.4:
            return 0
        else:
            return -2
    
    async def run_phase_3_transition(self, tickers: List[str]) -> Dict:
        """
        PHASE 3: Transition progressive DeepSeek → HRM
        
        Args:
            tickers: Liste de tickers à analyser quotidiennement
        
        Returns:
            Résultats de l'analyse quotidienne
        """
        self.logger.info(f"⚖️ PHASE 3: Transition - Jour {self.transition_manager.current_day}")
        
        try:
            # Charger le progrès de la transition
            self.transition_manager.load_progress()
            
            # Allouer les tickers entre DS et HRM
            allocation = self.transition_manager.allocate_tickers_for_analysis(tickers)
            
            # Analyse DeepSeek
            ds_results = []
            if allocation['deepseek']:
                self.logger.info(f"🔍 Analyse DeepSeek: {len(allocation['deepseek'])} tickers")
                for ticker in allocation['deepseek']:
                    ticker_data = await self.deepseek_analyzer.get_ticker_data(ticker)
                    if ticker_data:
                        analysis = await self.deepseek_analyzer.analyze_microcap_with_deepseek(ticker_data)
                        ds_results.append(analysis)
            
            # Analyse HRM
            hrm_results = []
            if allocation['hrm']:
                self.logger.info(f"🧠 Analyse HRM: {len(allocation['hrm'])} tickers")
                for ticker in allocation['hrm']:
                    ticker_data = await self.deepseek_analyzer.get_ticker_data(ticker)
                    if ticker_data:
                        analysis = self.hrm_integrator.analyze_microcap_hierarchical(ticker_data)
                        hrm_results.append(analysis)
            
            # Évaluer la performance
            performance = self.transition_manager.evaluate_daily_performance(ds_results, hrm_results)
            
            # Ajuster l'allocation pour demain
            adjustment = self.transition_manager.adjust_allocation_based_on_performance()
            
            # Avancer au jour suivant
            self.transition_manager.advance_day()
            
            # Sauvegarder le progrès
            self.transition_manager.save_progress()
            
            results = {
                'day': performance['day'],
                'allocation_used': allocation,
                'deepseek_results': ds_results,
                'hrm_results': hrm_results,
                'performance': performance,
                'adjustment': adjustment
            }
            
            self.logger.info(f"✅ PHASE 3 Jour {performance['day']} terminé - Ajustement: {adjustment['action']}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ Erreur PHASE 3: {e}")
            return {}
    
    async def run_full_pipeline(self, 
                               dataset_size: int = 100,  # Réduit pour test
                               daily_tickers: List[str] = None) -> Dict:
        """
        Lance le pipeline complet
        
        Args:
            dataset_size: Taille du dataset à créer
            daily_tickers: Tickers pour analyse quotidienne
        
        Returns:
            Résultats du pipeline
        """
        self.logger.info("🚀 LANCEMENT PIPELINE COMPLET")
        
        results = {
            'phase_1_success': False,
            'phase_2_success': False,
            'phase_3_results': {}
        }
        
        # PHASE 1: Dataset Creation
        self.logger.info("=" * 60)
        self.logger.info("🔄 PHASE 1: CRÉATION DATASET DEEPSEEK")
        self.logger.info("=" * 60)
        
        phase_1_success = await self.run_phase_1_dataset_creation(dataset_size)
        results['phase_1_success'] = phase_1_success
        
        if not phase_1_success:
            self.logger.error("❌ PHASE 1 échouée - Arrêt du pipeline")
            return results
        
        # PHASE 2: HRM Training
        self.logger.info("=" * 60)
        self.logger.info("🔄 PHASE 2: ENTRAÎNEMENT HRM")
        self.logger.info("=" * 60)
        
        phase_2_success = self.run_phase_2_hrm_training()
        results['phase_2_success'] = phase_2_success
        
        if not phase_2_success:
            self.logger.error("❌ PHASE 2 échouée - Arrêt du pipeline")
            return results
        
        # PHASE 3: Transition (simulation d'une journée)
        self.logger.info("=" * 60)
        self.logger.info("🔄 PHASE 3: TRANSITION DEEPSEEK → HRM")
        self.logger.info("=" * 60)
        
        if daily_tickers is None:
            daily_tickers = ["ABEO", "SAVA", "GEVO", "VERI", "ATOS"]  # Test
        
        phase_3_results = await self.run_phase_3_transition(daily_tickers)
        results['phase_3_results'] = phase_3_results
        
        self.logger.info("🎉 PIPELINE COMPLET TERMINÉ AVEC SUCCÈS !")
        
        return results

if __name__ == "__main__":
    print("🚀 Démarrage du système de trading amélioré V2...")
    system = EnhancedTradingSystemV2()
    asyncio.run(system.run_full_pipeline())