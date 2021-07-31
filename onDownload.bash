echo "Creating virtual environment(venv)..."
python -m venv ./.venv
echo "Installing Python packages"
bash ./update.bash
echo "Gathering resources"