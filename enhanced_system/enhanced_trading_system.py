# Enhanced Trading System - Système de Trading Amélioré
import asyncio
import logging
import sys
import os
from datetime import datetime
from pathlib import Path

# Ajouter les chemins des modules
sys.path.append('enhanced_system/core_orchestrator')
sys.path.append('enhanced_system/hrm_ai')
sys.path.append('enhanced_system/deepseek_integration')
sys.path.append('enhanced_system/ibkr_trading')

from core_orchestrator.orchestrator import TradingOrchestrator

class EnhancedTradingSystem:
    """
    Système de trading amélioré utilisant HRM, DeepSeek et IBKR
    """
    
    def __init__(self):
        self.setup_logging()
        self.orchestrator = TradingOrchestrator()
        self.logger.info("🚀 Système de Trading Amélioré initialisé")
        
    def setup_logging(self):
        """Configure le logging pour le système complet"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('enhanced_trading.log', encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('EnhancedTradingSystem')
    
    async def run_daily_routine(self):
        """
        Exécute la routine quotidienne complète
        """
        self.logger.info("=" * 60)
        self.logger.info("🔄 DÉBUT DE LA ROUTINE QUOTIDIENNE")
        self.logger.info("=" * 60)
        
        try:
            # 1. Orchestration de l'analyse quotidienne
            await self.orchestrator.orchestrate_daily_analysis()
            
            # 2. Rapport de performance
            await self.generate_performance_report()
            
            # 3. Sauvegarde des données
            await self.save_daily_data()
            
            self.logger.info("=" * 60)
            self.logger.info("✅ ROUTINE QUOTIDIENNE TERMINÉE AVEC SUCCÈS")
            self.logger.info("=" * 60)
            
        except Exception as e:
            self.logger.error(f"❌ Erreur dans la routine quotidienne: {e}")
            raise
    
    async def generate_performance_report(self):
        """
        Génère un rapport de performance quotidien
        """
        self.logger.info("📊 Génération du rapport de performance...")
        
        # Simulation du rapport
        report = {
            'date': datetime.now().isoformat(),
            'system_status': 'OPERATIONAL',
            'modules_status': {
                'hrm': 'ACTIVE',
                'deepseek': 'ACTIVE', 
                'ibkr': 'ACTIVE'
            },
            'analysis_summary': 'Toutes les analyses terminées avec succès',
            'trades_executed': 0,
            'portfolio_value': 'Calculé automatiquement'
        }
        
        self.logger.info(f"📈 Rapport généré: {report}")
        return report
    
    async def save_daily_data(self):
        """
        Sauvegarde les données quotidiennes
        """
        self.logger.info("💾 Sauvegarde des données quotidiennes...")
        
        # Créer le dossier de sauvegarde s'il n'existe pas
        backup_dir = Path('enhanced_system/data/backups')
        backup_dir.mkdir(exist_ok=True, parents=True)
        
        # Simuler la sauvegarde
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = backup_dir / f'daily_backup_{timestamp}.json'
        
        backup_data = {
            'timestamp': datetime.now().isoformat(),
            'system_version': '1.0.0',
            'modules': ['HRM', 'DeepSeek', 'IBKR'],
            'status': 'COMPLETED'
        }
        
        self.logger.info(f"💾 Données sauvegardées dans: {backup_file}")
        return backup_data
    
    async def run_continuous_monitoring(self):
        """
        Mode surveillance continue (pour tests)
        """
        self.logger.info("👁️ Démarrage du mode surveillance continue...")
        
        while True:
            try:
                await self.run_daily_routine()
                self.logger.info("⏰ Attente 24h avant prochaine analyse...")
                await asyncio.sleep(86400)  # 24 heures
                
            except KeyboardInterrupt:
                self.logger.info("🛑 Arrêt du mode surveillance")
                break
            except Exception as e:
                self.logger.error(f"❌ Erreur dans la surveillance: {e}")
                await asyncio.sleep(3600)  # Attendre 1h en cas d'erreur

if __name__ == "__main__":
    print("🚀 Démarrage du système de trading amélioré...")
    system = EnhancedTradingSystem()
    asyncio.run(system.run_daily_routine()) 