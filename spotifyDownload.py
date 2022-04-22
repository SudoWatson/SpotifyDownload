from datetime import datetime
import io
import os
import sys
import requests
import logging
from zipfile import ZipFile
from dotenv import load_dotenv

import spotipy
from spotipy.oauth2 import SpotifyOAuth
from ytmusicapi import YTMusic
from tqdm.utils import disp_trim
from tqdm import tqdm
import youtube_dl
import eyed3





print("""
  /$$$$$$                        /$$     /$$  /$$$$$$                                             
 /$$__  $$                      | $$    |__/ /$$__  $$                                            
| $$  \__/  /$$$$$$   /$$$$$$  /$$$$$$   /$$| $$  \__//$$   /$$                                   
|  $$$$$$  /$$__  $$ /$$__  $$|_  $$_/  | $$| $$$$   | $$  | $$                                   
 \____  $$| $$  \ $$| $$  \ $$  | $$    | $$| $$_/   | $$  | $$                                   
 /$$  \ $$| $$  | $$| $$  | $$  | $$ /$$| $$| $$     | $$  | $$                                   
|  $$$$$$/| $$$$$$$/|  $$$$$$/  |  $$$$/| $$| $$     |  $$$$$$$                                   
 \______/ | $$____/  \______/    \___/  |__/|__/      \____  $$                                   
          | $$                                        /$$  | $$                                   
          | $$                                       |  $$$$$$/                                   
          |__/                                        \______/                                    
 /$$$$$$$                                    /$$                           /$$                    
| $$__  $$                                  | $$                          | $$                    
| $$  \ $$  /$$$$$$  /$$  /$$  /$$ /$$$$$$$ | $$  /$$$$$$   /$$$$$$   /$$$$$$$  /$$$$$$   /$$$$$$ 
| $$  | $$ /$$__  $$| $$ | $$ | $$| $$__  $$| $$ /$$__  $$ |____  $$ /$$__  $$ /$$__  $$ /$$__  $$
| $$  | $$| $$  \ $$| $$ | $$ | $$| $$  \ $$| $$| $$  \ $$  /$$$$$$$| $$  | $$| $$$$$$$$| $$  \__/
| $$  | $$| $$  | $$| $$ | $$ | $$| $$  | $$| $$| $$  | $$ /$$__  $$| $$  | $$| $$_____/| $$      
| $$$$$$$/|  $$$$$$/|  $$$$$/$$$$/| $$  | $$| $$|  $$$$$$/|  $$$$$$$|  $$$$$$$|  $$$$$$$| $$      
|_______/  \______/  \_____/\___/ |__/  |__/|__/ \______/  \_______/ \_______/ \_______/|__/      
                                                                                                  """)


# TODO Cleanup the following stuff

spotURL = "https://api.spotify.com/"
# Directory to download files to
#directory = ("//".join(os.path.realpath(__file__).split('\\')[:-1]))   # Windows?
directory = ("/".join(os.path.realpath(__file__).split('/')[:-1]))   # TODO Linux? Even needed here?

authDir = (directory + "/headers_auth.json")



# Setup log file
logDir = os.path.join(directory, "logs")
logFileName = datetime.now().strftime("%m-%d-%Y-%H_%M") + ".log"
logPath = os.path.join(logDir, logFileName)
if not os.path.exists(logDir):  # Create log folder if doesn't exist
    os.mkdir(logDir)
with open(logPath, "w+") as f:
    f.write(logFileName+'\n')

# Redifine log level names
logging.OKAY = logging.WARNING + 5

# TODO Different names for stream than file
logging.addLevelName(logging.DEBUG,     "[   DBUG   ]")
logging.addLevelName(logging.INFO,      "[   INFO   ]")
logging.addLevelName(logging.WARNING,   "[   WARN   ]")
logging.addLevelName(logging.OKAY,      "[   OKAY   ]")
logging.addLevelName(logging.ERROR,     "[   EROR   ]")
logging.addLevelName(logging.CRITICAL,  "[ CRITICAL ]")

# Add OKAY level
def logOKAY(self, message, *args, **kws):
    self._log(logging.OKAY, message, args, **kws) 

logging.Logger.okay = logOKAY

# Initiate logger
logger = logging.getLogger(" Spotify Downloader  ")
logger.setLevel(logging.DEBUG)

# Log format
logFormat = logging.Formatter("%(levelname)s :%(name)s: %(asctime)s - %(message)s")
streamFormat = logging.Formatter("%(levelname)s - %(message)s")

# Create file handler for logger
file_handler = logging.FileHandler(logPath)
file_handler.setFormatter(logFormat)
file_handler.setLevel(logging.DEBUG)

# Create stream handler
streamHandler = logging.StreamHandler()
streamHandler.setFormatter(streamFormat)
streamHandler.setLevel(logging.INFO)

# Add handlers to logger
logger.addHandler(file_handler)
logger.addHandler(streamHandler)



logger.debug("Begin Log\n")


# Begin
if not os.path.exists(os.path.join(directory, ".env")):
    logger.critical("No .env file found")
    sys.exit(1)
else:
    logger.debug(".env file found")


# TODO Clean this up too
newDir = input("Download directory: ")
Playlist_Name = input("Playlist Name: ")

directory += "/music"


load_dotenv()



if newDir != "":
    directory = newDir

if not os.path.isdir(directory):
    os.mkdir(directory)

logger.info(f"Downloading {Playlist_Name} playlist to {directory} ...")


# TODO ReadMe but like good
# TODO Failed songs list, then list them all at end
# TODO Take arguments
# TODO Notifications?? Using plyer seems hella easy
# TODO Functions


