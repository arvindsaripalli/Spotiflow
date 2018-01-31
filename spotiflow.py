import spotipy.util as util
import requests
import spotipy
import pprint
import sys
import numpy as np


def create_new_playlist(sp, username, name, tracklist):
    """
    Creates a new playlist from a tracklist.

    :param sp: Spotify auth object
    :param username: Spotify username.
    :param name: Name of the playlist name to be created.
    :param tracklist: List of track ids to be added to the playlist.
    """

    # Create empty playlist.
    sp.user_playlist_create(username, name, True)

    # Get user's playlists.
    playlists_result = sp.user_playlists(username)
    new_playlist_id = None

    # Look for new playlist.
    for playlist in playlists_result['items']:
        if playlist['name'] == name:
            new_playlist_id = playlist['id']

    # Add tracks to new playlist.
    if new_playlist_id is not None:
        sp.user_playlist_add_tracks(username, new_playlist_id, tracklist)

    print(name, " created!\n")


def order_tracks(playlist, track_features):
    """
    Returns a list of track ids that are sorted in order of closeness.

    :param playlist: Dictionary of track names and ids.
    :param track_features: Dicttionary of track features.
    :return: (list) A list of track_ids ordered by closeness.
    """

    # Solution and remaining lists.
    remaining = playlist.copy()
    solution = []

    # Get starting track, add it to the solution, and remove it
    # from remaining tracks.
    current = list(remaining.keys())[0]
    del remaining[current]
    solution.append(current)

    # Iterate through the remaining elements.
    for i in range(len(remaining)):
        min_distance = -1
        min_track = None

        # Find the min track
        for track in remaining:
            distance = get_distance(np.array(track_features[current]),
                                    np.array(track_features[track]))
            if min_distance == -1 or min_distance > distance:
                min_distance = distance
                min_track = track

        # Update current, add to solutions, and remove from remaining.
        current = min_track
        solution.append(current)
        del remaining[current]
    return solution


def get_distance(a, b):
    """
    Returns the euclidean distance between two track features lists.
    """
    return np.linalg.norm(a - b)


def remove_query_spaces(q):
    """
    Replaces spaces with + in a query.

    :param q: Query such as an artist or track name.
    :return: The query with + in place of spaces.
    """
    return '+'.join(q.split(' '))


def get_genres(track, artist, keys):
    """
    Returns a genre for the track if a genre for it is found in the Last.fm API.

    :param track: Track name.
    :param artist: Artist name.
    :param keys: API keys for Last.fm API.
    :return: (str) the genre of the track if available.
    """
    genres_list = ['electronic', 'jazz', 'hip hop', 'pop', 'rock',
                   'alternative rock', 'metal', 'indie']

    # Format artist and track name and create url from them
    artist = remove_query_spaces(artist)
    track = remove_query_spaces(track)
    url = "http://ws.audioscrobbler.com/2.0/?method=track.getInfo&api_key=" \
          + keys[2] + "&artist=" + artist + "&track=" + track + "&format=json"

    # Last.fm GET request and parsed to json.
    response = requests.get(url).json()

    # Find all Last.fm tags for the song.
    tags = []
    if 'track' in response:
        for tag in response['track']['toptags']['tag']:
            tags.append(tag['name'])

    # Returns the first genre that is matched by a tag and the genre
    # filter.
    for tag in tags:
        for genre in genres_list:
            if tag.lower() in genre or genre in tag.lower():
                return genre

    return None


def get_track_features(track_id, sp):
    """
    Returns the features of a given track if features for the track exist.

    :param track_id: The spotify id of the track.
    :param sp: Spotify auth object.
    :return: (list) Track feature names mapped to their values.
    """

    feature_filter = ['danceability', 'energy', 'instrumentalness', 'loudness', 'speechiness', 'tempo', 'valence']
    return_features = []

    # Get features from this track.
    features = sp.audio_features([track_id])

    if None in features:
        return []

    # Add desired features of track.
    for feature in features[0]:
        if feature in feature_filter:
            return_features.append(features[0][feature])

    return return_features


