import send_slack_message as ssm

"""
client = slack.WebClient(token="https://hooks.slack.com/services/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")
response = client.files_upload(
    channels="#급등주",
    file="found_jongmok_20210510.csv",
    title="Found Jongmok",
    filetype="csv"
)
assert response["ok"]


import requests

payload={"text": "This is a line of text in a channel.\nAnd this is another line of text."}

def send_message_to_slack(text): 
    url = "https://hooks.slack.com/services/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" 
    payload = { "text" : text } 
    requests.post(url, json=payload)

send_message_to_slack("Send Message Using Python")    
"""

ssm.send_message_to_slack("test")