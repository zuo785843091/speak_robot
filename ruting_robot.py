# coding: utf-8
import urllib.request
import sys
import json

def robot_main(words):
    url = "http://www.tuling123.com/openapi/api?"

    key = "46b80b0569b14457b0222a2792775f9f"
    userid = "eb2edb736"

    words = urllib.parse.quote(words)
    url = url + "key=" + key + "&info=" + words + "&userid=" + userid

    req = urllib.request.Request(url)
    
    req.add_header("apikey", "g8NGc0yPGlqA6ciy6HQLpgax")
    print(url)
    #req = url
    print("robot start request")
    resp = urllib.request.urlopen(req)
    print("robot stop request")
    content = resp.read()
    if content:
        data = json.loads(content.decode("utf-8"))
        return data["text"]
    else:
        return None
