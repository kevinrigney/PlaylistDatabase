#!/usr/bin/env python3

import mysql.connector as mysql
import datetime

from math import floor
from threading import RLock
from configparser import ConfigParser

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
        
        print('Dropping...')
        try:
            self._cur.execute('drop database PlaylistDB')
        except mysql.errors.DatabaseError:
            #print('No database exists.')
            pass
            
        self._cur.execute('create database PlaylistDB')
        self._cur.execute('use PlaylistDB')

        
        self._cur.execute('''CREATE TABLE IF NOT EXISTS Artist (
            id  INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
            artist_name VARCHAR(256) UNIQUE NOT NULL,
        
            PRIMARY KEY (id),
            KEY (artist_name)
        )''')
        
        self._cur.execute('''CREATE TABLE IF NOT EXISTS Album (
            id  INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
            album_name VARCHAR(256) NOT NULL,
            artist_id  INTEGER NOT NULL,
        
            PRIMARY KEY (id),
            FOREIGN KEY (artist_id) REFERENCES Artist(id) ON UPDATE CASCADE,
            UNIQUE(album_name,artist_id)
        )''')
        
        self._cur.execute('''CREATE TABLE IF NOT EXISTS Track (
            id  INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
            track_name VARCHAR(256) NOT NULL,
            youtube_link TEXT,
            filesystem_link TEXT, 
            album_id  INTEGER NOT NULL,
            artist_id  INTEGER NOT NULL,
        
            PRIMARY KEY (id),
            FOREIGN KEY (album_id) REFERENCES Album(id)  ON UPDATE CASCADE,
            FOREIGN KEY (artist_id) REFERENCES Artist(id) ON UPDATE CASCADE ,
            KEY (track_name),
            UNIQUE(track_name,album_id,artist_id)            
        )''')
        
        self._cur.execute('''CREATE TABLE IF NOT EXISTS Station (
            id  INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
            station_name VARCHAR(256) NOT NULL UNIQUE,
            web_address TEXT,
            ignore_artists TEXT,
            ignore_titles TEXT,
            youtube_playlist_id TEXT,
            active BOOL NOT NULL,
        
            PRIMARY KEY (id),
            KEY (station_name)
        )''')
        
        self._cur.execute('''CREATE TABLE IF NOT EXISTS Playlist (
            id INTEGER NOT NULL AUTO_INCREMENT UNIQUE,
            track_id INTEGER NOT NULL,
            station_id INTEGER NOT NULL,
            play_time DATETIME NOT NULL,
        
            PRIMARY KEY (id),
            KEY (station_id),
            FOREIGN KEY (track_id) REFERENCES Track(id) ON UPDATE CASCADE,
            FOREIGN KEY (station_id) REFERENCES Station(id) ON UPDATE CASCADE,
            UNIQUE(track_id,station_id,play_time)
        )''')           
        
        
        if commit:
            self._conn.commit()
        
        
    def _get_all_stations(self):
        
        self._cur.execute('''SELECT * from Station''')
        stations = self._cur.fetchall()
        
        return stations
    
    def _get_station_id_from_name(self,name):
               
        self._cur.execute('''SELECT Station.id from Station where Station.station_name = %s''',(name,))
        
        try:
            station_id = self._cur.fetchone()[0]
        except TypeError:
            # LookupError seems better here
            raise LookupError('Station: ' + str(name) + ' could not be found.')
                
        #print('station_id: ' + str(station_id))
        return station_id
    
    def _make_artist(self,name,get_id=True,commit=True):
        '''
        Create an artist in the table.
        For artists we only have a name.
        '''
        
        self._cur.execute('''
        INSERT IGNORE INTO Artist(artist_name)
        VALUES ( %s )''', (name,)
        )
        
        # If they're doing a bunch of makes they might not want
        # to commit after each one
        if commit:
            self._conn.commit()
        if get_id:
            self._cur.execute('''
            SELECT Artist.id FROM Artist WHERE
            Artist.artist_name=%s''',(name,))
            return self._cur.fetchone()[0]        
        
    
    def _make_album(self,artist_id,album,get_id=True,commit=True):
        '''
        Create an album in the table.
        '''
        
        # Get the artist id
        
        self._cur.execute('''
        INSERT IGNORE INTO Album(album_name,artist_id)
        VALUES ( %s, %s )''', (album,artist_id)
        )
        
        # If they're doing a bunch of makes they might not want
        # to commit after each one
        if commit:
            self._conn.commit()
        
        if get_id:
            self._cur.execute('''
            SELECT Album.id FROM Album WHERE
            Album.album_name=%s AND Album.artist_id=%s
            ''',(album,artist_id))
            return self._cur.fetchone()[0]        
        
        
    def _make_track(self,name,album_id,artist_id,yt_link='',fs_link='',get_id=True,commit=True):
        '''
        Given a track name, ablum ID,and an artist ID, make a track in the
        'Track' table. Optionally a youtube URL or filesystem location can also be specified.
        '''
        
        # We're doing a 'OR REPLACE' because maybe we're updating a track with a 
        # new youtube or filesystem link.
        self._cur.execute('''
        INSERT INTO Track (track_name,youtube_link,filesystem_link,album_id,artist_id)
        VALUES( %s, %s, %s, %s, %s ) ON DUPLICATE KEY UPDATE
        youtube_link=VALUES(youtube_link),filesystem_link=VALUES(filesystem_link)''',
        (name,yt_link,fs_link,album_id,artist_id)
        )
        
        # If they're doing a bunch of makes they might not want
        # to commit after each one
        if commit:
            self._conn.commit()
        
        if get_id:
            self._cur.execute('''
            SELECT Track.id FROM Track WHERE
            Track.track_name=%s AND 
            Track.youtube_link=%s AND 
            Track.filesystem_link=%s AND
            Track.album_id=%s AND
            Track.artist_id=%s''',(name,yt_link,fs_link,album_id,artist_id))
            return self._cur.fetchone()[0]        

    def _add_playlist_entry(self,station_id,track_id,play_time,commit=True):
        '''
        Given a station ID, track ID, and a play time (a string date)
        create a new row in the corresponding playlist table
        '''
        # No 'INSERT OR REPLACE INTO' because this should be unique based on the play times
        self._cur.execute('''
        INSERT INTO Playlist (track_id,station_id,play_time)
        VALUES (%s, %s, %s)
        ''', (track_id,station_id,play_time)
        )
                
        # If they're doing a bunch of makes they might not want
        # to commit after each one
        if commit:
            self._conn.commit()
        
        return self._cur.lastrowid
    
    #
    # BEGIN PUBLIC FUNCTIONS
    #
    
    def create_station(self,station_name,web_address,ignore_artists=[],ignore_titles=[],youtube_playlist_id='',get_id=True,commit=True):
        '''
        Create a station and associated playlist
        '''
        
        with self._lock:
            # Create a new playlist to use for this station
            #playlist_name = self._make_playlist(station_name)
            
            # v2 will use a different format for this... Probably another table?
            ignore_artists = str(ignore_artists)
            ignore_titles = str(ignore_titles)
            #print(playlist_name)
            self._cur.execute('''
            INSERT IGNORE INTO Station(station_name,web_address,ignore_artists,ignore_titles,youtube_playlist_id,active)
            VALUES ( %s, %s, %s, %s, %s, %s )''', (station_name,web_address,ignore_artists,ignore_titles,youtube_playlist_id,'true')
            )
            
            if commit:
                self._conn.commit()
            
            if get_id:
                self._cur.execute('''
                SELECT Station.id FROM Station WHERE
                station_name=%s''',(station_name,))              
            
                return self._cur.fetchone()[0]        

       
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
            
            # Loop up the station's ID
            station_id = self._get_station_id_from_name(station_name)
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
            #date_ms = int(floor(date.microsecond/1000))
            date = date.strftime('%Y-%m-%d %H:%M:%S.%f')
            
            # Now that we have the data we can make an entry
            return self._add_playlist_entry(station_id,track_id,date,commit=commit)

    
    def get_latest_station_tracks(self,station_name,num_tracks=1):
        '''
        Get a number of tracks from a station. Order from newest
        to oldest.
        '''
        with self._lock:
            station_id = self._get_station_id_from_name(station_name)
            
            self._cur.execute('''SELECT Track.track_name, Artist.artist_name, Playlist.play_time, Track.youtube_link, Album.album_name, Track.filesystem_link FROM Playlist
            JOIN Artist JOIN Track JOIN Album ON 
            Playlist.track_id = Track.id and Track.artist_id = Artist.id and Track.album_id = Album.id WHERE Playlist.station_id = %s
            ORDER BY Playlist.play_time DESC LIMIT %s''',(station_id,num_tracks))
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
                id,name,web_address,ignore_artists,ignore_titles,youtube_playlist_id,active = s
                
                if station is not None:
                    if name != station:
                        continue
                
                channel_dict = {}
    
                channel_dict['site'] = web_address
                exec("channel_dict['ignoreartists'] = "+ ignore_artists)
                exec("channel_dict['ignoretitles'] = "+ ignore_titles)
                channel_dict['name'] = name
                channel_dict['playlist'] = youtube_playlist_id

                if (active == 1):
                    channel_dict['active'] = True
                else:
                    channel_dict['active'] = False
 
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
            self._cur.execute('''SELECT Track.youtube_link from Track JOIN Artist JOIN Album ON
            Track.artist_id = Artist.id and Track.album_id = Album.id WHERE Track.track_name = %s and Album.album_name = %s and Artist.artist_name = %s LIMIT 1''',
            (title,album,artist))
            
            url = self._cur.fetchone()
            
            # LookupError seems better
            if url == None:
                raise LookupError
            else:
                return url[0]

    def lookup_station_by_playlist_id(self,playlist_id):
        with self._lock:
            self._cur.execute('''SELECT * from Station where Station.youtube_playlist_id = %s''',(playlist_id,))
            station = self._cur.fetchone()

            if station == None:
                raise LookupError
            else:
                id, name, addr, i_a, i_t, pl_id, active = station
                station_dict = {}
                station_dict['id'] = id
                station_dict['name'] = name
                station_dict['ignore_artists'] = i_a
                station_dict['ignore_titles'] = i_t
                station_dict['playlist_id'] = pl_id
                station_dict['active'] = active

                return station_dict

    def __init__(self,user='root',password='password',host='127.0.0.1',initialize=False,config_file=None,connect=True):
        
        # Config contains the config file, an INI format
        config = ConfigParser()
        if config_file is not None:
            config.read(config_file)            
            # Use the values here instead of the available kwargs
            self._user = config['database']['user']
            self._password = config['database']['password']
            self._host = config['database']['host']
        

        self._conn = mysql.connect(user=self._user,password=self._password,host=self._host)
        
        self._cur = self._conn.cursor()
        
        # Check if the DB exists
        try:
            self._cur.execute('USE PlaylistDB;')
        except mysql.errors.ProgrammingError:
            print('The database does not exist. Initializing')
            initialize = True
    
        # Lock on our public-facing functions
        self._lock = RLock()
        
        if initialize:
            self._init_database_schema()
        
        if not connect:
            # Then close the connection because they will use "with" statements
            self._cur = None
            self._conn.close()
            self._conn = None

        #main()


    def __enter__(self):
        self._conn = mysql.connect(user=self._user,password=self._password,host=self._host)
        self._cur = self._conn.cursor()
        self._cur.execute('USE PlaylistDB;')
        
        return self._cur

    def __exit__(self,exc_type,exc_value,exc_traceback):

        self._cur = None
        self._conn.commit()
        self._conn.close()
        self._conn = None


