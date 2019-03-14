import apiai
import requests
import simplejson as json

from flask import Flask, request
from decouple import config

app = Flask(__name__)

CLIENT_ACCESS_TOKEN = config('CLIENT_ACCESS_TOKEN')
VERIFY_TOKEN = config('VERIFY_TOKEN')
PAGE_ACCESS_TOKEN = config('PAGE_ACCESS_TOKEN')

ai = apiai.ApiAI(CLIENT_ACCESS_TOKEN)

@app.route("/", methods=['GET', 'POST'])
def receive_message():

	if request.method == 'GET':
		token_sent = request.args.get('hub.verify_token')
		return verify_fb_token(token_sent)

	else:
		output = request.get_json()
		if output['object'] == 'page':
			for event in output['entry']:
				for message in event['messaging']:
					if message.get("message"):

						sender_id = message['sender']['id']
						recipient_id = message['recipient']['id']
						message_text = message['message'].get("text")
						message_to_send = parse_user_text(message_text)
						send_message_response(sender_id, message_to_send)

	return 'message process'

def verify_fb_token(token_sent):
	if token_sent == VERIFY_TOKEN:
		return request.args.get("hub.challenge")
	return 'Verified'


def parse_user_text(message_text):
	'''
	Send the message to API AI which invokes an intent
	and sends the response accordingly
	The bot response is appened with weaher data fetched from
	namaz client
	'''
	request = ai.text_request()
	request.query = message_text

	r = request.getresponse()
	response = json.loads(r.read().decode('utf-8'))
	response_status = response['status']['code']

	if response_status == 200:
		print ('Bot response '+ response['result']['fulfillment']['speech'])

		timings_namaz = ''

		input_city = response['result']['parameters'].get("geo-city")
		input_country = response['result']['parameters'].get("geo-country")

		if input_country and input_city:

			params = {'city' : input_city, 'country' : input_country}

			#extracting data from aladhan api
			resp = requests.get('http://api.aladhan.com/v1/timingsByCity', params=params)
			data = resp.json()

			fajr = str(data['data']['timings']['Fajr'])
			sunrise = str(data['data']['timings']['Sunrise'])
			dhuhr = str(data['data']['timings']['Dhuhr'])
			asr = str(data['data']['timings']['Asr'])
			maghrib = str(data['data']['timings']['Maghrib'])
			sunset = str(data['data']['timings']['Sunset'])
			isha = str(data['data']['timings']['Isha'])
			imsak = str(data['data']['timings']['Imsak'])
			midnight = str(data['data']['timings']['Midnight'])
			method = str(data['data']['meta']['method']['name'])

			timings_namaz = '\n Fajr : ' + fajr + '\n Sunrise : ' + sunrise + '\n Dhuhr : ' + dhuhr + '\n Asr : ' + asr + '\n Maghrib : ' + maghrib + '\n Sunset : ' + sunset + '\n Isha : ' + isha + '\n Imsak : ' + imsak + '\n Midnight : ' + midnight + '\n according to the calculation report of ' + method + '. '
			return (response['result']['fulfillment']['speech'] + timings_namaz)

		else:

			return response['result']['fulfillment']['speech']

	else:
		return 'Please try again'

	return 'Processed'



def send_message(sender_id, message):
	'''
	Sending response back to the user using facebook graph API
	'''
	r = requests.post("https://graph.facebook.com/v2.6/me/messages",
		params={'access_token' : PAGE_ACCESS_TOKEN},
		headers={'Content-Type' : 'application/json'},
		data=json.dumps({'recipient' : {'id' : sender_id}, 'message' : {'text': message}}))

def send_message_response(sender_id, message_text):
	delimiter = '. '
	messages = message_text.split(delimiter)
	for message in messages:
		send_message(sender_id, message)

	return 'Message Sent'

if __name__ == '__main__':
	app.run()