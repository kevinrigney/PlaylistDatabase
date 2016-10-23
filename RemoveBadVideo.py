#!/usr/bin/env python3

from PlaylistDatabase import PlaylistDatabase

db = PlaylistDatabase(config_file='PlaylistDatabaseConfig.ini')

video = input('Enter the video ID: ')
if video.startswith('https://youtu.be/'):
    pass
elif video.startswith('https://www.youtube.com/watch?v='):
    video.replace('https://www.youtube.com/watch?v=','https://youtu.be/')
else:
    video = 'https://youtu.be/'+video
db._cur.execute('''SELECT Track.id, Track.track_name, Artist.artist_name, Album.album_name, Track.artist_id, Track.album_id, Track.youtube_link from Track JOIN Artist JOIN Album WHERE Track.youtube_link=%s AND Track.album_id=Album.id AND Track.artist_id=Artist.id''',(video,))

track = db._cur.fetchall()

if len(track) > 1:
    print('\nWARNING: More than one track has the same video.\n')

    for ii,t in enumerate(track):
        print

        track_id,track_name,artist_name,album_name,artist_id,album_id,youtube_link = track[ii]

        print('Track '+str(ii)+' is: ',track_id,track_name,artist_name,album_name,artist_id,album_id, youtube_link)

    ii=int(input('\nWhat track do you want to use? '))

else:
    ii=0

track_id,track_name,artist_name,album_name,artist_id,album_id,youtube_link = track[ii]

print('Track '+str(ii)+' is: ',track_id,track_name,artist_name,album_name,artist_id,album_id, youtube_link)

yesorno = input('Do you want to delete this track and add it to the ignore lists? (yes/no): ')

if yesorno.lower()=='yes':

    db._cur.execute('''SELECT Playlist.*,Station.* FROM Playlist JOIN Station WHERE Playlist.track_id=%s AND Playlist.station_id=Station.id''',(track_id,))
    
    stations = db._cur.fetchall()
    
    unique_station = {}
    
    for s in stations:
        playlist_entry_id, track_id, pl_station_id,playtime,station_id,station_name,station_url,ignore_artists,ignore_titles,playlist_url = s
            
        unique_station[station_id] = (station_name,station_url,ignore_artists,ignore_titles,playlist_url)
        
    print(unique_station)
    
    for id in unique_station:
        exec('ignore_artists = ' + unique_station[id][2])
        exec('ignore_titles = ' + unique_station[id][3])
        if artist_name not in ignore_artists:
            ignore_artists.append(artist_name)
        if track_name not in ignore_titles:
            ignore_titles.append(track_name)
        unique_station[id] = unique_station[id][0],unique_station[id][1],str(ignore_artists),str(ignore_titles),unique_station[id][4]
        db._cur.execute('''
        UPDATE Station
        SET ignore_artists=%s, ignore_titles=%s
        WHERE Station.id=%s
        ''',(str(ignore_artists),str(ignore_titles), id))
        db._conn.commit()
            
    print(unique_station)
    
    
    # Get all tracks with the matching artist id and album id
    all_tracks = []
    db._cur.execute('''SELECT Track.id FROM Track WHERE Track.album_id=%s AND Track.artist_id=%s''',(album_id,artist_id))
    for id in db._cur.fetchall():
        if id not in all_tracks:
            all_tracks.append(id[0])

    for id in all_tracks:
        # Remove the station entries
        db._cur.execute('''DELETE FROM Playlist WHERE Playlist.track_id=%s''',(id,))
        # Remove the track entries
        db._cur.execute('''DELETE FROM Track WHERE Track.id=%s''',(id,))
    
    # Remove the album entries
    db._cur.execute('''DELETE FROM Album WHERE Album.id=%s''',(album_id,))
    
    # Remove the artist entries
    db._cur.execute('''DELETE FROM Artist WHERE Artist.id=%s''',(artist_id,))
    
    db._conn.commit()
    #Tracks = db._cur.fetchall()
else:
    yesorno = input('Do you want to update the youtube URL for this track? (yes/no): ')
    if yesorno.lower() == 'yes':
        url = input('Enter the new youtube url: ')
        url = url.replace('https://www.youtube.com/watch?v=','https://youtu.be/')                        

        db._cur.execute('''
        UPDATE Track
        SET youtube_link=%s
        WHERE Track.id=%s
        ''',(url,track_id))
        db._conn.commit()
    else:
        print('Not modifying database.')