if __name__ == '__main__':

    print('Unit Testing...')
    db = PlaylistDatabase(initialize=True)
    
    stations = []
    for ii in range(10):
        stations.append({
                 'name':'Station'+str(ii),
                 'site':'Station'+str(ii)+'.Site',
                 'ignoreartists':['Station'+str(ii)+'.ignoreartist1','Station'+str(ii)+'.ignoreartist2'],
                 'ignoretitles':['Station'+str(ii)+'.ignoretitle1','Station'+str(ii)+'.ignoretitle2'],
                 'playlist':'Station'+str(ii)+'.PlaylistURL'
                })
    local_station_count = len(stations)
    
    for s in stations:
        print('Inserting... ',end='')
        id = db.create_station(s['name'],s['site'],s['ignoreartists'],s['ignoretitles'],s['playlist'])
        print('Station id:',id)
    
    # Do it again (to make sure we aren't duplicating stations
    for s in stations:
        print('Inserting... ',end='')
        id = db.create_station(s['name'],s['site'],s['ignoreartists'],s['ignoretitles'],s['playlist'])
        print('Station id:',id)
    # TODO Make a test for this
    
    assert local_station_count == len(db.get_station_data())
    
    print('Verifying station data... ',end='')
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
    print('Done.')
    
    # Make some tracks that will be overwritten by the next loop where we add tracks
    # to a playlist
    sname = stations[0]['name']
    tracks = []
    print('Making tracks... ')#,end='')
    for ii in range(100):
        tracks.append({
                   'album':'Album'+sname+str(ii),
                   'artist':'Artist'+sname+str(ii),
                   'name':'Name'+sname+str(ii),
                   'date':datetime.datetime.fromtimestamp(ii*1000),
                   'youtube':'Youtube'+sname+str(ii),
                   })
        for t in tracks:        
            
            # Make (or don't) the artist
            artist_id = db._make_artist(t['artist'],commit=False)
            
            # Make (or don't) the album
            album_id = db._make_album(artist_id,t['album'],commit=False)
            
            # Make (or don't) a track            
            track_id = db._make_track(t['name'],album_id,artist_id,t['youtube'],commit=False)
            
        #id = db.add_track_to_station_playlist(sname,t['album'],t['artist'],t['name'],t['date'],t['youtube'],commit=False)
        #track_id.append(id)
    print('Done.')
    
    # Test insertion of songs into playlists   
    for s in stations:
        sname = s['name']
        print('Adding tracks to station',sname)
        # Make some tracks for this station
        tracks = []
        for ii in range(10):
            tracks.append({
                       'album':'Album'+sname+str(ii),
                       'artist':'Artist'+sname+str(ii),
                       'name':'Name'+sname+str(ii),
                       'date':datetime.datetime.fromtimestamp(ii*1000),
                       'youtube':'Youtube'+sname+str(ii),
                       })
        for t in tracks:          
            id = db.add_track_to_station_playlist(sname,t['album'],t['artist'],t['name'],t['date'],t['youtube'],commit=False)
            #track_id.append(id)
    db._conn.commit()

    
    # And make sure that all of the id's line up
    
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
    
    
    print('All tests passed')
            
            
        
