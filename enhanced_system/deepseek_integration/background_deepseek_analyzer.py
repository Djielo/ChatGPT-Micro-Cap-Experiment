import pandas as pd
import asyncio
import json
import logging
from datetime import datetime
from deepseek_microcap_analyzer import DeepSeekMicroCapAnalyzer

# === CONFIGURATION ===
CSV_PATH = "enhanced_system/data/micro_caps_extended.csv"
OUTPUT_PATH = "enhanced_system/data/deepseek_analysis_results.json"
LOG_PATH = "enhanced_system/logs/deepseek_background.log"

# === SETUP LOGGING ===
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
console = logging.StreamHandler()
console.setFormatter(logging.Formatter("[%(asctime)s] %(message)s", datefmt="%H:%M:%S"))
logging.getLogger().addHandler(console)

class BackgroundDeepSeekAnalyzer:
    def __init__(self):
        self.analyzer = DeepSeekMicroCapAnalyzer()
        self.results = []
        self.progress = 0
        
    async def analyze_all_microcaps(self):
        """Analyse toutes les micro-caps avec DeepSeek"""
        logging.info("🚀 Démarrage de l'analyse DeepSeek en arrière-plan")
        
        # Charger les données
        df = pd.read_csv(CSV_PATH)
        total_tickers = len(df)
        logging.info(f"📊 {total_tickers} micro-caps à analyser")
        
        # Filtrer les micro-caps prometteuses (Market Cap 50M-300M)
        promising_caps = df[
            (df["Market Cap"] >= 50_000_000) & 
            (df["Market Cap"] <= 300_000_000) &
            (df["Volume"] > 1000)  # Volume minimum
        ]
        
        logging.info(f"🎯 {len(promising_caps)} micro-caps prometteuses identifiées")
        
        # Analyser par batch pour éviter la surcharge
        batch_size = 10
        for i in range(0, len(promising_caps), batch_size):
            batch = promising_caps.iloc[i:i+batch_size]
            tickers = batch["Ticker"].tolist()
            
            logging.info(f"📦 Analyse du batch {i//batch_size + 1}/{(len(promising_caps)-1)//batch_size + 1}")
            logging.info(f"🔍 Tickers: {tickers}")
            
            try:
                # Analyser le batch
                batch_results = await self.analyzer.mass_analyze_microcaps(
                    tickers, 
                    target_count=len(tickers)
                )
                
                # Ajouter les résultats
                for result in batch_results:
                    result["analysis_timestamp"] = datetime.now().isoformat()
                    self.results.append(result)
                
                # Sauvegarder progressivement
                self.save_progress()
                
                logging.info(f"✅ Batch {i//batch_size + 1} terminé: {len(batch_results)} analyses")
                
                # Pause entre batches
                await asyncio.sleep(5)
                
            except Exception as e:
                logging.error(f"❌ Erreur batch {i//batch_size + 1}: {e}")
                continue
        
        # Sauvegarde finale
        self.save_final_results()
        logging.info(f"🎉 Analyse terminée: {len(self.results)} micro-caps analysées")
        
    def save_progress(self):
        """Sauvegarde progressive des résultats"""
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(self.results, f, indent=2, ensure_ascii=False, default=str)
        logging.info(f"💾 Progression sauvegardée: {len(self.results)} analyses")
    
    def save_final_results(self):
        """Sauvegarde finale avec métadonnées"""
        final_data = {
            "metadata": {
                "total_analyses": len(self.results),
                "analysis_date": datetime.now().isoformat(),
                "source_csv": CSV_PATH,
                "analyzer_version": "DeepSeek MicroCap Analyzer v1.0"
            },
            "results": self.results
        }
        
        with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, indent=2, ensure_ascii=False, default=str)
        
        logging.info(f"💾 Résultats finaux sauvegardés: {OUTPUT_PATH}")
        
        # Statistiques
        if self.results:
            confidences = [r.get("deepseek_analysis", {}).get("confidence", 0) for r in self.results]
            decisions = [r.get("deepseek_analysis", {}).get("decision", "UNKNOWN") for r in self.results]
            
            logging.info(f"📊 Statistiques:")
            logging.info(f"  - Confiance moyenne: {sum(confidences)/len(confidences):.2f}")
            logging.info(f"  - Décisions BUY: {decisions.count('BUY')}")
            logging.info(f"  - Décisions HOLD: {decisions.count('HOLD')}")
            logging.info(f"  - Décisions SELL: {decisions.count('SELL')}")

async def main():
    """Fonction principale"""
    analyzer = BackgroundDeepSeekAnalyzer()
    await analyzer.analyze_all_microcaps()

if __name__ == "__main__":
    asyncio.run(main())
