# HelloFresh to Mealie Menu 🍳

Script Python pour générer automatiquement un planning de repas hebdomadaire dans [Mealie](https://mealie.io/) à partir de vos commandes HelloFresh.

## 🎯 Fonctionnalités

- ✅ Connexion automatique à HelloFresh
- ✅ Récupération des recettes de ta box de la semaine
- ✅ Matching automatique avec tes recettes Mealie existantes
- ✅ Création du meal plan pour la semaine suivante (lundi→samedi)
- ✅ Mode headless - Compatible cron/automation
- ✅ Mode silencieux par défaut / verbeux en DEBUG
- ✅ Configuration externe via `config.yaml`

## 📋 Prérequis

- Python 3.9+
- Un compte HelloFresh actif
- Une instance Mealie avec les recettes HelloFresh déjà importées
- Les recettes HelloFresh doivent être dans Mealie avec des noms similaires

## 🚀 Installation

```bash
# 1. Cloner le repo
git clone https://github.com/hello-lemon/hellofresh2mealiemenu
cd hellofresh2mealiemenu

# 2. Installer les dépendances
pip3 install playwright requests pyyaml

# 3. Installer Chromium pour Playwright
python3 -m playwright install chromium

# 4. (Linux uniquement) Installer les dépendances système
sudo python3 -m playwright install-deps
```

## ⚙️ Configuration

```bash
# 1. Copier le fichier de config par défaut
cp default-config.yaml config.yaml

# 2. Éditer config.yaml avec tes identifiants
nano config.yaml
```

### Exemple de `config.yaml`

```yaml
# HelloFresh
hellofresh_email: "ton_email@example.com"
hellofresh_password: "ton_mot_de_passe"
hellofresh_subscription_id: "123456"

# Mealie
mealie_url: "https://ton-instance-mealie.fr"
mealie_token: "ton_token_mealie"

# Planning
entry_type: "dinner"  # Type de repas: dinner, lunch, breakfast, side
matching_threshold: 0.6  # Seuil de matching (0.5 à 0.8) - plus bas = plus permissif

# Jours de la semaine à planifier
days_to_plan:
  - monday
  - tuesday
  - wednesday
  - thursday
  - friday
  - saturday
```

### Comment trouver ton `subscription_id` HelloFresh ?

1. Va sur https://www.hellofresh.fr/my-account/deliveries/menu
2. Regarde l'URL : `?subscriptionId=123456`
3. Le nombre après `subscriptionId=` c'est ton ID

### Comment créer un token Mealie ?

1. Va dans Mealie → Settings → API Tokens
2. Crée un nouveau token
3. Copie le token généré dans `config.yaml`

## 📝 Utilisation

### Lancement manuel

```bash
python3 hellofresh2mealiemenu.py
```

**Mode silencieux (par défaut) :**
```
✅ Meal plan créé pour semaine 45 (6 recettes) en 12.3s
```

**Mode DEBUG (édite le script et mets `DEBUG_MODE = True`) :**
```
🔐 Connexion à HelloFresh...
📋 Récupération des recettes semaine 2025-W45...
📚 Chargement des recettes Mealie...
🔗 Matching des recettes...
✅ Meal plan créé pour semaine 45 (6 recettes) en 12.3s
```

### Automatisation avec cron

Pour lancer automatiquement chaque semaine :

```bash
# Éditer le crontab
crontab -e

# Ajouter cette ligne (tous les samedis à 10h)
0 10 * * 6 cd ~/scripts/hellofresh2mealie && python3 hellofresh2mealiemenu.py >> mealplan.log 2>&1
```

**Explication :**
- `0 10 * * 6` = Samedi à 10h00
- Le script génère le planning pour le **lundi suivant**
- Les logs sont sauvegardés dans `mealplan.log`

### Autres exemples de timing cron

```bash
# Tous les dimanches à 20h
0 20 * * 0 cd ~/scripts/hellofresh2mealie && python3 hellofresh2mealiemenu.py >> mealplan.log 2>&1

# Tous les vendredis à 18h
0 18 * * 5 cd ~/scripts/hellofresh2mealie && python3 hellofresh2mealiemenu.py >> mealplan.log 2>&1
```

## 🔧 Personnalisation

### Changer les jours planifiés

Dans `config.yaml` :

```yaml
# Pour planifier seulement 4 jours (lundi au jeudi)
days_to_plan:
  - monday
  - tuesday
  - wednesday
  - thursday

# Pour inclure le dimanche
days_to_plan:
  - sunday
  - monday
  - tuesday
  - wednesday
  - thursday
  - friday
  - saturday
```

### Changer le type de repas

Dans `config.yaml` :

```yaml
entry_type: "lunch"  # Valeurs possibles: dinner, lunch, breakfast, side
```

### Ajuster le seuil de matching

Si trop/pas assez de recettes sont matchées, ajuste dans `config.yaml` :

```yaml
matching_threshold: 0.7  # Valeur entre 0.5 et 0.8
# Plus bas (0.5) = plus permissif, plus de matches
# Plus haut (0.8) = plus strict, matches plus précis
```

## ⚠️ Troubleshooting

**Problème : Échec de connexion HelloFresh**
- Active le mode debug dans `config.yaml` : `debug_mode: true`
- Le script créera des captures d'écran pour diagnostiquer le problème :
  - `hellofresh_no_email_field.png` - Le champ email n'a pas été trouvé
  - `hellofresh_no_password_field.png` - Le champ mot de passe n'a pas été trouvé
  - `hellofresh_no_submit_button.png` - Le bouton de connexion n'a pas été trouvé
  - `hellofresh_login_failed.png` - La connexion a échoué (identifiants invalides ou changement du site)
- Vérifie tes identifiants dans `config.yaml`
- **Important** : HelloFresh peut bloquer les serveurs/VPS avec Cloudflare. Lance plutôt le script depuis ton ordinateur personnel.

**Problème : Aucune recette HelloFresh trouvée**
- Vérifie tes identifiants dans `config.yaml`
- Vérifie ton `subscription_id`
- Regarde la capture d'écran : `hellofresh_error.png`
- **Important** : HelloFresh peut bloquer les serveurs/VPS avec Cloudflare. Lance plutôt le script depuis ton ordinateur personnel.

**Problème : Aucune recette matchée**
- Vérifie que les recettes HelloFresh sont bien importées dans Mealie
- Baisse le seuil de matching à 0.5 dans le script

**Problème : Erreur Mealie API**
- Vérifie le token Mealie dans `config.yaml`
- Vérifie l'URL Mealie (avec https://)

**Problème : playwright not found**
```bash
pip3 install playwright
python3 -m playwright install chromium
```

**Problème : Cloudflare bloque la connexion**
- HelloFresh peut bloquer les IPs de serveurs/VPS
- Lance le script depuis ton ordinateur personnel plutôt qu'un serveur distant
- Ou utilise un VPN/proxy résidentiel

## 📊 Logs

```bash
# Voir les derniers logs
tail -20 mealplan.log

# Suivre les logs en temps réel
tail -f mealplan.log
```

## 🤝 Contribution

Les contributions sont les bienvenues ! N'hésite pas à ouvrir une issue ou une pull request.

## 📄 Licence

MIT

## 🙏 Crédits

- [Mealie](https://mealie.io/) - Application de gestion de recettes
- [Playwright](https://playwright.dev/) - Automation de navigateur
- [HelloFresh](https://www.hellofresh.fr/) - Service de box repas

---

**Note** : Ce script n'est pas affilié à HelloFresh. Il est destiné à un usage personnel pour automatiser la création de meal plans.
