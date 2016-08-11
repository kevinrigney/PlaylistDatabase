#!/usr/bin/env python3

import sqlite3
import datetime

from math import floor
from threading import RLock

class PlaylistDatabase():
    '''
    This database is designed to manage songs played by a 
    internet radio station. It stores the web address of the station,
    some details about it, and the playlist of songs.
    The playlist includes a link to a youtube video of the song.
    '''

    def _init_database_schema(self,commit=True):
        '''
        !!! ALL EXISTING DATA IS LOST WHEN USING THIS FUNCTION !!!

        Initialize the database. This consists of:
        * Dropping all relevant tables.
        * Creating new empty tables.
        '''
        self._cur.executescript('''
        DROP TABLE IF EXISTS Artist;
        DROP TABLE IF EXISTS Album;
        DROP TABLE IF EXISTS Track;
        DROP TABLE IF EXISTS Station;
        
        CREATE TABLE Artist (
            id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            name    TEXT UNIQUE
        );
        
        CREATE TABLE Album (
            id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            name   TEXT,
            artist_id  INTEGER,
            unique(name,artist_id)
        );
        
        CREATE TABLE Track (
            id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            name TEXT,
            youtube_link TEXT,
            filesystem_link TEXT, 
            album_id  INTEGER,
            artist_id  INTEGER,
            unique(name,album_id,artist_id)            
        );
            
        CREATE TABLE Station (
            id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            name TEXT,
            web_address TEXT,
            ignore_artists TEXT,
            ignore_titles TEXT,
            youtube_playlist_id TEXT,
            playlist_id INTEGER
        );
            
        ''')
        
        # Get all tables beginning with playlist_
        playlist_tables = self._cur.execute('''
        SELECT name
        FROM sqlite_master
        WHERE name LIKE 'playlist_%'
        '''
        ).fetchall()
        
        # And drop them
        for t in playlist_tables:
            self._cur.execute('DROP TABLE ' +t[0])
        
        if commit:
            self._conn.commit()
    
    def _generate_playlist_name_from_station_name(self,sname):
        sname = sname.replace(' ','_')
        sname = sname.replace('-','_')
        return sname
        
        
    def _get_all_stations(self):
        
        stations = self._cur.execute('''SELECT * from Station''').fetchall()
        return stations
    
    def _get_station_id_from_name(self,name):
        station_id = self._cur.execute('''
        SELECT Station.id from STATION where Station.name = ?''',(name,)).fetchone()[0]
        return station_id
        
    def _get_playlist_id_from_station_id(self,station_id):
        playlist_id = self._cur.execute('''
        SELECT Station.playlist_id from STATION where Station.id = ?''',(station_id,)).fetchone()[0]
        return playlist_id
    
    def _get_playlist_id_from_station_name(self,name):
        playlist_id = self._cur.execute('''
        SELECT Station.playlist_id from STATION where Station.name = ?''',(name,)).fetchone()[0]
        return playlist_id
    
    def _make_playlist(self,name,commit=True):
        # TODO Sanitize the name more to disallow injection
        name = self._generate_playlist_name_from_station_name(name)
    
        # Make the playlist. play_time is unique because this is a playlist for
        # a specific station
        self._cur.execute('''
        CREATE TABLE playlist_''' + name + '''(
            id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            track_id INTEGER,
            play_time VARCHAR(24) UNIQUE
        )
        ''')
        
        # If they're doing a bunch of makes they might not want
        # to commit after each one
        if commit:
            self._conn.commit()
        
        # Return the playlist name
        return 'playlist_'+name
    
    def _make_artist(self,name,get_id=True,commit=True):
        '''
        Create an artist in the table.
        For artists we only have a name.
        '''
        
        self._cur.execute('''
        INSERT OR IGNORE INTO Artist(name)
        VALUES ( ? )''', (name,)
        )
        
        # If they're doing a bunch of makes they might not want
        # to commit after each one
        if commit:
            self._conn.commit()
        
        if get_id:        
            # The ID of the artist
            artist_id = self._cur.execute('SELECT id FROM Artist where name=?',(name,)).fetchone()[0]
            #print(artist_id)
            return artist_id
        
    
    def _make_album(self,artist_id,album,get_id=True,commit=True):
        '''
        Create an album in the table.
        '''
        
        # Get the artist id
        
        self._cur.execute('''
        INSERT OR IGNORE INTO Album(name,artist_id)
        VALUES ( ?, ? )''', (album,artist_id)
        )
        
        # If they're doing a bunch of makes they might not want
        # to commit after each one
        if commit:
            self._conn.commit()
        
        if get_id:        
            # The ID of the album
            album_id = self._cur.execute('SELECT id FROM Album where name=? and artist_id = ?',(album,artist_id)).fetchone()[0]
            #print(artist_id)
            return album_id
        
    def _make_track(self,name,album_id,artist_id,yt_link='',fs_link='',get_id=True,commit=True):
        '''
        Given a track name, ablum ID,and an artist ID, make a track in the
        'Track' table. Optionally a youtube URL or filesystem location can also be specified.
        '''
        
        # We're doing a 'OR REPLACE' because maybe we're updating a track with a 
        # new youtube or filesystem link.
        self._cur.execute('''
        INSERT OR REPLACE INTO Track (name,youtube_link,filesystem_link,album_id,artist_id)
        VALUES( ?, ?, ?, ?, ? ) ''',
        (name,yt_link,fs_link,album_id,artist_id)
        )
        
        # If they're doing a bunch of makes they might not want
        # to commit after each one
        if commit:
            self._conn.commit()
        
        if get_id:
            # And return the ID
            track_id = self._cur.execute('''SELECT id FROM Track where 
            name=? and youtube_link=? and filesystem_link=? and album_id=? and artist_id=?'''
            ,(name,yt_link,fs_link,album_id,artist_id)
            ).fetchone()[0]
            return track_id
        
    def _add_playlist_entry(self,playlist_id,track_id,play_time,get_id=True,commit=True):
        '''
        Given a playlist ID, track ID, and a play time (a string date)
        create a new row in the corresponding playlist table
        '''
        # No 'INSERT OR REPLACE INTO' because this should be unique based on the play times
        self._cur.execute('''
        INSERT INTO ''' + playlist_id + ''' (track_id,play_time)
        VALUES (?, ?)
        ''', (track_id,play_time)
        )
                
        # If they're doing a bunch of makes they might not want
        # to commit after each one
        if commit:
            self._conn.commit()
        
        if get_id:
            playlist_id = self._cur.execute('SELECT id FROM ' + playlist_id + ''' where
            track_id = ? and play_time = ?''',(track_id,play_time)
            ).fetchone()[0]
            return playlist_id
    
    def _does_playlist_exist(self,playlist_common_name):
        '''
        Given a "common name" of a playlist, check if we have one
        already in the database
        '''
        raise NotImplementedError()   
    
    #
    # BEGIN PUBLIC FUNCTIONS
    #
    
    def create_station(self,station_name,web_address,ignore_artists=[],ignore_titles=[],youtube_playlist_id='',get_id=True,commit=True):
        '''
        Create a station and associated playlist
        '''
        
        with self._lock:
            # Create a new playlist to use for this station
            playlist_name = self._make_playlist(station_name)
            
            # v2 will use a different format for this... Probably another table?
            ignore_artists = str(ignore_artists)
            ignore_titles = str(ignore_titles)
            
            #print(playlist_name)
            self._cur.execute('''
            INSERT INTO Station(name,web_address,ignore_artists,ignore_titles,playlist_id,youtube_playlist_id)
            VALUES ( ?, ?, ?, ?, ?, ? )''', (station_name,web_address,ignore_artists,ignore_titles,playlist_name,youtube_playlist_id)
            )
            
            if commit:
                self._conn.commit()
            
            if get_id:
                station_id = self._cur.execute('''
                SELECT Station.id FROM Station WHERE
                name = ? and web_address = ? and ignore_artists = ? and ignore_titles = ? and playlist_id = ? and youtube_playlist_id = ?'''
                ,(station_name,web_address,ignore_artists,ignore_titles,playlist_name,youtube_playlist_id)).fetchone()[0]
                return station_id
        
    
       
    def add_track_to_station_playlist(self,station_name,artist,album,track,date,youtube_link='',commit = True):
        '''
        This public function takes a station common name
        and a tuple representing the tracks data. It looks up the
        playlist, creates an artist (if necessary), creates a 
        track (if necessary), and adds the track to the playlist
        '''
        
        with self._lock:
            # This might happen. But upstream from here we should really be 
            # catching stuff like this
            if artist == '' or track == '':
                #print('Skipped')
                return None
            
            # Make a short link
            youtube_link = youtube_link.replace('https://www.youtube.com/watch?v=','https://youtu.be/')                               
                        
            # Now that we have the data...
            
            # Loop up the station's playlist
            playlist_id = self._get_playlist_id_from_station_name(station_name)
            #print('playlist_id is :'+ playlist_id)
            
            # Make (or don't) the artist
            artist_id = self._make_artist(artist,commit=commit)
            
            # Make (or don't) the album
            album_id = self._make_album(artist_id,album,commit=commit)
            
            # Make (or don't) a track
            track_id = self._make_track(track,album_id,artist_id,youtube_link,commit=commit)
            
            # Make a date. It's stored as a string because 
            # sqlite doesn't have a date data type. That's OK though
            # because sqlite can search based on this string's structure.    
            date_ms = int(floor(date.microsecond/1000))
            date = date.strftime('%Y-%m-%d %H:%M:%S.')+str(date_ms)
            
            # Now that we have the data we can make an entry
            return self._add_playlist_entry(playlist_id,track_id,date,commit=commit)

    def get_latest_station_tracks(self,station_name,num_tracks=1):
        '''
        Get a number of tracks from a station. Order from newest
        to oldest.
        '''
        with self._lock:
            playlist = self._get_playlist_id_from_station_name(station_name)
            
            self._cur.execute('SELECT Track.name, Artist.name, '+playlist+'.play_time, Track.youtube_link, Album.name, Track.filesystem_link FROM ' +playlist + ''' 
            JOIN Artist JOIN Track JOIN Album ON 
            ''' + playlist + '''.track_id = Track.id and Track.artist_id = Artist.id and Track.album_id = Album.id
            ORDER BY ''' + playlist +'.play_time DESC LIMIT ?',(num_tracks,))
            data = self._cur.fetchall()
            
            # The data we will send back
            tracks = []
            for t in data:
                temp = {}
                temp['name'] = t[0]
                temp['artist'] = t[1]
                temp['time'] = t[2]               
                temp['youtube'] = t[3]
                temp['album'] = t[4]
                temp['filesystem'] = t[5]
                tracks.append(temp)
                
            if num_tracks == 1:
                return tracks[0]
            else:
                return tracks
            
    def get_station_data(self,station=None):
        '''
        Return a list of dictionaries of the station data
        '''
        
        with self._lock:
            out_list = []
            for s in self._get_all_stations():
                id,name,web_address,ignore_artists,ignore_titles,youtube_playlist_id,playlist_id = s
                
                if station is not None:
                    if name != station:
                        continue
                
                channel_dict = {}
    
                channel_dict['site'] = web_address
                exec("channel_dict['ignoreartists'] = "+ ignore_artists)
                exec("channel_dict['ignoretitles'] = "+ ignore_titles)
                channel_dict['name'] = name
                channel_dict['playlist'] = youtube_playlist_id
                try:
                    track_data = self.get_latest_station_tracks(name)
                    channel_dict['lastartist'] = track_data['artist']
                    channel_dict['lastsong'] = track_data['name']
                except IndexError:
                    channel_dict['lastartist'] = ''
                    channel_dict['lastsong'] = ''
                    
                
                out_list.append(channel_dict)

        if station is not None:
            return out_list[0]
        else:
            return out_list

    def look_up_song_youtube(self,artist,album,title):
        '''
        Given the artist, album, and title,
        Look up the song's youtube URL
        '''
        
        with self._lock:
            url = self._cur.execute('''SELECT Track.youtube_link from Track JOIN Artist JOIN Album ON
            Track.artist_id = Artist.id and Track.album_id = Album.id WHERE Track.name = ? and Album.name = ? and Artist.name = ? LIMIT 1''',
            (title,album,artist)).fetchone()
            
            # LookupError seems better
            if url == None:
                raise LookupError
            else:
                return url[0]

    def __init__(self,db_name='playlist_store.db',initialize=False):
        
        self._conn = sqlite3.connect(db_name)
        self._cur = self._conn.cursor()
        
        # Lock on our public-facing functions
        self._lock = RLock()
        
        if initialize:
            self._init_database_schema()

        #main()
