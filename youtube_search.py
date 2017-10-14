#!/usr/bin/env python3
import httplib2
import os
import sys

from apiclient.discovery import build
from apiclient.errors import HttpError
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage
from oauth2client.tools import argparser, run_flow


class YoutubeSearcher():
 
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

  def get_most_viewed_link(self,query,max_results=5):
    videos = self.youtube_search(query,max_results)
    try:  
      video = videos[0]
      return ('https://www.youtube.com/watch?v='+video,video)
    except IndexError:
      return ('','')

  def youtube_search(self,query,max_results=5):  
    
    # Call the search.list method to retrieve results matching the specified
    # query term.
    search_response = self.youtube.search().list(
      q=query,
      part="id",
      maxResults=max_results,
      order="relevance"
    ).execute()

    videos = []

    # Add each result to the appropriate list, and then display the lists of
    # matching videos, channels, and playlists.
    for search_result in search_response.get("items", []):
      if search_result["id"]["kind"] == "youtube#video":
        #print(search_result)
        videos.append(search_result["id"]["videoId"])

    #print("Videos:\n", "\n".join(videos), "\n")
    return videos

  def is_video_valid(self,video_id):
    # Check if a video is still valid.
    # (make sure it hasn't been deleted)

    # The part is "id" because it has a quota cost of 0
    search_response = self.youtube.videos().list(
      id=video_id,
      part="id"
    ).execute()

    return search_response['pageInfo']['totalResults'] > 0

if __name__ == "__main__":
  argparser.add_argument("--q", help="Search term", default="Google")
  argparser.add_argument("--max-results", help="Max results", default=25)
  args = argparser.parse_args()

  searcher = YoutubeSearcher()
  try:
    video = searcher.get_most_viewed_link(args.q)
    print("Video: "+video)
  except HttpError as e:
    print("An HTTP error %d occurred:\n%s" % (e.resp.status, e.content))
