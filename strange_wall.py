# strange_wall - A Twitter connected recreation of the light wall from Stranger Things.
# Author: James Barnett (james@jmbarnet.net)
# Github: jbarnett-r7

# Improvised code from:
# NeoPixel library strandtest example
# Author: Tony DiCola (tony@tonydicola.com)

import time
import datetime
import random
import twitter
import redis
import thread
from neopixel import *

#Variables that contains the user credentials to access Twitter API
ACCESS_TOKEN = "" # Twitter access token
ACCESS_TOKEN_SECRET = "" # Twitter access token secret
CONSUMER_KEY = "" # Twitter consumer key
CONSUMER_SECRET = "" # Twitter consumer secret

# LED strip configuration:
LED_COUNT      = 100     # Number of LED pixels.
LED_PIN        = 18      # GPIO pin connected to the pixels (must support PWM!).
LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
LED_DMA        = 4       # DMA channel to use for generating signal (try 5)
LED_BRIGHTNESS = 255     # Set to 0 for darkest and 255 for brightest
LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)

# Mappings for letters and colors. The colors match what is shown in Stranger Things.
# The letter mapping will need to be adjusted based on the location of the lights in relation to the letters on the wall.
# The number corresponds to the location on the strand.
ALPHABET = { ' ': [0, 'blank'], 'a': [1, 'white'], 'b': [3, 'blue'], 'c': [4, 'red'], 'd': [6, 'green'], 'e': [8, 'white'], 'f': [9, 'orange'], 'g': [11, 'red'], 'h': [13, 'blue'], 'i': [33, 'green'], 'j': [31, 'red'], 'k': [30, 'blue'], 'l': [27, 'green'], 'm': [26, 'orange'], 'n': [25, 'red'], 'o': [22, 'red'], 'p': [20, 'white'], 'q': [18, 'red'], 'r': [39, 'green'], 's': [41, 'white'], 't': [43, 'orange'], 'u': [45, 'blue'], 'v': [47, 'red'], 'w': [49, 'blue'], 'x': [50, 'orange'], 'y': [51, 'red'], 'z': [53, 'red'] }
# Map human readable colors to RGB equivalent.
COLORS = { 'red': Color(255, 0, 0), 'green': Color(0, 255, 0), 'blue': Color(0, 0, 255), 'orange': Color(255, 69, 0), 'white': Color(255, 255, 255), 'blank': Color(0, 0, 0) }
# Messages to print when no tweets are found
IDLE_MESSAGES = ["one moose", "run", "right here", "upside down", "drink your ovaltine"]
# Twitter hashtag to search for
SEARCH_QUERY = "#statxlights"

# Light up a single light.
#
# strip - the Adafruit_Neopixel object to light
# pixel - Integer representing the LED to light up
# color - RGB representation of the color to light
# wait_ms - Time in milliseconds to leave the light lit
def light_single(strip, pixel, color, wait_ms=500):
	print("lighting up pixel {0} with {1}".format(pixel, color))	
	strip.setPixelColor(pixel, color)
	strip.show()
	time.sleep(1)
	strip.setPixelColor(pixel, Color(0,0,0))
	strip.show()
	time.sleep(.5)

# Light all corresponding lights for the given word
#
# strip - the Adafruit_Neopixel object to light
# word - String of the word to illuminate
def light_word(strip, word):
	for c in word:
		random_color = COLORS[random.choice(COLORS.keys())]
		light_single(strip, ALPHABET[c][0], COLORS[ALPHABET[c][1]])
	flash_all(strip, 3)

# Light all letters in the alphabet sequentially
# Useful for debugging and troubleshooting
#
# strip - the Adafruit_Neopixel object to light
# count - Integer of the amount of LEDs to light
def flash_alphabet(strip, count):
	for i in xrange(count):
		for letter in ALPHABET.keys():
			strip.setPixelColor(ALPHABET[letter][0], COLORS[ALPHABET[letter][1]])
		strip.show()
		time.sleep(0.25)
		reset(strip)
		time.sleep(0.25)

# Flash all of the lights on and off
#
# strip - the Adafruit_Neopixel object to light
# count - Integer of the amount of LEDs to light
def flash_all(strip, count):
	for i in xrange(count):
		for p in range(strip.numPixels()):
			strip.setPixelColor(p, COLORS[random.choice(COLORS.keys())])
		strip.show()
		time.sleep(0.25)
		reset(strip)
		time.sleep(0.25)

# Clear the color from each of the LEDs, resetting them back to off
#
# strip - the Adafruit_Neopixel object to light
def reset(strip):
	for p in range(strip.numPixels()):
		strip.setPixelColor(p, Color(0, 0, 0))
	strip.show()

# Check twitter for any new tweets from the above defined hashtag
#
# twitter_api - twitter API object to use
def tweet_check_service(twitter_api):
        starting_search_results = twitter_api.GetSearch(term=SEARCH_QUERY)
	last_search_id = 0
	if starting_search_results:
		last_search_id = starting_search_results[0].id
	while True:
		try:
		        print "checking for new tweets"
	            new_search_results = twitter_api.GetSearch(term=SEARCH_QUERY, since_id=last_search_id)
			if new_search_results:
				for tweet in new_search_results:
					print("There was a new tweet, publishing {0}".format(tweet.text))
					safe_tweet = tweet.text.replace(SEARCH_QUERY, '')
					safe_tweet = strip_bad_chars(safe_tweet.lower())
					r.publish('tweet-channel', safe_tweet)
					# Quick and dirty way to make sure that the same tweet doesnt get returned in the search twice
					if tweet.id > last_search_id:
						last_search_id = tweet.id
		except Exception as err:
			print("an error occurred while checking for new tweets")
                time.sleep(10)

def strip_bad_chars(tweet):
	for ch in tweet:
		if ch not in ALPHABET.keys():
			tweet = tweet.replace(ch, '')
	return tweet


# Main program logic
if __name__ == '__main__':
	# Set up the redis pubsub
	r = redis.StrictRedis(host='localhost', port=6379, db=0)
	pubsub = r.pubsub()
	pubsub.subscribe('tweet-channel')
	# Data is returned the first time you check for messages even if nothing is there. This will prevent errors down below (aka HACK)
	pubsub.get_message()

	# Create NeoPixel object with appropriate configuration.
	strip = Adafruit_NeoPixel(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)
	# Intialize the library (must be called once before other functions).
	strip.begin()

	# Define the Twitter API object
	api = twitter.Api(consumer_key=CONSUMER_KEY, consumer_secret=CONSUMER_SECRET, access_token_key=ACCESS_TOKEN, access_token_secret=ACCESS_TOKEN_SECRET)
	print(api.VerifyCredentials())

	thread.start_new_thread( tweet_check_service, (api,) )
	last_message = datetime.datetime.now()
	print ('Press Ctrl-C to quit.')
	while True:
		try:
			print "checking for messages"
			message = pubsub.get_message()
			print message	
			if message:
				print("lighting up {0}".format(message['data']))
				reset(strip)
				light_word(strip, message['data'])
				reset(strip)
				last_message = datetime.datetime.now()
			else:
				five_min_ago = datetime.datetime.now() - datetime.timedelta(seconds = 20)
				print last_message
				print five_min_ago
				if last_message < five_min_ago:
					message = random.choice(IDLE_MESSAGES)
					print("No tweets in the last 5 min. printing {0}".format(message))
					reset(strip)
					light_word(strip, message)
					reset(strip)
					last_message = datetime.datetime.now()
		except Exception as err:
			print("an error occurred while checking for new messages or printing the message")
		message = None
		time.sleep(1)
