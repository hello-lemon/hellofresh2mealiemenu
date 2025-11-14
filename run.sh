#!/bin/bash
# Wrapper script pour hellofresh2mealiemenu
# Gère automatiquement le venv et les dépendances

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

# Créer le venv s'il n'existe pas
if [ ! -d "$VENV_DIR" ]; then
    echo "🔧 Création du virtual environment..."
    python3 -m venv "$VENV_DIR"
fi

# Activer le venv
source "$VENV_DIR/bin/activate"

# Installer les dépendances si nécessaire
if ! python3 -c "import playwright" 2>/dev/null; then
    echo "📦 Installation des dépendances..."
    pip3 install -q playwright requests pyyaml
    python3 -m playwright install chromium
fi

# Lancer le script avec tous les arguments passés
python3 "$SCRIPT_DIR/hellofresh2mealiemenu.py" "$@"
