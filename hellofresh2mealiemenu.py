#!/usr/bin/env python3
"""
Script pour créer automatiquement un meal plan dans Mealie
à partir des recettes de la semaine HelloFresh

Version Playwright - Full headless, compatible cron
"""

import requests
import json
import random
import yaml
import os
import sys
import argparse
from datetime import datetime, timedelta
from difflib import SequenceMatcher
import time
from playwright.sync_api import sync_playwright

# =============================================================================
# CONFIGURATION
# =============================================================================

# Charger la config depuis config.yaml (dans le même dossier que le script)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.yaml")

try:
    with open(CONFIG_PATH, 'r') as f:
        config = yaml.safe_load(f)

    # Mode debug
    DEBUG_MODE = config.get('debug_mode', False)

    # HelloFresh
    HELLOFRESH_MAGIC_LINK = config.get('hellofresh_magic_link')
    SUBSCRIPTION_ID = config['hellofresh_subscription_id']

    # Mealie
    MEALIE_URL = config['mealie_url']
    MEALIE_TOKEN = config['mealie_token']

    # Planning
    ENTRY_TYPE = config.get('entry_type', 'dinner')
    MATCHING_THRESHOLD = config.get('matching_threshold', 0.6)
    DAYS_TO_PLAN = config.get('days_to_plan', ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday"])
    
except FileNotFoundError:
    print(f"❌ Fichier {CONFIG_PATH} introuvable")
    print(f"   Copie default-config.yaml vers config.yaml et remplis tes identifiants")
    exit(1)
except KeyError as e:
    print(f"❌ Clé manquante dans config.yaml: {e}")
    exit(1)

# =============================================================================
# FONCTIONS UTILITAIRES
# =============================================================================

def log(message, level="info"):
    """Afficher un message seulement en mode debug"""
    if DEBUG_MODE or level in ["error", "always"]:
        print(message)

# =============================================================================
# FONCTIONS HELLOFRESH
# =============================================================================

def get_current_week_recipes_with_magic_link(magic_link, sub_id, week_offset=0):
    """
    Récupérer les recettes de la commande HelloFresh
    en utilisant un lien magique (magic link) reçu par email

    Args:
        magic_link: URL du magic link HelloFresh
        sub_id: ID de souscription
        week_offset: Décalage en semaines (0=semaine actuelle, 1=semaine prochaine, -1=semaine dernière)
    """
    log("🔐 Connexion à HelloFresh via magic link...", "always")

    with sync_playwright() as p:
        # Lancer le navigateur (headless sauf si DEBUG)
        browser = p.chromium.launch(headless=not DEBUG_MODE)
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        page = context.new_page()

        try:
            # Aller directement sur le lien magique
            log("   Navigation vers le lien magique...")
            page.goto(magic_link, wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

            # Screenshot 1: Après clic sur magic link
            screenshot_path = os.path.join(SCRIPT_DIR, "debug_step1_after_magic_link.png")
            page.screenshot(path=screenshot_path, full_page=True)
            log(f"   Screenshot 1 sauvegardé: {screenshot_path}", "always")
            log(f"   URL après magic link: {page.url}", "always")

            # Le lien magique devrait nous authentifier et rediriger vers le menu
            log("   Authentification en cours...")

            # Attendre d'être sur la page du compte
            try:
                page.wait_for_url("**/my-account/**", timeout=15000)
                log("   ✅ Authentification réussie")

                # Screenshot 2: Après authentification
                screenshot_path = os.path.join(SCRIPT_DIR, "debug_step2_after_auth.png")
                page.screenshot(path=screenshot_path, full_page=True)
                log(f"   Screenshot 2 sauvegardé: {screenshot_path}", "always")
            except:
                # Vérifier si on est déjà sur la bonne page
                if '/my-account/' not in page.url:
                    log("   ⚠️  Redirection inattendue, tentative de navigation vers le menu...", "always")
                    screenshot_path = os.path.join(SCRIPT_DIR, "debug_step2_redirect_issue.png")
                    page.screenshot(path=screenshot_path, full_page=True)
                    log(f"   Screenshot 2 (erreur) sauvegardé: {screenshot_path}", "always")

            # Calculer la semaine cible (actuelle + offset)
            target_date = datetime.now() + timedelta(weeks=week_offset)
            year = target_date.isocalendar()[0]
            week_num = target_date.isocalendar()[1]
            week = f"{year}-W{week_num:02d}"

            week_label = "actuelle" if week_offset == 0 else f"{'prochaine' if week_offset == 1 else f'+{week_offset}'}" if week_offset > 0 else f"{week_offset}"
            log(f"📋 Récupération des recettes semaine {week_label} ({week})...", "always")

            # Aller sur le menu
            menu_url = f"https://www.hellofresh.fr/my-account/deliveries/menu?week={week}&subscriptionId={sub_id}&locale=fr-FR"
            log(f"   Navigation vers: {menu_url}", "always")
            page.goto(menu_url, wait_until="domcontentloaded", timeout=60000)
            time.sleep(3)

            # Screenshot 3: Page du menu
            screenshot_path = os.path.join(SCRIPT_DIR, "debug_step3_menu_page.png")
            page.screenshot(path=screenshot_path, full_page=True)
            log(f"   Screenshot 3 sauvegardé: {screenshot_path}", "always")
            log(f"   URL actuelle: {page.url}", "always")

            # Extraire les titres des recettes
            titles = []
            weekly_menu_section = page.query_selector("#weekly-menu")

            if not weekly_menu_section:
                log("❌ Section #weekly-menu non trouvée", "error")
                # Prendre un screenshot pour debug
                screenshot_path = os.path.join(SCRIPT_DIR, "hellofresh_debug.png")
                page.screenshot(path=screenshot_path, full_page=True)
                log(f"   Screenshot sauvegardé: {screenshot_path}", "error")
                log(f"   URL actuelle: {page.url}", "error")
                return []

            recipe_cards = weekly_menu_section.query_selector_all("[data-recipe-id]")
            log(f"   Trouvé {len(recipe_cards)} recettes")

            for card in recipe_cards:
                try:
                    # Ignorer les recettes offertes
                    is_free = card.query_selector("span:has-text('Offert')")
                    if is_free:
                        continue

                    # Récupérer le titre principal
                    title_elem = card.query_selector("[data-test-id='product-name']")
                    if not title_elem:
                        continue

                    title = title_elem.inner_text().strip()

                    # Récupérer le sous-titre
                    subtitle_elem = card.query_selector("[data-test-id='product-headline-screen-reader-text']")
                    if subtitle_elem:
                        subtitle = subtitle_elem.inner_text().strip()
                        full_title = f"{title} {subtitle}"
                    else:
                        full_title = title

                    if full_title:
                        titles.append(full_title)
                except:
                    continue

            log(f"✅ {len(titles)} recettes trouvées\n")

            return titles

        except Exception as e:
            log(f"❌ Erreur: {e}", "error")
            try:
                screenshot_path = os.path.join(SCRIPT_DIR, "hellofresh_error.png")
                page.screenshot(path=screenshot_path)
                log(f"   Screenshot sauvegardé: {screenshot_path}", "error")
            except:
                pass
            return []
        finally:
            browser.close()


# =============================================================================
# FONCTIONS MEALIE
# =============================================================================

def get_all_mealie_recipes():
    """
    Récupérer toutes les recettes de Mealie
    """
    log("📚 Chargement des recettes Mealie...")
    
    url = f"{MEALIE_URL}/api/recipes"
    headers = {'Authorization': f'Bearer {MEALIE_TOKEN}'}
    
    try:
        all_recipes = {}
        page = 1
        per_page = 100
        
        while True:
            params = {'page': page, 'perPage': per_page}
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'items' in data:
                recipes = data['items']
                
                for recipe in recipes:
                    all_recipes[recipe['name'].lower()] = recipe['id']
                
                if len(recipes) < per_page:
                    break
                
                page += 1
            else:
                break
        
        log(f"✅ {len(all_recipes)} recettes dans Mealie\n")
        return all_recipes
        
    except Exception as e:
        log(f"❌ Erreur Mealie: {e}", "error")
        return {}

def delete_week_mealplans(start_date, end_date):
    """
    Supprimer tous les meal plans d'une semaine dans Mealie
    """
    log(f"🗑️  Suppression des meal plans ({start_date.strftime('%d/%m')} - {end_date.strftime('%d/%m')})...")
    
    url = f"{MEALIE_URL}/api/households/mealplans"
    headers = {'Authorization': f'Bearer {MEALIE_TOKEN}'}
    
    params = {
        'start_date': start_date.strftime('%Y-%m-%d'),
        'end_date': end_date.strftime('%Y-%m-%d'),
        'perPage': 100
    }
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        
        meal_plans = response.json()
        
        if isinstance(meal_plans, dict) and 'items' in meal_plans:
            meal_plans = meal_plans['items']
        
        if isinstance(meal_plans, list) and len(meal_plans) > 0:
            deleted_count = 0
            for plan in meal_plans:
                plan_id = plan.get('id')
                if plan_id:
                    delete_url = f"{MEALIE_URL}/api/households/mealplans/{plan_id}"
                    del_response = requests.delete(delete_url, headers=headers, timeout=30)
                    if del_response.status_code in [200, 204]:
                        log(f"   ✅ Supprimé: {plan.get('date', 'unknown')}")
                        deleted_count += 1
            
            log(f"   ✅ {deleted_count} meal plans supprimés\n")
        else:
            log("   ℹ️  Aucun meal plan à supprimer\n")
    
    except Exception as e:
        log(f"   ⚠️  Erreur suppression: {str(e)}\n")

def similarity(a, b):
    """Calculer la similarité entre deux chaînes"""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def match_recipe(hf_title, mealie_recipes):
    """
    Trouver la recette Mealie correspondante
    """
    best_match = None
    best_score = 0
    
    for mealie_title, mealie_id in mealie_recipes.items():
        score = similarity(hf_title, mealie_title)
        
        if score > best_score:
            best_score = score
            best_match = (mealie_title, mealie_id, score)
    
    if best_match and best_match[2] >= MATCHING_THRESHOLD:
        return best_match
    
    return best_match if best_match else None

def create_meal_plan(recipe_ids, start_date):
    """
    Créer un meal plan dans Mealie (ordre randomisé)
    """
    log("📅 Création du meal plan...")
    
    # Randomiser l'ordre des recettes
    random.shuffle(recipe_ids)
    
    url = f"{MEALIE_URL}/api/households/mealplans"
    headers = {
        'Authorization': f'Bearer {MEALIE_TOKEN}',
        'Content-Type': 'application/json',
    }
    
    current_date = start_date
    created = 0
    
    for day_name in DAYS_TO_PLAN:
        if not recipe_ids:
            break
        
        recipe_id = recipe_ids.pop(0)
        
        meal_plan_data = {
            'date': current_date.strftime('%Y-%m-%d'),
            'entryType': ENTRY_TYPE,
            'recipeId': recipe_id
        }
        
        try:
            response = requests.post(url, headers=headers, json=meal_plan_data, timeout=30)
            
            if response.status_code in [200, 201]:
                log(f"   ✅ {day_name.capitalize()}")
                created += 1
            else:
                log(f"   ⚠️  {day_name.capitalize()} : Erreur {response.status_code}")
        
        except Exception as e:
            log(f"   ❌ {day_name.capitalize()} : {str(e)[:50]}")
        
        current_date += timedelta(days=1)
    
    log("")
    return created

# =============================================================================
# FONCTION PRINCIPALE
# =============================================================================

def main(magic_link_arg=None, week_offset=0):
    start_time = time.time()

    if DEBUG_MODE:
        print("="*80)
        print("🍳 Génération automatique du meal plan Mealie")
        print("="*80 + "\n")

    # Récupérer les recettes HelloFresh
    # Priorité 1: Argument de ligne de commande
    # Priorité 2: Config file
    magic_link = magic_link_arg or HELLOFRESH_MAGIC_LINK

    if not magic_link:
        print("❌ Erreur: Vous devez fournir un magic link")
        print("\nUsage:")
        print('  ./run.sh -m "https://click.bnlx.hellofresh.link/..." -w 1')
        print('  OU')
        print('  python3 hellofresh2mealiemenu.py -m "https://click.bnlx.hellofresh.link/..." -w 1')
        print('\nOu ajoutez hellofresh_magic_link dans config.yaml')
        return

    hf_recipes = get_current_week_recipes_with_magic_link(magic_link, SUBSCRIPTION_ID, week_offset)
    
    if not hf_recipes:
        print("❌ Aucune recette HelloFresh trouvée")
        return
    
    if DEBUG_MODE:
        print("📋 Recettes HelloFresh de la semaine:")
        for i, title in enumerate(hf_recipes, 1):
            print(f"   {i}. {title}")
        print()
    
    # Récupérer toutes les recettes Mealie
    mealie_recipes = get_all_mealie_recipes()
    
    if not mealie_recipes:
        print("❌ Aucune recette Mealie trouvée")
        return
    
    # Matcher les recettes
    log("🔗 Matching des recettes...")
    
    matched_ids = []
    
    for hf_title in hf_recipes:
        match = match_recipe(hf_title, mealie_recipes)
        
        if match:
            mealie_title, mealie_id, score = match
            
            if score >= MATCHING_THRESHOLD:
                log(f"   ✅ {hf_title}")
                log(f"      → {mealie_title} (score: {score:.2f})")
                matched_ids.append(mealie_id)
            else:
                log(f"   ⚠️  {hf_title} (score: {score:.2f})")
        else:
            log(f"   ⚠️  {hf_title} (aucun match)")
    
    log("")
    
    if not matched_ids:
        print("❌ Aucune recette matchée")
        return
    
    # Calculer la semaine cible pour Mealie
    # HelloFresh livre en fin de semaine W, on mange pendant la semaine W+1
    # Donc: recettes HelloFresh W+offset → planning Mealie pour semaine W+offset+1
    today = datetime.now()

    # Calculer le prochain lundi (début de la semaine suivante)
    days_until_next_monday = (7 - today.weekday()) % 7
    if days_until_next_monday == 0:
        days_until_next_monday = 7
    next_monday = today + timedelta(days=days_until_next_monday)

    # Ajouter le week_offset pour obtenir la semaine cible
    target_monday_date = next_monday + timedelta(weeks=week_offset)
    target_sunday = target_monday_date + timedelta(days=6)

    log(f"📅 Planning semaine {target_monday_date.isocalendar()[1]} ({target_monday_date.strftime('%d/%m')} - {target_sunday.strftime('%d/%m')})\n", "always")
    
    # Supprimer les meal plans existants
    delete_week_mealplans(target_monday_date, target_sunday)

    # Créer le nouveau meal plan
    created = create_meal_plan(matched_ids, target_monday_date)
    
    elapsed = time.time() - start_time
    
    if DEBUG_MODE:
        print("="*80)
        print("✅ TERMINÉ")
        print("="*80)
        print(f"\n🌐 Vérifie ton planning: {MEALIE_URL}/g/home/mealplan\n")
    else:
        print(f"✅ Meal plan créé pour semaine {target_monday_date.isocalendar()[1]} ({created} recettes) en {elapsed:.1f}s")

if __name__ == "__main__":
    # Gestion des arguments de ligne de commande
    parser = argparse.ArgumentParser(
        description='Génère automatiquement un meal plan dans Mealie à partir des recettes HelloFresh',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Exemples:
  # Semaine actuelle
  ./run.sh -m "https://click.bnlx.hellofresh.link/..."

  # Semaine prochaine
  ./run.sh -m "https://click.bnlx.hellofresh.link/..." -w 1

  # Planifier plusieurs semaines d'un coup (même magic link)
  ./run.sh -m "https://click.bnlx.hellofresh.link/..." --weeks 0,1
  ./run.sh -m "https://click.bnlx.hellofresh.link/..." --weeks 1,2
  ./run.sh -m "https://click.bnlx.hellofresh.link/..." --weeks 0,1,2

  # Utiliser le magic link du fichier config.yaml
  ./run.sh
        '''
    )

    parser.add_argument(
        '-m', '--magic-link',
        type=str,
        help='Lien magique HelloFresh reçu par email'
    )

    parser.add_argument(
        '-w', '--week',
        type=int,
        default=0,
        help='Décalage de semaines (0=actuelle, 1=prochaine, etc.)'
    )

    parser.add_argument(
        '--weeks',
        type=str,
        help='Liste de semaines à planifier séparées par des virgules (ex: 0,1,2)'
    )

    args = parser.parse_args()

    try:
        # Si --weeks est fourni, planifier plusieurs semaines
        if args.weeks:
            week_offsets = [int(w.strip()) for w in args.weeks.split(',')]
            print(f"📅 Planification de {len(week_offsets)} semaine(s) : {', '.join(map(str, week_offsets))}\n")

            for i, week_offset in enumerate(week_offsets, 1):
                if i > 1:
                    print("\n" + "="*80 + "\n")
                print(f"📌 Semaine {week_offset} ({i}/{len(week_offsets)})")
                main(magic_link_arg=args.magic_link, week_offset=week_offset)
        else:
            # Comportement classique avec -w
            main(magic_link_arg=args.magic_link, week_offset=args.week)
    except KeyboardInterrupt:
        print("\n⚠️  Interrompu")
    except Exception as e:
        print(f"❌ Erreur: {e}")
        if DEBUG_MODE:
            import traceback
            traceback.print_exc()