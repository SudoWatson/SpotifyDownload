echo "Creating virtual environment(venv)..."
python -m venv $1/.venv
echo "Installing Python packages"
bash $1/update.bash $1
echo "Gathering resources"