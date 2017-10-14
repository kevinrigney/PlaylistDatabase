#!/usr/bin/env python3

import httplib2
import os
import sys

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow

class YoutubePlaylist():
  # The CLIENT_SECRETS_FILE variable specifies the name of a file that contains
  # the OAuth 2.0 information for this application, including its client_id and
  # client_secret. You can acquire an OAuth 2.0 client ID and client secret from
  # the Google Developers Console at
  # https://console.developers.google.com/.
  # Please ensure that you have enabled the YouTube Data API for your project.
  # For more information about using OAuth2 to access the YouTube Data API, see:
  #   https://developers.google.com/youtube/v3/guides/authentication
  # For more information about the client_secrets.json file format, see:
  #   https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
  CLIENT_SECRETS_FILE = "client_secrets.json"

  # This variable defines a message to display if the CLIENT_SECRETS_FILE is
  # missing.
  MISSING_CLIENT_SECRETS_MESSAGE = """
  WARNING: Please configure OAuth 2.0

  To make this sample run you will need to populate the client_secrets.json file
  found at:

     %s

  with information from the Developers Console
  https://console.developers.google.com/

  For more information about the client_secrets.json file format, please visit:
  https://developers.google.com/api-client-library/python/guide/aaa_client_secrets
  """ % os.path.abspath(os.path.join(os.path.dirname(__file__),
                                     CLIENT_SECRETS_FILE))

  # This OAuth 2.0 access scope allows for full read/write access to the
  # authenticated user's account.
  YOUTUBE_READ_WRITE_SCOPE = "https://www.googleapis.com/auth/youtube"
  YOUTUBE_API_SERVICE_NAME = "youtube"
  YOUTUBE_API_VERSION = "v3"
  
  def __init__(self):
    flow = flow_from_clientsecrets(self.CLIENT_SECRETS_FILE,
      message=self.MISSING_CLIENT_SECRETS_MESSAGE,
      scope=self.YOUTUBE_READ_WRITE_SCOPE)

    storage = Storage("ytpl-oauth2.json")
    credentials = storage.get()

    if credentials is None or credentials.invalid:
      flags = argparser.parse_args()
      credentials = run_flow(flow, storage, flags)

    self.youtube = build(self.YOUTUBE_API_SERVICE_NAME, self.YOUTUBE_API_VERSION,
      http=credentials.authorize(httplib2.Http()))

  def create_playlist(self,title):
    # This code creates a new, private playlist in the authorized user's channel.
    playlists_insert_response = self.youtube.playlists().insert(
      part="snippet,status",
      body=dict(
        snippet=dict(
          title=title,
          description="A private playlist created with the YouTube API v3"
        ),
        status=dict(
          privacyStatus="private"
        )
      )
    ).execute()   

    print("New playlist id: %s" % playlists_insert_response["id"])
    return playlists_insert_response['id']

  def add_video_to_playlist(self,video,playlist):
    song_insert_response = self.youtube.playlistItems().insert(
      part='snippet,status',
      body=dict(
        snippet=dict(
          playlistId=playlist,
          resourceId=dict(
            kind='youtube#video',
            videoId=video
          ),
          position=0
        )
      )
    )
    song_insert_response.execute()
    return song_insert_response

  def remove_last_videos_from_playlist(self,playlist,num_to_delete=100):
    # First we need to figure out how many videos we need to seek through
    # Untill we start deleting
    maxResults=50
    request = self.youtube.playlistItems().list(
      playlistId=playlist,
      part='id',
      maxResults=maxResults
    )
    
    stillRunning = True
    videoList = []
    # Because we don't know how many responses we will get we need to
    # keep track of each response we get. Once we run out of responses
    # we will then go through it and remove them
    while request:
      response = request.execute()
      videos = response['items']
      #nextToken = response['nextPageToken']

      for v in videos:
        videoList.append(v['id'])

      request = self.youtube.playlistItems().list_next(
        request, response)
      


    # Reverse the list. We've been appending to the end so we want
    # to start at the end
    videoList.reverse()

    # And keep the num_to_delete
    videoList = videoList[:num_to_delete]

    # Make the requests. We're going to delete 'em
    for v in videoList:
      self.youtube.playlistItems().delete(
        id=v
      ).execute()    

if __name__ == '__main__':
  ytpl = YoutubePlaylist()
