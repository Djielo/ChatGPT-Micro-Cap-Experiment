# Transition Manager - Gestionnaire de Transition DS → HRM
"""
Gestionnaire de la transition progressive entre DeepSeek et HRM
Jour 1: 90% DS / 10% HRM → Objectif: 0% DS / 100% HRM
"""

import json
import logging
from typing import Dict, List, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path

class TransitionManager:
    """
    Gestionnaire de la transition progressive DeepSeek → HRM
    """
    
    def __init__(self):
        self.setup_logging()
        self.logger.info("⚖️ Transition Manager initialisé")
        
        # Configuration initiale
        self.current_day = 1
        self.ds_percentage = 90  # Début: 90% DeepSeek
        self.hrm_percentage = 10  # Début: 10% HRM
        
        # Historique des performances
        self.performance_history = []
        
        # Paramètres d'ajustement
        self.adjustment_step = 10  # Palier standard 10%
        self.min_performance_threshold = 0.6  # Seuil minimum performance
        
    def setup_logging(self):
        """Configure le logging"""
        self.logger = logging.getLogger('TransitionManager')
    
    def get_current_allocation(self) -> Tuple[float, float]:
        """
        Retourne l'allocation actuelle DS/HRM
        
        Returns:
            Tuple (ds_percentage, hrm_percentage)
        """
        return (self.ds_percentage, self.hrm_percentage)
    
    def allocate_tickers_for_analysis(self, tickers: List[str]) -> Dict[str, List[str]]:
        """
        Répartit les tickers entre DeepSeek et HRM selon l'allocation actuelle
        
        Args:
            tickers: Liste des tickers à analyser
        
        Returns:
            Dict avec 'deepseek' et 'hrm' contenant leurs tickers respectifs
        """
        total_tickers = len(tickers)
        
        # Calculer le nombre de tickers pour chaque système
        hrm_count = int(total_tickers * (self.hrm_percentage / 100))
        ds_count = total_tickers - hrm_count
        
        # Mélanger pour éviter les biais
        import random
        shuffled_tickers = tickers.copy()
        random.shuffle(shuffled_tickers)
        
        allocation = {
            'deepseek': shuffled_tickers[:ds_count],
            'hrm': shuffled_tickers[ds_count:ds_count + hrm_count]
        }
        
        self.logger.info(f"📊 Allocation Jour {self.current_day}: DS={ds_count} ({self.ds_percentage}%), HRM={hrm_count} ({self.hrm_percentage}%)")
        
        return allocation
    
    def evaluate_daily_performance(self, 
                                  ds_results: List[Dict], 
                                  hrm_results: List[Dict]) -> Dict:
        """
        Évalue la performance quotidienne des deux systèmes
        
        Args:
            ds_results: Résultats DeepSeek
            hrm_results: Résultats HRM
        
        Returns:
            Métriques de performance comparatives
        """
        # Calculer les métriques pour DeepSeek
        ds_metrics = self._calculate_metrics(ds_results, 'deepseek')
        
        # Calculer les métriques pour HRM
        hrm_metrics = self._calculate_metrics(hrm_results, 'hrm')
        
        # Performance comparative
        performance_comparison = {
            'day': self.current_day,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'deepseek_metrics': ds_metrics,
            'hrm_metrics': hrm_metrics,
            'allocation': {
                'ds_percentage': self.ds_percentage,
                'hrm_percentage': self.hrm_percentage
            }
        }
        
        # Ajouter à l'historique
        self.performance_history.append(performance_comparison)
        
        self.logger.info(f"📈 Performance Jour {self.current_day}: DS={ds_metrics['avg_confidence']:.2f}, HRM={hrm_metrics['avg_confidence']:.2f}")
        
        return performance_comparison
    
    def _calculate_metrics(self, results: List[Dict], system_name: str) -> Dict:
        """
        Calcule les métriques pour un système donné
        """
        if not results:
            return {
                'avg_confidence': 0.0,
                'decision_distribution': {},
                'count': 0,
                'system': system_name
            }
        
        # Extraire les confidences
        confidences = []
        decisions = []
        
        for result in results:
            if system_name == 'deepseek':
                analysis = result.get('deepseek_analysis', {})
            else:  # hrm
                analysis = result.get('analysis', {}) or result.get('hierarchical_analysis', {})
            
            confidence = analysis.get('confidence', 0.5)
            decision = analysis.get('decision', 'HOLD')
            
            confidences.append(confidence)
            decisions.append(decision)
        
        # Calculer les métriques
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        decision_distribution = {decision: decisions.count(decision) for decision in set(decisions)}
        
        return {
            'avg_confidence': avg_confidence,
            'decision_distribution': decision_distribution,
            'count': len(results),
            'system': system_name
        }
    
    def adjust_allocation_based_on_performance(self) -> Dict[str, Any]:
        """
        Ajuste l'allocation basée sur les performances récentes
        
        Returns:
            Détails de l'ajustement effectué
        """
        if len(self.performance_history) < 2:
            return {'action': 'no_adjustment', 'reason': 'Données insuffisantes'}
        
        # Performance actuelle vs précédente
        current_perf = self.performance_history[-1]
        previous_perf = self.performance_history[-2]
        
        current_combined = self._calculate_combined_performance(current_perf)
        previous_combined = self._calculate_combined_performance(previous_perf)
        
        # Logique d'ajustement
        if current_combined > previous_combined:
            # Performance améliore → Continue la transition
            return self._increase_hrm_allocation()
        else:
            # Performance détériore → Ralentit la transition
            return self._decrease_hrm_allocation()
    
    def _calculate_combined_performance(self, perf_data: Dict) -> float:
        """
        Calcule la performance combinée pondérée
        """
        ds_conf = perf_data['deepseek_metrics']['avg_confidence']
        hrm_conf = perf_data['hrm_metrics']['avg_confidence']
        ds_weight = perf_data['allocation']['ds_percentage'] / 100
        hrm_weight = perf_data['allocation']['hrm_percentage'] / 100
        
        combined = (ds_conf * ds_weight) + (hrm_conf * hrm_weight)
        return combined
    
    def _increase_hrm_allocation(self) -> Dict[str, Any]:
        """
        Augmente l'allocation HRM (transition positive)
        """
        if self.hrm_percentage >= 100:
            return {
                'action': 'transition_complete',
                'reason': 'HRM atteint 100%',
                'new_allocation': (0, 100)
            }
        
        # Augmenter HRM de 10%
        new_hrm = min(100, self.hrm_percentage + self.adjustment_step)
        new_ds = 100 - new_hrm
        
        old_allocation = (self.ds_percentage, self.hrm_percentage)
        self.ds_percentage = new_ds
        self.hrm_percentage = new_hrm
        
        self.logger.info(f"📈 Transition positive: DS {old_allocation[0]}%→{new_ds}%, HRM {old_allocation[1]}%→{new_hrm}%")
        
        return {
            'action': 'increase_hrm',
            'reason': 'Performance améliorée',
            'old_allocation': old_allocation,
            'new_allocation': (new_ds, new_hrm)
        }
    
    def _decrease_hrm_allocation(self) -> Dict[str, Any]:
        """
        Diminue l'allocation HRM (ralentit la transition)
        """
        if self.hrm_percentage <= 10:
            return {
                'action': 'minimum_reached',
                'reason': 'HRM déjà au minimum 10%',
                'new_allocation': (self.ds_percentage, self.hrm_percentage)
            }
        
        # Diminuer HRM de 50% de l'ajustement (5% au lieu de 10%)
        reduction = self.adjustment_step // 2
        new_hrm = max(10, self.hrm_percentage - reduction)
        new_ds = 100 - new_hrm
        
        old_allocation = (self.ds_percentage, self.hrm_percentage)
        self.ds_percentage = new_ds
        self.hrm_percentage = new_hrm
        
        self.logger.warning(f"📉 Transition ralentie: DS {old_allocation[0]}%→{new_ds}%, HRM {old_allocation[1]}%→{new_hrm}%")
        
        return {
            'action': 'decrease_hrm',
            'reason': 'Performance détériorée',
            'old_allocation': old_allocation,
            'new_allocation': (new_ds, new_hrm)
        }
    
    def advance_day(self) -> int:
        """
        Avance au jour suivant
        
        Returns:
            Nouveau numéro de jour
        """
        self.current_day += 1
        self.logger.info(f"📅 Jour {self.current_day} - Allocation: DS={self.ds_percentage}%, HRM={self.hrm_percentage}%")
        return self.current_day
    
    def save_progress(self, filepath: str = "transition_progress.json"):
        """
        Sauvegarde le progrès de la transition
        """
        progress_data = {
            'current_day': self.current_day,
            'ds_percentage': self.ds_percentage,
            'hrm_percentage': self.hrm_percentage,
            'performance_history': self.performance_history,
            'last_updated': datetime.now().isoformat()
        }
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(progress_data, f, indent=2, default=str)
        
        self.logger.info(f"💾 Progrès sauvegardé: {filepath}")
    
    def load_progress(self, filepath: str = "transition_progress.json"):
        """
        Charge le progrès de la transition
        """
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            self.current_day = progress_data['current_day']
            self.ds_percentage = progress_data['ds_percentage']
            self.hrm_percentage = progress_data['hrm_percentage']
            self.performance_history = progress_data['performance_history']
            
            self.logger.info(f"📥 Progrès chargé: Jour {self.current_day}, DS={self.ds_percentage}%, HRM={self.hrm_percentage}%")
            
        except FileNotFoundError:
            self.logger.info("📋 Nouveau début de transition")
        except Exception as e:
            self.logger.error(f"❌ Erreur chargement progrès: {e}")
    
    def get_transition_summary(self) -> Dict:
        """
        Retourne un résumé de la transition
        """
        return {
            'current_day': self.current_day,
            'current_allocation': {
                'deepseek_percentage': self.ds_percentage,
                'hrm_percentage': self.hrm_percentage
            },
            'total_evaluations': len(self.performance_history),
            'transition_progress': f"{100 - self.ds_percentage}% vers HRM complet",
            'is_complete': self.hrm_percentage >= 100
        }

if __name__ == "__main__":
    print("🚀 Démarrage du gestionnaire de transition...")
    manager = TransitionManager()
    print("Module de gestion de transition prêt")