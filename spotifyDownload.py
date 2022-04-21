import io
import os
import requests
import spotipy
from tqdm.utils import disp_trim
import youtube_dl
import eyed3

from tqdm import tqdm
from dotenv import load_dotenv
from ytmusicapi import YTMusic
from spotipy.oauth2 import SpotifyOAuth
from zipfile import ZipFile

load_dotenv()




Playlist_Name = "Good Songs"

spotURL = "https://api.spotify.com/"
directory = ("//".join(os.path.realpath(__file__).split('\\')[:-1]))
playlistDirectory = os.path.join(directory, "playlists", Playlist_Name)
playlist = None
songs = []
ytSongs = []
scope = "user-library-read"
ydl_opts = {
    "outtmpl": playlistDirectory + "/music/%(title)s.%(ext)s",
    "restrictfilenames": True,
    "ignoreerrors": True,
    "download_archive": playlistDirectory+"/archive",
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


class Song:
    def __init__(self, title, id, artist, album, coverURL):  # User 'PRIV' Frame to store ID for comparing with archive and removing no longer wanted songs
        self.title = title
        self.id = id
        self.artist = artist
        self.album = album
        self.coverURL = coverURL


# Get song titles and artists from Spotify playlist
print("Gathering Spotify song data...")
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

print("Spotify data gathered")

# Get YouTube watch IDs of all songs
print("Getting song IDs...")

ytm = YTMusic((directory+"/headers_auth.json"))

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
    if not id: print(f" \033[31mCouldn't find song {song.title}\033[0m")
    # if song is songs[2]:  #TODO ends at fifth song for testing
    #     break

print("Song IDs gathered")

# Download all songs
print("Downloading songs...")
ydl_opts["outtmpl"] = playlistDirectory+"/music/%(title)s.%(ext)s"
with youtube_dl.YoutubeDL(ydl_opts) as ydl:
    for song in tqdm(ytSongs):
        songURL = "https://www.youtube.com/watch?v=" + song.id
        song.path = (ydl.prepare_filename(ydl.extract_info(songURL)))
        song.path = song.path[:song.path.index(".")]  # Remove extension
        song.path += ".mp3"

print("Downloading finished")

# Write mp3 metadata
print("Writing metadata...")
for songFilePath in tqdm(os.listdir((playlistDirectory + "/music"))):
    for ytSong in ytSongs:
        if songFilePath in ytSong.path:
            songFile = eyed3.load(os.path.join(playlistDirectory, "music", songFilePath)).tag
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
            break # TODO Uhmmmm I feel like we DON'T want this

print("Finished writing metadata")


# TODO Remove old songs
if os.path.exists(playlistDirectory + "/music"):
    print("Removing old songs...")
    removedSongNames = []
    lines = ""
    removeIDs = []
    IDs = None
    with open(os.path.join(playlistDirectory, "archive"), 'r') as f:
        IDs = f.readlines()
    for songFilePath, songID in tqdm(zip(os.listdir((playlistDirectory + "/music")), IDs)):  # Go through each song already downloaded
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
            songFile = eyed3.load(os.path.join(playlistDirectory, "music", songFilePath)).tag
            removedSongNames.append(songFile.title)
            removeID = songFile.privates.get(b"Spotify Downloader - Lennert").owner_data
            removeIDs.append(removeID.decode("utf-8"))
            os.remove(os.path.join(playlistDirectory, "music", songFilePath))  # Remove song
    with open(os.path.join(playlistDirectory, "archive"), 'w') as f:
        for line in IDs:
            if line.replace("youtube ", '').replace('\n', '') not in removeIDs:
                f.write(line)
    if len(removedSongNames):
        print("Removed the following songs:")
        for songName in removedSongNames:
            print(songName)
    else:
        print("No songs removed")



# Compressing music folder
print("Compressing files...")
zip = ZipFile(os.path.join(playlistDirectory, "music.zip"), "w")

for song in tqdm(os.listdir((playlistDirectory + "/music"))):
    zip.write((playlistDirectory + "/music/" + song),song)

zip.close()
print("Finished music compression")
