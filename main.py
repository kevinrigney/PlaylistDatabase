#!/usr/bin/env python3

from time import sleep
import random
import signal as sig
from threading import Event
from datetime import datetime as dt
from traceback import print_exc

# Youtube stuff
from apiclient.errors import HttpError
import youtube_search
import youtube_playlist

# The playlist database
from PlaylistDatabase import PlaylistDatabase

# The secret sauce - a function that takes in the channel dict
# and figures out if there's a new song
from lookup import lookup_info_from_channel_dict

end_event = Event() 
pldb = PlaylistDatabase(config_file='PlaylistDatabaseConfig.ini',connect=False) # The database
searcher = youtube_search.YoutubeSearcher() # When searching for songs in youtube
ytpl = youtube_playlist.YoutubePlaylist() # For manipulating youtube playlists

def siginthandler(signum,frame):
    print('Got signal')
    end_event.set()    

def grabinfo(channel_dict,db):
    '''
    Given a channel dictionary containing information about a channel
    Scrape the artist and title
    '''
    site=channel_dict['site']
    lastartist = channel_dict['lastartist']
    lastsong = channel_dict['lastsong']
    ignoreartists = channel_dict['ignoreartists']
    ignoretitles = channel_dict['ignoretitles']
    name = channel_dict['name']
    playlist_id = channel_dict['playlist']
    #playlist_date = channel_dict['playlist']['date']
    print('Updating channel %s'%(name,))

    # This function checks the state of the channel. If there is a new
    # song that should be added to the DB/Youtube then it will return it.
    # If not it returns a  None's (Not very pythonic I know)
    #
    # It should do all of the checking if there is a song to be ignored
    # or if the song is a duplicate to the previous song (that's why
    # we give it the entire dict). In a custom implmentation this can
    # actually do whatever you want but I wanted to abstract as much 
    # of the functionality as possible out of the main.
    artist,song,album = lookup_info_from_channel_dict(channel_dict)
    
    print('Last song: "' + str(lastsong) + '" Last artist: "' + str(lastartist) + '"')
    print('This song: "' + str(song) + '" This artist: "' + str(artist) + '" This album: "' + str(album)+'"')
    
    if artist != None:
            
        # Before we look up the song on youtube see if there
        # is already an entry for this one
        try:
            print('Looking up in database...')
            url = db.look_up_song_youtube(artist,album,song)
            # Getting this ID assumes we always have a youtube short URL
            ytid = url.split('youtu.be/')[1] # HTTPS Indifferent

            # Make sure the video hasn't been taken down.
            if not searcher.is_video_valid(ytid):
                # Trigger it to look up the track again.
                print('Video ' + ytid + ' has ben taken down. Re-searching.')
                raise LookupError

        except LookupError:
            # Ok, look it up             
            print('Song not found in DB. Looking up in youtube.')   
            (url,ytid)=searcher.get_most_viewed_link(artist+' '+song)
            
        if url!='':
            print('URL Found. Adding to station DB playlist.')
            time_now = dt.now()
            print('Url: %s'%url)
            db.add_track_to_station_playlist(name,artist,album,song,time_now,url)
            print('Adding to youtube playlist')
            try:
                ytpl.add_video_to_playlist(ytid,playlist_id)
            except HttpError as e:
                if e._get_reason() == 'Playlist contains maximum number of items.':
                    print('Playlist is too large. Removing the last 100 items.')
                    ytpl.remove_last_videos_from_playlist(playlist_id)
                    ytpl.add_video_to_playlist(id,playlist_id)
            print('Done')
        else:
            print('Url not found.')


def main():

    # Run this script every 120(ish) seconds and try to get the next song
    while (not end_event.isSet()):
        sleeptime = random.randint(100,140)
        try:
            # Re-open and close the conntection every time 
            with pldb:
                for channel_dict in pldb.get_station_data():
                    print() 
                    if(channel_dict['active']):
                        grabinfo(channel_dict,pldb)
                        #sleeptime-=10
                    else:
                        print('Skipping channel: ' + channel_dict['name'])
        except:
            print_exc()
            print('Got exception')

        if sleeptime <=0:
            sleeptime=10
        print('Sleeping for %d seconds'%(sleeptime,))
        while (sleeptime > 0) and (not end_event.isSet()):
            sleep(1)
            sleeptime -=1

if __name__ == "__main__":
    sig.signal(sig.SIGINT,siginthandler)
    main()
