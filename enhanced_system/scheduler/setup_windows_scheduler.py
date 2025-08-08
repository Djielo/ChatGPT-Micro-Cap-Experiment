#!/usr/bin/env python3
"""
Script de configuration du Windows Task Scheduler pour le pipeline MicroCaps.
Configure les tâches programmées avec les offsets définis dans WORKFLOW_DS.md.

Créneaux configurés:
- Étape 0 (fetch_all_microcaps_fmp.py): 5x/jour
- Étape 1 (extended_to_potential.py): 5x/jour, +2min
- Étape 2 (DS_potential_to_pepite.py): 3x/jour, +4min  
- Étape 3 (DS_pepite_to_sharpratio.py): 3x/jour, +6min

Usage: python setup_windows_scheduler.py
"""

import subprocess
import os
import sys
from datetime import datetime, timedelta

def run_schtasks_command(cmd):
    """Exécute une commande schtasks et affiche le résultat."""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {cmd}")
            if result.stdout.strip():
                print(f"   {result.stdout.strip()}")
        else:
            print(f"❌ {cmd}")
            print(f"   Erreur: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Erreur lors de l'exécution: {e}")
        return False

def create_task(task_name, script_path, schedule, start_time, interval_minutes=0):
    """Crée une tâche Windows avec schtasks."""
    
    # Chemin absolu du script
    abs_script_path = os.path.abspath(script_path)
    if not os.path.exists(abs_script_path):
        print(f"⚠️  Script non trouvé: {abs_script_path}")
        return False
    
    # Répertoire de travail
    work_dir = os.path.dirname(os.path.abspath("."))
    
    # Commande Python
    python_cmd = f'python "{abs_script_path}"'
    
    # Configuration de la tâche
    cmd = f'schtasks /create /tn "{task_name}" /tr "{python_cmd}" /sc {schedule}'
    
    if schedule == "daily":
        cmd += f' /st {start_time}'
    elif schedule == "minute":
        cmd += f' /mo {interval_minutes}'
    
    cmd += f' /sd {datetime.now().strftime("%d/%m/%Y")}'
    cmd += f' /f'  # Force la création/remplacement
    
    return run_schtasks_command(cmd)

def main():
    print("🚀 Configuration du Windows Task Scheduler pour le pipeline MicroCaps")
    print("=" * 70)
    
    # Vérification des droits administrateur
    try:
        result = subprocess.run("schtasks /query", shell=True, capture_output=True)
        if result.returncode != 0:
            print("❌ Erreur: Ce script nécessite des droits administrateur.")
            print("   Veuillez exécuter en tant qu'administrateur.")
            return False
    except:
        print("❌ Erreur: Impossible d'accéder à schtasks.")
        return False
    
    # Configuration des tâches
    tasks = [
        {
            "name": "MicroCaps_Etape0_Fetch",
            "script": "enhanced_system/deepseek_integration/fetch_all_microcaps_fmp.py",
            "schedule": "daily",
            "times": ["09:00", "14:30", "18:00", "22:00", "01:00"],
            "description": "Collecte des données microcaps (5x/jour)"
        },
        {
            "name": "MicroCaps_Etape1_Filter", 
            "script": "enhanced_system/deepseek_integration/extended_to_potential.py",
            "schedule": "daily",
            "times": ["09:02", "14:32", "18:02", "22:02", "01:02"],
            "description": "Filtrage et scoring (5x/jour, +2min)"
        },
        {
            "name": "MicroCaps_Etape2_DeepSeek",
            "script": "enhanced_system/deepseek_integration/DS_potential_to_pepite.py", 
            "schedule": "daily",
            "times": ["14:34", "18:04", "22:04"],
            "description": "Analyse DeepSeek (3x/jour, +4min)"
        },
        {
            "name": "MicroCaps_Etape3_SharpRatio",
            "script": "enhanced_system/deepseek_integration/DS_pepite_to_sharpratio.py",
            "schedule": "daily", 
            "times": ["14:36", "18:06", "22:06"],
            "description": "Calcul Sharpe Ratio (3x/jour, +6min)"
        }
    ]
    
    success_count = 0
    total_count = 0
    
    for task in tasks:
        print(f"\n📋 {task['description']}")
        print(f"   Script: {task['script']}")
        
        for time in task['times']:
            task_name = f"{task['name']}_{time.replace(':', '')}"
            total_count += 1
            
            if create_task(task_name, task['script'], "daily", time):
                success_count += 1
                print(f"   ✅ Tâche créée: {task_name} à {time}")
            else:
                print(f"   ❌ Échec création: {task_name}")
    
    print(f"\n📊 Résumé: {success_count}/{total_count} tâches créées avec succès")
    
    if success_count == total_count:
        print("🎉 Configuration terminée avec succès!")
        print("\n📝 Prochaines étapes:")
        print("1. Vérifiez les tâches dans 'Gestionnaire des tâches Windows'")
        print("2. Testez manuellement chaque script avant la première exécution")
        print("3. Surveillez les logs dans enhanced_system/logs/")
        print("4. Vérifiez les fichiers CSV/JSON générés")
    else:
        print("⚠️  Certaines tâches n'ont pas pu être créées.")
        print("   Vérifiez les droits administrateur et les chemins des scripts.")
    
    return success_count == total_count

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
