workingDir=pwd

cd $1

git pull https://github.com/SudoWatson/spotifyDownload

.venv/Scripts/python.exe -m pip install --upgrade pip

.venv/Scripts/python.exe -m pip install -r requirements.txt

cd $wd