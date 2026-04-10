from flask import Flask, request, jsonify
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf.json_format import MessageToJson
import binascii
import aiohttp
from google.protobuf.json_format import MessageToDict
import requests
import json
import like_pb2
import like_count_pb2
from google.protobuf.message import DecodeError
from datetime import datetime, timedelta
import uid_generator_pb2
# Add these imports to suppress the SSL warning
import urllib3
import warnings

# Disable the InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
application = app

# Simplified allowed keys - just a set of valid keys
ALLOWED_KEYS = {"krish", "arya", "mxleak"}

def encrypt_message(plaintext):
    key = b'Yg&tc%DEuh6%Zc^8'
    iv = b'6oyZDr22E3ychjM%' 
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_message = pad(plaintext, AES.block_size)
    encrypted_message = cipher.encrypt(padded_message)
    return binascii.hexlify(encrypted_message).decode('utf-8')
    
def create_protobuf_message(user_id, region):
    message = like_pb2.like()
    message.uid = int(user_id)
    message.region = region
    return message.SerializeToString()

async def send_request(encrypted_uid, token, url):
    edata = bytes.fromhex(encrypted_uid)
    token = token['token']
    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Authorization': f"Bearer {token}",
        'Content-Type': "application/x-www-form-urlencoded",
        'Expect': "100-continue",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': "OB53"
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, data=edata, headers=headers) as response:
            if response.status != 200:
                return None
            return response.status

async def send_multiple_requests(uid, server_name, url):
    region = (server_name)
    protobuf_message = create_protobuf_message(uid, region)
    encrypted_uid = encrypt_message(protobuf_message)
    
    tasks = []
    tokens = token_used(server_name)
    for i, token_data in enumerate(tokens):
        token = token_data['token']
        tasks.append(send_request(encrypted_uid, token, url))
    
    results = await asyncio.gather(*tasks)
    return results

def create_protobuf(uid):
    message = uid_generator_pb2.uid_generator()
    message.saturn_ = int(uid)
    message.garena = 1
    return message.SerializeToString()

def enc(uid):
    protobuf_data = create_protobuf(uid)
    encrypted_uid = encrypt_message(protobuf_data)
    return encrypted_uid

def make_request(encrypt, server_name, token):
    if server_name == "IND":
        url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
    elif server_name in {"BR", "US", "SAC", "NA"}:
        url = "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
    else:
        url = "https://clientbp.ggblueshark.com/GetPlayerPersonalShow"

    edata = bytes.fromhex(encrypt)

    headers = {
        'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Authorization': f"Bearer {token}",
        'Content-Type': "application/x-www-form-urlencoded",
        'Expect': "100-continue",
        'X-Unity-Version': "2018.4.11f1",
        'X-GA': "v1 1",
        'ReleaseVersion': "OB53"
    }
    response = requests.post(url, data=edata, headers=headers, verify=False)
    hex = response.content.hex()
    binary = bytes.fromhex(hex)
    decode = decode_protobuf(binary)
    return decode

def token_used(server_name):
    # Get tokens from local server
    if server_name == "IND":
        response = requests.get("https://free-like-token.onrender.com/token/ind")
    elif server_name in {"BR", "US", "SAC", "NA"}:
        response = requests.get("https://token.freefireinfo.xyz/token/usa")
    else:
        response = requests.get("https://sea-free-like-token.onrender.com/token/sea")
    
    tokens = response.json()
    token_list = [{"token": token} for token in tokens]
    return token_list

def decode_protobuf(binary):
    from google.protobuf.message import DecodeError
    try:
        items = like_count_pb2.Info()
        items.ParseFromString(binary)
        return items
    except DecodeError as e:
        print(f"Error decoding Protobuf data: {e}")
        print(f"Binary data (truncated): {binary[:50]}")
        return None

@app.route('/', methods=['GET'])
def handler():
    return "Running..."

@app.route('/<int:uid>/<server_nam>/<key>', methods=['GET'])
def handle_request(uid, server_nam, key):    
    if key in ALLOWED_KEYS:
        if not uid or not server_nam or not key:
            return jsonify({"error": "UID, Region and Key are required"}), 400

        def process_request():
            response = requests.get(f"https://regionaljwt.freefireinfo.xyz/token?region={server_nam}")
            token = response.text
    
            encrypt = enc(uid)
            server_name = server_nam.upper()
            before = make_request(encrypt, server_name, token)
            jsone = MessageToJson(before)
            data = json.loads(jsone)
            before_like = data['AccountInfo'].get('Likes', None)
            if before_like is None:
                before_like = int("0")
            else:
                before_like = int(before_like)
            
            if server_name == "IND":
                url = "https://client.ind.freefiremobile.com/LikeProfile"
            elif server_name in {"BR", "US", "SAC", "NA"}:
                url = "https://client.us.freefiremobile.com/LikeProfile"
            else:
                url = "https://clientbp.ggblueshark.com/LikeProfile"
    
            asyncio.run(send_multiple_requests(uid, server_name, url))
    
            after = make_request(encrypt, server_name, token)
            jsone = MessageToJson(after)
            data = json.loads(jsone)
            after_like = data['AccountInfo'].get('Likes', None)
            if after_like is None:
                after_like = int("0")
            else:
                after_like = int(after_like)

            id = int(data['AccountInfo']['UID'])
            name = str(data['AccountInfo']['PlayerNickname'])
            like_given = after_like - before_like
            
            status = 1 if like_given != 0 else 2
                
            result = {
                "LikesGivenByAPI": like_given,
                "LikesafterCommand": after_like,
                "LikesbeforeCommand": before_like,
                "PlayerNickname": name,
                "UID": id,
                "status": status
            }
            return result

        hex_result = process_request()
        return hex_result
            
    else:
        return jsonify({"error": "Invalid Key. Contact: Telegram @smartclownyt"})

if __name__ == '__main__':
    app.run(debug=False, host="0.0.0.0", port=4600)
