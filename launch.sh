#!/bin/bash

# Script de lancement pour EV Eco-Speed Advisory App
echo "🚗🔋 Lancement de l'EV Eco-Speed Advisory App..."

# Trouver Python 3.12
PYTHON_CMD=""
if command -v python3.12 &> /dev/null; then
    PYTHON_CMD="python3.12"
elif command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
elif command -v python &> /dev/null; then
    PYTHON_CMD="python"
else
    echo "❌ Python n'est pas installé. Veuillez installer Python 3.12+"
    echo "💡 Vous pouvez l'installer avec: brew install python@3.12"
    exit 1
fi

echo "🐍 Python trouvé: $PYTHON_CMD"

# Vérifier si l'environnement virtuel existe
if [ ! -d "venv" ]; then
    echo "📦 Création de l'environnement virtuel..."
    $PYTHON_CMD -m venv venv
    if [ $? -ne 0 ]; then
        echo "❌ Erreur lors de la création de l'environnement virtuel"
        exit 1
    fi
fi

# Activer l'environnement virtuel
echo "🔧 Activation de l'environnement virtuel..."
source venv/bin/activate

# Vérifier que l'activation a fonctionné
if [ -z "$VIRTUAL_ENV" ]; then
    echo "❌ Erreur lors de l'activation de l'environnement virtuel"
    exit 1
fi

# Installer/mettre à jour les dépendances
echo "📚 Installation des dépendances..."
pip install --upgrade pip
pip install -r requirements.txt

# Vérifier que Streamlit est installé
if ! command -v streamlit &> /dev/null; then
    echo "❌ Streamlit n'est pas installé dans l'environnement virtuel"
    echo "🔧 Installation de Streamlit..."
    pip install streamlit
fi

# Lancer l'application
echo "🚀 Lancement de l'application Streamlit..."
echo "📍 L'application sera disponible à : http://localhost:8502"
echo "⏹️  Pour arrêter l'application, appuyez sur Ctrl+C"
echo ""

# Utiliser le chemin complet de streamlit dans l'environnement virtuel
./venv/bin/streamlit run app.py
