import os
import requests
def send_simple_message():
  	return requests.post(
  		"https://api.mailgun.net/v3/sandbox7c596a8043134994941668ae565cb653.mailgun.org/messages",
  		auth=("api", os.getenv('MAILGUN_API_KEY')),
  		data={"from": "Mailgun Sandbox <postmaster@sandbox7c596a8043134994941668ae565cb653.mailgun.org>",
			"to": "Ian Bruce <ian.b@justicequest.pro>",
  			"subject": "Hello Ian Bruce",
  			"text": "Congratulations Ian Bruce, you just sent an email with Mailgun! You are truly awesome!"})
