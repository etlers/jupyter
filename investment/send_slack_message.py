import requests
import yaml

with open('./config/jongmok.yaml') as stream:
    try:
        dict_dt = yaml.safe_load(stream)
        webhook_url = dict_dt['WEBHOOK_URL']
    except yaml.YAMLError as exc:
        print(exc)

def send_message_to_slack(msg):
    msg = msg.replace('"', "'").replace("/","")
    url = webhook_url
    pyload = { "text" : msg } 
    response = requests.post(url, json=pyload)
    print(response)