if __name__ == '__main__':

    print('Unit Testing...')
    db = PlaylistDatabase('/tmp/dbtest.db',True)
    
    stations = []
    for ii in range(100):
        stations.append({
                 'name':'Station'+str(ii),
                 'site':'Station'+str(ii)+'.Site',
                 'ignoreartists':['Station'+str(ii)+'.ignoreartist1','Station'+str(ii)+'.ignoreartist2'],
                 'ignoretitles':['Station'+str(ii)+'.ignoretitle1','Station'+str(ii)+'.ignoretitle2'],
                 'playlist':'Station'+str(ii)+'.PlaylistURL'
                })
    local_station_count = len(stations)
    
    for s in stations:
        db.create_station(s['name'],s['site'],s['ignoreartists'],s['ignoretitles'],s['playlist'])
    
    # Do it again (to make sure we aren't duplicating stations
    #for s in stations:
    #    db.create_station(s['name'],s['site'],s['ignoreartists'],s['ignoretitles'],s['playlist'])
    # TODO Make a test for this
    
    
    # Make sure our data matches the DB
    db_station_count = 0
    for s in stations:
        ret_station = db.get_station_data(s['name'])
        for key in s:
            assert s[key] == ret_station[key]
        db_station_count+=1
            
    # And make sure we got every station
    assert db_station_count == local_station_count
    
    # And make sure there aren't duplicates in the DB
    assert local_station_count == len(db.get_station_data())
    
    # TODO Test insertion of songs into playlists
    
    track_id = []
    for s in stations:
        sname = s['name']
        
        # Make some tracks for this station
        tracks = []
        for ii in range(100):
            tracks.append({
                       'album':'Album'+sname+str(ii),
                       'artist':'Artist'+sname+str(ii),
                       'name':'Name'+sname+str(ii),
                       'date':datetime.datetime.fromtimestamp(ii*1000),
                       'youtube':'Youtube'+sname+str(ii),
                       })
        for t in tracks:          
            track_id.append(db.add_track_to_station_playlist(sname,t['album'],t['artist'],t['name'],t['date'],t['youtube'],commit=False))
    
    # And make sure that all of the id's line up
    '''
    for s in stations:
        sname = s['name']
        
        # Make some tracks for this station - JUST LIKE ABOVE
        tracks = []
        for ii in range(100):
            tracks.append({
                       'album':'Album'+sname+str(ii),
                       'artist':'Artist'+sname+str(ii),
                       'name':'Name'+sname+str(ii),
                       'date':datetime.datetime.fromtimestamp(ii*1000),
                       'youtube':'Youtube'+sname+str(ii),
                       })
    '''
    
    db._conn.commit()
    print('All tests passed')
            
            
        