playlistDirectory = os.path.join(directory, Playlist_Name)
playlist = None
songs = []
ytSongs = []
scope = "user-library-read"
ydl_opts = {
    "outtmpl": playlistDirectory + "/%(title)s.%(ext)s",
    "restrictfilenames": True,
    "ignoreerrors": True,
    "download_archive": playlistDirectory+"/archive",
    "format": "bestaudio/best",
    "geo_bypass": True,
    "keepvideo": False,
    "no_color": False,
#    "ffmpeg_location": os.getenv("FFMPEG_PATH"),  # Linux shouldn't need?
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }]
}


class Song:
    def __init__(self, title, id, artist, album, coverURL):  # User 'PRIV' Frame to store ID for comparing with archive and removing no longer wanted songs
        self.title = title
        self.id = id
        self.artist = artist
        self.album = album
        self.coverURL = coverURL


# Get song titles and artists from Spotify playlist
logger.info("Gathering Spotify song data...")
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

results = sp.current_user_playlists()["items"]  # Gets user playlists
for plst in results:
    if plst["name"] == Playlist_Name:  # Gets 'Playlist_Name' playlist
        playlist = sp.playlist(playlist_id=plst["id"])["tracks"]

while playlist:  # Goes through 100 song chunks of the playlist
    for song in tqdm(playlist["items"]):  # Goes through each song in chunk
        song = song["track"]
        songs.append(Song(song["name"], 0, song["artists"][0]["name"], song["album"]["name"], song["album"]["images"][2]["url"]))  # Get song data
    if playlist["next"]:  # Continue if there is another song chunk
        playlist = sp.next(playlist)
    else:  # Don't continue if not another chunk
        playlist = None

logger.okay("Spotify data gathered")

# Get YouTube watch IDs of all songs
logger.info("Getting song IDs...")

ytm = YTMusic(authDir)

for song in tqdm(songs):
    ytSongList = ytm.search(query=(song.title + " " + song.artist), filter="songs")  # Search for song on YouTube Music
    id = None
    for ytSong in ytSongList:
        id = None
        for artist in ytSong["artists"]:
            if song.artist.lower() in artist["name"].lower() or artist["name"].lower() in song.artist.lower():  # Check if song in search results is likely correct
                song.id = ytSong["videoId"]
                id = "https://www.youtube.com/watch?v=" + song.id
                break
        if id:
            ytSongs.append(song)  # Add song if found likely result
            break
    if not id: logger.error(f" \033[31mCouldn't find song {song.title}\033[0m")

logger.okay("Song IDs gathered")

# Download all songs
logger.info("Downloading songs...")
ydl_opts["outtmpl"] = playlistDirectory+"/%(title)s.%(ext)s"
with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    for song in tqdm(ytSongs):
        songURL = "https://www.youtube.com/watch?v=" + song.id
        song.path = (ydl.prepare_filename(ydl.extract_info(songURL)))
        song.path = song.path[:song.path.index(".")]  # Remove extension
        song.path += ".mp3"

logger.okay("Downloading finished")

# Write mp3 metadata
logger.info("Writing metadata...")
for songFilePath in tqdm(os.listdir((playlistDirectory))):
    for ytSong in ytSongs:
        if songFilePath in ytSong.path:
            songFile = eyed3.load(os.path.join(playlistDirectory, songFilePath)).tag
            songFile.title = ytSong.title
            songFile.artist = ytSong.artist
            songFile.album = ytSong.album
            songFile.privates.set(bytes(ytSong.id, encoding='utf-8'), b"Spotify Downloader - Lennert")
            
            # Get image data
            response = requests.get(ytSong.coverURL)
            image_bytes = io.BytesIO(response.content)
            # Add image to mp3
            songFile.images.set(type_=3, img_data=image_bytes.getvalue(), mime_type=response.headers["Content-Type"], description=u"", img_url=None)
            
            songFile.save()
            break

logger.okay("Finished writing metadata")


# TODO Remove old songs
if os.path.exists(playlistDirectory):
    logger.info("Removing old songs...")
    removedSongNames = []
    lines = ""
    removeIDs = []
    IDs = None
    with open(os.path.join(playlistDirectory, "archive"), 'r') as f:
        IDs = f.readlines()
    for songFilePath, songID in tqdm(zip(os.listdir(playlistDirectory), IDs)):  # Go through each song already downloaded
        want = False
        
        #print(songFile.privates.get(bytes(songID, encoding='utf-8')))
        for song in songs:  # Go through each song expected to have
            if songFilePath in song.path:  # If downloaded song is in expected songs, we want it
                want = True
                break
            # if song.id not in songID:
            #     print(song.id)
            #     print(songID)
            #     removeIDs.append(songID)
                #IDs.remove(songID)  # Remove song from archive
        if not want:  # Remove song if we don't want it
            songFile = eyed3.load(os.path.join(playlistDirectory, songFilePath))
            if songFile is None: continue
            songFile = songFile.tag
            logger.info(f"Removed song: {songFile.title}")
            removedSongNames.append(songFile.title)
            removeID = songFile.privates.get(b"Spotify Downloader - Lennert").owner_data
            removeIDs.append(removeID.decode("utf-8"))
            os.remove(os.path.join(playlistDirectory, songFilePath))  # Remove song
    with open(os.path.join(playlistDirectory, "archive"), 'w') as f:
        for line in IDs:
            if line.replace("youtube ", '').replace('\n', '') not in removeIDs:
                f.write(line)
    if not len(removedSongNames):
        logger.info("No songs removed")


logger.okay("Spotify Downloader complete!")