def pick_playlist(sp, username):
    """
    Prompts for playlist to choose and returns the playlist name and
    id for that playlist.

    :param sp: Spotipy auth object.
    :param username: Spotify username.
    :return: tuple (playlist, user_id)
        WHERE
        (list) playlist is the chosen playlist name and id.
        (str) user_id is the id of the playlist owner.
    """
    # Grab user playlists created, followed, public, private, etc.
    playlists_result = sp.user_playlists(username)
    playlists = []
    user_ids = []
    playlist_count = 0

    # Displays prompt.
    print("Pick a playlist: ")
    for playlist in playlists_result['items']:
        playlist_count += 1

        # Add to playlists name and ids
        playlist_id = playlist['id']
        name = playlist['name']
        playlists.append([name, playlist_id])

        # Record owner of the playlist
        user_ids.append(playlist['owner']['id'])

        print(str(playlist_count) + " " + name)

    # Check if choice is valid
    chosen_playlist = int(input())
    if chosen_playlist > playlist_count or chosen_playlist < 1:
        print("That is not a valid choice. Please try again.")
        sys.exit(1)

    return playlists[chosen_playlist - 1], user_ids[chosen_playlist - 1]


def user_login(scope):
    """
    Logs into a user's account.

    :param scope: The API use permissions
    :return: tuple (token, user, keys)
        WHERE
        token is the API token.
        username is the spotify username.
        keys is the list of API keys.
    """

    # Get API keys
    read_key = open("keys.txt", 'r')
    keys = read_key.read().split(',')

    # Parse command line arguments.
    if len(sys.argv) > 1:
        username = sys.argv[1]
    else:
        print("Usage: python %s [username]" % (sys.argv[0],))
        sys.exit(1)

    # Get API token with spotipy.
    token = util.prompt_for_user_token(username, scope,
                                       client_id=keys[0].rstrip(),
                                       client_secret=keys[1].rstrip(),
                                       redirect_uri='http://localhost:8888/callback')
    return token, username, keys


def main():
    pp = pprint.PrettyPrinter(indent=2)

    # Read permissions for Spotify API.
    scope = 'user-library-read playlist-modify-public'

    # Get user login information.
    token, username, keys = user_login(scope)

    if token:
        sp = spotipy.Spotify(auth=token)
        playlist = {}
        track_features = {}
        track_genre = {}

        # Prompt user for playlist selection.
        playlist_id, playlist_owner_id = pick_playlist(sp, username)
        playlist_name = playlist_id[0]
        playlist_id = playlist_id[1]

        # Get playlist information from id.
        playlist_result = sp.user_playlist_tracks(playlist_owner_id, playlist_id=playlist_id)
        playlist_result = playlist_result['items']
        print("Gathering features and genre...")

        # Add tracks to playlist dictionary and get features
        for track in playlist_result:
            # Gather the track and artist name, and track id for each track.
            track_id = track['track']['id']
            name = track['track']['name']
            artist = track['track']['artists'][0]['name']

            # Add track to this playlist.
            playlist[track_id] = [name, artist]

            # Gather features for this track.
            track_features[track_id] = get_track_features(track_id, sp)

            # Get the genre of the track.
            # track_genre[track_id] = get_genres(name, artist, keys)

        print("Done\n")

        # Order the tracks in the playlist.
        new_tracklist = order_tracks(playlist, track_features)

        # Prompt for creation of new playlist.
        new_playlist_name = playlist_name + " - Improved"
        should_create = input("Creating new public playlist '{}', continue? (y/n)  ".format(new_playlist_name))

        # Create playlist from new tracklist.
        if should_create.lower() != "n" and should_create.lower() != "no":
            create_new_playlist(sp, username, new_playlist_name, new_tracklist)

        print("Thanks for using Spotiflow!")


if __name__ == '__main__':
    main()
