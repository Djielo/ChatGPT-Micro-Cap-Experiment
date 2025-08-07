# HRM Financial Trainer
"""
Entraîneur HRM pour l'analyse financière de micro-caps
Utilise le dataset collecté pour entraîner le modèle HRM
"""

import json
import torch
import numpy as np
from typing import Dict, List, Any
import logging
from pathlib import Path

class HRMFinancialTrainer:
    """
    Entraîneur HRM pour l'analyse financière
    """
    
    def __init__(self, dataset_path: str = "hrm_real_dataset_50.json"):
        self.setup_logging()
        self.logger.info("🎓 HRM Financial Trainer initialisé")
        
        self.dataset_path = dataset_path
        self.dataset = None
        self.model = None
        
        # Configuration HRM pour les finances
        self.financial_config = {
            'input_features': [
                'price_at_analysis', 'price_change_pct', 'market_cap',
                'volume_avg_7d', 'pe_ratio', 'beta', 'short_ratio',
                'cash_per_share', 'debt_to_equity'
            ],
            'output_classes': ['BUY', 'SELL', 'HOLD'],
            'max_sequence_length': 32,
            'hidden_size': 512
        }
        
    def setup_logging(self):
        """Configure le logging"""
        self.logger = logging.getLogger('HRMFinancialTrainer')
    
    def load_dataset(self) -> bool:
        """
        Charge le dataset d'entraînement
        
        Returns:
            True si succès, False sinon
        """
        try:
            self.logger.info(f"📥 Chargement du dataset: {self.dataset_path}")
            
            with open(self.dataset_path, 'r', encoding='utf-8') as f:
                self.dataset = json.load(f)
            
            self.logger.info(f"✅ Dataset chargé: {len(self.dataset)} exemples")
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Erreur chargement dataset: {e}")
            return False
    
    def preprocess_example(self, example: Dict) -> Dict:
        """
        Préprocesse un exemple pour l'entraînement HRM
        
        Args:
            example: Exemple du dataset
        
        Returns:
            Exemple préprocessé pour HRM
        """
        input_data = example['input_data']
        analysis = example['analysis']
        
        # Extraire les features numériques
        features = []
        for feature in self.financial_config['input_features']:
            value = input_data.get(feature, 0.0)
            if value is None:
                value = 0.0
            features.append(float(value))
        
        # Normaliser les features
        normalized_features = self.normalize_features(features)
        
        # Créer le contexte textuel (reasoning steps)
        reasoning_context = " ".join(analysis.get('reasoning_steps', []))
        
        # Mapper la décision à un index
        decision = analysis.get('decision', 'HOLD')
        decision_index = self.financial_config['output_classes'].index(decision)
        
        # Formatter pour HRM
        hrm_input = {
            'features': normalized_features,
            'context': reasoning_context,
            'target_decision': decision_index,
            'confidence': analysis.get('confidence', 0.5),
            'ticker': input_data.get('ticker', 'UNKNOWN')
        }
        
        return hrm_input
    
    def normalize_features(self, features: List[float]) -> List[float]:
        """
        Normalise les features financières
        
        Args:
            features: Features brutes
        
        Returns:
            Features normalisées
        """
        # Normalisations spécifiques aux features financières
        normalized = []
        
        for i, value in enumerate(features):
            if i == 0:  # price_at_analysis
                normalized.append(np.log10(max(value, 0.01)) / 2.0)  # Log scale prix
            elif i == 1:  # price_change_pct
                normalized.append(value / 100.0)  # Pourcentage normalisé
            elif i == 2:  # market_cap
                normalized.append(np.log10(max(value, 1000000)) / 12.0)  # Log scale market cap
            elif i == 3:  # volume_avg_7d
                normalized.append(np.log10(max(value, 1000)) / 10.0)  # Log scale volume
            else:  # Autres ratios
                normalized.append(np.tanh(value / 10.0))  # Tanh pour limiter
        
        return normalized
    
    def create_training_tensors(self) -> Dict[str, torch.Tensor]:
        """
        Crée les tensors d'entraînement pour HRM
        
        Returns:
            Tensors formatés pour HRM
        """
        if not self.dataset:
            raise ValueError("Dataset non chargé")
        
        # Préprocesser tous les exemples
        processed_examples = []
        for example in self.dataset:
            processed = self.preprocess_example(example)
            processed_examples.append(processed)
        
        # Créer les tensors
        features_list = [ex['features'] for ex in processed_examples]
        decisions_list = [ex['target_decision'] for ex in processed_examples]
        confidences_list = [ex['confidence'] for ex in processed_examples]
        
        # Convertir en tensors PyTorch
        features_tensor = torch.tensor(features_list, dtype=torch.float32)
        decisions_tensor = torch.tensor(decisions_list, dtype=torch.long)
        confidences_tensor = torch.tensor(confidences_list, dtype=torch.float32)
        
        self.logger.info(f"📊 Tensors créés: Features {features_tensor.shape}, Décisions {decisions_tensor.shape}")
        
        return {
            'features': features_tensor,
            'decisions': decisions_tensor,
            'confidences': confidences_tensor,
            'examples': processed_examples
        }
    
    def prepare_hrm_format(self) -> Dict:
        """
        Prépare le dataset au format HRM
        
        Returns:
            Dataset formaté pour l'entraînement HRM
        """
        self.logger.info("🔄 Préparation du format HRM...")
        
        if not self.load_dataset():
            return None
        
        # Créer les tensors d'entraînement
        training_data = self.create_training_tensors()
        
        # Format HRM avec structure hiérarchique
        hrm_dataset = {
            'name': 'microcap_financial_analysis',
            'description': 'Dataset d\'analyse financière micro-caps pour HRM',
            'version': '1.0',
            'num_examples': len(self.dataset),
            'input_dim': len(self.financial_config['input_features']),
            'output_classes': len(self.financial_config['output_classes']),
            'data': {
                'input_features': training_data['features'],
                'target_decisions': training_data['decisions'],
                'confidence_scores': training_data['confidences'],
                'raw_examples': training_data['examples']
            },
            'config': self.financial_config
        }
        
        # Sauvegarder le dataset formaté
        output_path = "hrm_financial_training_dataset.pt"
        torch.save(hrm_dataset, output_path)
        
        self.logger.info(f"✅ Dataset HRM sauvegardé: {output_path}")
        
        return hrm_dataset
    
    def analyze_dataset_statistics(self) -> Dict:
        """
        Analyse les statistiques du dataset
        
        Returns:
            Statistiques du dataset
        """
        if not self.dataset:
            self.load_dataset()
        
        # Analyser les décisions
        decisions = [ex['analysis']['decision'] for ex in self.dataset]
        decision_counts = {decision: decisions.count(decision) for decision in set(decisions)}
        
        # Analyser les secteurs
        sectors = [ex['input_data']['sector'] for ex in self.dataset]
        sector_counts = {sector: sectors.count(sector) for sector in set(sectors)}
        
        # Analyser les performances
        performances = [ex['input_data']['price_change_pct'] for ex in self.dataset]
        avg_performance = np.mean(performances)
        
        stats = {
            'total_examples': len(self.dataset),
            'decision_distribution': decision_counts,
            'sector_distribution': sector_counts,
            'average_performance_7d': round(avg_performance, 2),
            'performance_range': [round(min(performances), 2), round(max(performances), 2)]
        }
        
        self.logger.info(f"📈 Statistiques dataset: {stats}")
        return stats

if __name__ == "__main__":
    print("🚀 Démarrage du trainer HRM financier...")
    trainer = HRMFinancialTrainer()
    print("Module d'entraînement HRM financier prêt")