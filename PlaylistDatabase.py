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
            artist_id  INTEGER
        );
        
        CREATE TABLE Track (
            id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            name TEXT,
            youtube_link TEXT,
            filesystem_link TEXT, 
            album_id  INTEGER,
            artist_id  INTEGER        
            
        );
            
        CREATE TABLE Station (
            id  INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT UNIQUE,
            name TEXT,
            web_address TEXT,
            last_update INTEGER UNSIGNED,
            ignore_artists TEXT,
            ignore_titles TEXT,
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
        if ' ' in name:
            raise ValueError('Spaces are not allowed in a playlist name')
    
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
            artist_id = self._cur.execute('SELECT id FROM ARTIST where name=?',(name,)).fetchone()[0]
            #print(artist_id)
            return artist_id
    
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
    
    def create_station(self,station_name,web_address,ignore_artists='',ignore_titles='',last_update=0,get_id=True,commit=True):
        '''
        Create a station and associated playlist
        '''
        
        with self._lock:
            # Create a new playlist to use for this station
            playlist_name = self._make_playlist(station_name)
            #print(playlist_name)
            self._cur.execute('''
            INSERT INTO Station(name,web_address,last_update,ignore_artists,ignore_titles,playlist_id)
            VALUES ( ?, ?, ?, ?, ?, ? )''', (station_name,web_address,last_update,ignore_artists,ignore_titles,playlist_name)
            )
            
            if commit:
                self._conn.commit()
            
            if get_id:
                station_id = self._cur.execute('''
                SELECT Station.id FROM Station WHERE
                name = ? and web_address = ? and last_update = ? and ignore_artists = ? and ignore_titles = ? and playlist_id = ?'''
                ,(station_name,web_address,last_update,ignore_artists,ignore_titles,playlist_name)).fetchone()[0]
                return station_id
        
    
       
    def add_track_to_station_playlist(self,station_name,artist,track,date,youtube_link='',commit = True):
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
            # Make a track
            track_id = self._make_track(track,0,artist_id,youtube_link,commit=commit)
            
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
            
            self._cur.execute('SELECT Track.name, Artist.name, '+playlist+'.play_time, Track.youtube_link FROM ' +playlist + ''' JOIN Artist JOIN Track
            ON ''' + playlist + '''.track_id = Track.id and Track.artist_id = Artist.id
            ORDER BY ''' + playlist +'.play_time DESC LIMIT ?',(num_tracks,))
            data = self._cur.fetchall()
            return data

    def __init__(self,initialize=False):
        
        self._conn = sqlite3.connect('playlist_store.db')
        self._cur = self._conn.cursor()
        
        # Lock on our public-facing functions
        self._lock = RLock()
        
        if initialize:
            self._init_database_schema()

        #main()