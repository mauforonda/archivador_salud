#!/usr/bin/env python3
import twitter
import datetime as dt
import json
import internetarchive as ia
import requests
from io import BytesIO

def auth():
  with open('credentials.json', 'r') as f:
    creds = json.load(f)
    twitter_api = twitter.Api(consumer_key=creds['twitter']['consumer_key'],
                              consumer_secret=creds['twitter']['consumer_secret'],
                              access_token_key=creds['twitter']['access_token_key'],
                              access_token_secret=creds['twitter']['access_token_secret'],
                              tweet_mode='extended')
    ia_cred = [creds['internetarchive']['access'], creds['internetarchive']['secret']]
    return [twitter_api, ia_cred]

def get_images(timeline):
  tweets = []
  for tweet in timeline:
    images = []
    if tweet._json.__contains__('extended_entities'):
      if tweet._json['extended_entities'].__contains__('media'):
        images = [img['media_url_https'] for img in tweet._json['extended_entities']['media'] if img['type'] == 'photo']
    if len(images) != 0:
      created_at = dt.datetime.strptime(tweet._json['created_at'], '%a %b %d %H:%M:%S %z %Y').astimezone(dt.timezone(-dt.timedelta(hours=4)))
      tweets.append([created_at, images])
  return tweets

def save_last(timeline):
  with open('last', 'w+') as f:
    f.write(str(timeline[0].id))

def upload(access, secret, image_name, extension, image, tweet_date, user):
  u = ia.upload(image_name,
                {'{i}.{e}'.format(i=image_name, e=extension): image},
                metadata = {'title': image_name, 'mediatype': 'image', 'date': tweet_date, 'creator': user['name'], 'source': 'https://twitter.com/{}'.format(user['twitter_handle'])},
                access_key=access,
                secret_key=secret)
  return u

def retry(access, secret, failed):
  if len(failed) > 0:
    print('retry for {} items'.format(len(failed)))
    for i in failed:
      u = upload(access, secret, i[0], i[1], i[2])

def archive(auth_ia, user, tweets):
  failed = []
  access, secret = auth_ia
  for ntweet, tweet in enumerate(tweets):
    tweet_name = tweet[0].strftime('{}_%Y-%m-%d_%H-%M-%S'.format(user['twitter_handle']))
    tweet_date = tweet[0].strftime('%Y-%m-%d')
    print(str(ntweet) + ": " + tweet_name)
    for n, url in enumerate(tweet[1]):
      extension = url.split('.')[-1]
      image_name = '{f}_{n}'.format(f=tweet_name,n=n)
      image = BytesIO(requests.get(url).content)
      print('image downloaded')
      u = upload(access, secret, image_name, extension, image, tweet_date, user)
      if u[0].status_code == 200:
        print('uploaded')
      else:
        print('failed')
        failed.append([image_name, extension, image])
  retry(access, secret, failed)

def get_last():
  try:
    with open('last', 'r') as f:
      return f.read().strip()
  except FileNotFoundError:
    return 'Nah'
    
def get_tweets(api, user, since_last):
  last = get_last()
  if since_last == True or last != 'Nah':
    timeline = api.GetUserTimeline(screen_name=user, since_id=last, count=200)
  else:
    timeline = api.GetUserTimeline(screen_name=user, count=200)
  if len(timeline) == 0:
    tweets = 'Nah'
    print('no new tweets since last time')
  else:
    print('tweets downloaded')
    tweets = get_images(timeline)
    print('{} tweets with images'.format(len(tweets)))
    save_last(timeline)
  return tweets
  
def tweet_archiver(institution):
  api, auth_ia = auth()
  tweets = get_tweets(api, institution['twitter_handle'], True)
  if tweets != 'Nah':
    archive(auth_ia, institution, tweets)

institution = {'twitter_handle': 'minsaludbolivia',
               'name': 'Ministerio de Salud de Bolivia'}

tweet_archiver(institution)
