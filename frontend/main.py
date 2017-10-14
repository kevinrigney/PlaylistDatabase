from flask import Flask, request, render_template,url_for,redirect
from PlaylistDatabase import PlaylistDatabase

#import IPython

db = PlaylistDatabase(config_file='/home/pi/PlaylistDatabase/PlaylistDatabaseConfig.ini',connect=False)

app = Flask(__name__)

def get_youtube_id(video):

    # Strip anything leading up to the ID
    video = video.split('://youtu.be/')[-1]
    video = video.split('youtube.com/watch?v=')[-1]

    # Try to strip any requests
    if '?' in video:
        video = video[0:video.find('?')]
    # Strip more junk (playlists)
    if '&' in video:
        video = video[0:video.find('&')]

    return video
        
def lookup_track_by_id(ytid):
    video = 'https://youtu.be/'+get_youtube_id(ytid)
    
    with db as cursor:
       cursor.execute('''SELECT Track.id, Track.track_name, Artist.artist_name, Album.album_name, Track.youtube_link from Track JOIN Artist JOIN Album WHERE Track.youtube_link = %s AND Track.album_id=Album.id AND Track.artist_id=Artist.id''',(video,))
       tracks = cursor.fetchall()
    
    return tracks

def get_track_last_play_stats(track_id):

    return 'Unknown'

def make_track_info_dict(track_list):
    tracks = []

    for t in track_list:

        track_id, track_name,artist_name,album_name,youtube_link = t

        this_track = {}
        
        this_track['uid'] = track_id
        this_track['title'] = track_name
        this_track['artist'] = artist_name
        this_track['album'] = album_name
        this_track['youtube_id'] = get_youtube_id(youtube_link)
        this_track['last_play'] = get_track_last_play_stats(track_id)

        #this_track['replace_url'] = url_for('replace_ytid',uid=track_id)
        this_track['uid_url'] = url_for('uid_info',uid=track_id)
        
        tracks.append(this_track)

    return tracks

def make_track_info(track,show_video):

    track_dict = make_track_info_dict(track)

    return render_template('track_info.html',tracks=track_dict,show_video=show_video) 


@app.route('/player/<string:station_id>')
def make_player(station_id):
    # Look up the station's latest track and make a player for it.

    try:
        with db:
            station = db.lookup_station_by_playlist_id(station_id)
    except LookupError:
        return render_template('empty_body.html',body='No station found with that ID')
        
    print('Station is: ' + station['name'])
    
    with db:
        latest_tracks = db.get_latest_station_tracks(station['name'],5)
    
    track_ytid = get_youtube_id(latest_tracks[0]['youtube'])
    print(track_ytid)
    player = render_template('station_player.html',video_id=track_ytid)
                
    track = lookup_track_by_id(track_ytid)
    #print(track)
    #IPython.embed()

    track_info = make_track_info(track,False)#render_template('track_info.html',tracks=latest_tracks,show_video=True)

    body = player + '\n<br>' + track_info

    return render_template('empty_body.html',body=body)


@app.route('/replace/<string:uid>',methods=['POST'])
def replace_ytid(uid):

    new_id = request.form['new_id']

    with db as cursor:
        cursor.execute('''SELECT Track.id, Track.track_name, Artist.artist_name, Album.album_name, Track.youtube_link from Track JOIN Artist JOIN Album WHERE Track.id = %s AND Track.album_id=Album.id AND Track.artist_id=Artist.id''',(uid,))
        track = cursor.fetchall()

    track_dict = make_track_info_dict(track)[0]

    new_id = 'https://youtu.be/' + get_youtube_id(new_id)

    with db as cursor:
        cursor.execute('''UPDATE Track SET youtube_link=%s WHERE Track.id=%s''',(new_id,track_dict['uid']))
        print('uid: ' + uid + ' new_id: ' + new_id)

    return redirect(track_dict['uid_url'])

@app.route('/uid/<string:uid>')
def uid_info(uid):

    with db as cursor:
        cursor.execute('''SELECT Track.id, Track.track_name, Artist.artist_name, Album.album_name, Track.youtube_link from Track JOIN Artist JOIN Album WHERE Track.id = %s AND Track.album_id=Album.id AND Track.artist_id=Artist.id''',(uid,))
        track = cursor.fetchall()

    track_dict = make_track_info_dict(track)

    #track_info = render_template('track_info.html',tracks=track_dict,youtube_id=uid,show_video=True,show_replace=True)
    #return render_template('empty_body.html',body=track_info)
    
    # Originally redirecting to track_info. This is a problem if multiple tracks
    # share the same youtube video because you don't get the video you actually wanted.
    #return redirect(url_for('track_info',ytid=track_dict[0]['youtube_id']))

    try:
        return render_template('track_info.html',tracks=track_dict,youtube_id=track_dict[0]['youtube_id'],show_video=True,show_replace=True)
    except IndexError:
        return render_template('track_info.html',tracks=track_dict,youtube_id='Track not found',show_video=True,show_replace=True)


@app.route('/track/<string:ytid>')
def track_info(ytid):

    tracks = lookup_track_by_id(ytid)
    track_dict = make_track_info_dict(tracks)

    track_info = render_template('track_info.html',tracks=track_dict,youtube_id=ytid,show_video=True,show_replace=True)

    return render_template('empty_body.html',body=track_info)

@app.route('/search',methods=['GET','POST'])
def make_track_search():
    if request.method != 'POST':
        return render_template('track_search.html')

    # Fetch tracks from a search    
    url = request.form['youtube_id']
    artist = request.form['artist']
    album = request.form['album']
    title = request.form['title']
    show_video = request.form.getlist('show_video')
    show_video = (show_video == ['on'])

    video = 'https://youtu.be/'+get_youtube_id(url)
   
    with db as cursor: 
        cursor.execute('''SELECT Track.id, Track.track_name, Artist.artist_name, Album.album_name, Track.youtube_link from Track JOIN Artist JOIN Album WHERE Track.track_name LIKE %s AND Track.youtube_link LIKE %s AND Album.album_name LIKE %s AND Artist.artist_name LIKE %s AND Track.album_id=Album.id AND Track.artist_id=Artist.id''',('%'+title+'%',video+'%','%'+album+'%','%'+artist+'%',))

        tracks = cursor.fetchall()

    track_info = make_track_info(tracks,show_video)

    return render_template('track_search_result.html',search_results=track_info,youtube_id=video)

@app.route('/latest')
def show_lastest():

    # Get the lastest track from each channel

    station_data = db.get_station_data()
    return(str(station_data))

@app.route('/')
def main():
    return redirect(url_for('make_track_search'))
