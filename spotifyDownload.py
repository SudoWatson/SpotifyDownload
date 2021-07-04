import http
import json
import os
import requests
import base64
import spotipy
from tqdm.utils import disp_trim
import youtube_dl

from tqdm import tqdm
from dotenv import load_dotenv
from ytmusicapi import YTMusic
from spotipy.oauth2 import SpotifyOAuth
from zipfile import ZipFile

load_dotenv()

spotURL = "https://api.spotify.com/"
directory = ("//".join(os.path.realpath(__file__).split('\\')[:-1]))
playlist = None
songs = []
songIDS = []
scope = "user-library-read"
ydl_opts = {
    "outtmpl": directory+"/music/%(title)s.%(ext)s",
    "restrictfilenames": True,
    "ignoreerrors": True,
    "download_archive": directory+"/archive",
    "format": "bestaudio/best",
    "geo_bypass": True,
    "keepvideo": False,
    "no_color": False,
    "ffmpeg_location": os.getenv("FFMPEG_PATH"),
    "postprocessors": [{
        "key": "FFmpegExtractAudio",
        "preferredcodec": "mp3",
        "preferredquality": "192",
    }]
}



# Get song titles and artists from Spotify playlist
print("Gathering Spotify song data...")
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

results = sp.current_user_playlists()["items"]
for plst in results:
    if plst["name"] == "Test Playlist":
        playlist = sp.playlist(playlist_id=plst["id"])["tracks"]

while playlist:
    for song in tqdm(playlist["items"]):
        song = song["track"]
        songs.append({"name": song["name"], "artist": song["artists"][0]["name"]})
    if playlist["next"]:
        playlist = sp.next(playlist)
    else:
        playlist = None

print("Spotify data gathered")

# Get YouTube watch IDs of all songs
print("Getting song IDs...")

ytm = YTMusic((directory+"/headers_auth.json"))

for song in tqdm(songs):
    ytSongList = ytm.search(query=(song["name"] + " " + song["artist"]), filter="songs")
    id = None
    for ytSong in ytSongList:
        id = None
        for artist in ytSong["artists"]:
            if song["artist"].lower() in artist["name"].lower() or artist["name"].lower() in song["artist"].lower():
                id = "https://www.youtube.com/watch?v=" + ytSong["videoId"]
                break
        if id:
            songIDS.append(id)
            break
    if not id: print(f" \033[31mCouldn't find song {song['name']}\033[0m")

print("Song IDs gathered")

# Download all songs
print("Downloading songs...")
with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    for song in tqdm(songIDS):
        ydl.download([song])

print("Downloading finished")

# Compressing music folder
print("Compressing files...")
zip = ZipFile("music.zip", "w")

for song in tqdm(os.listdir((directory + "/music"))):
    zip.write((directory + "/music/" + song),song)

zip.close()
print("Finished music compression")