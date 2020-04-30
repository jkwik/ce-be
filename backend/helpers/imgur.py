from requests import request
import os
from dotenv import load_dotenv

load_dotenv()

ROOT_URL = 'https://imgur-apiv3.p.rapidapi.com/3'

HEADERS = {
    'x-rapidapi-host': os.getenv('X_RAPIDAPI_HOST'),
    'x-rapidapi-key': os.getenv('X_RAPIDAPI_KEY'),
    'Authorization': os.getenv('IMGUR_AUTH_HEADER')
}

ADD_IMAGE_HEADERS = {
    'x-rapidapi-host': os.getenv('X_RAPIDAPI_HOST'),
    'x-rapidapi-key': os.getenv('X_RAPIDAPI_KEY'),
    'Authorization': os.getenv('IMGUR_AUTH_HEADER'),
    'content-type': "application/x-www-form-urlencoded"
}

def createAlbum():
    """
    Create album creates an anonymous album from imgur and returns the resulting delete hash and album id
    Returns:
        - album_id
        - album_deletehash
        - status code
    """
    resp = request("POST", ROOT_URL + '/album', headers=HEADERS).json()
    
    if resp['status'] != 200:
        return None, None, resp['status']

    return resp['data']['id'], resp['data']['deletehash'],  resp['status']


def addImage(album, image):
    """
    Adds a client image to an anonymous album from imgur and returns the resulting link and status code
    Returns:
        - image link
        - status code
    """

    image_data = image.read()
    payload = {
        "album": album,
        "image": image_data
    }

    resp = request("POST", ROOT_URL + '/image', data=payload, headers=ADD_IMAGE_HEADERS).json()
    
    if resp['status'] != 200:
        return None, resp['status']

    return resp['data']['link'], resp['status']
