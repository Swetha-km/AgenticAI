import os
import re
import urllib.parse
import urllib.request

from flask import Flask, request, jsonify, abort, render_template_string

app = Flask(_name_)

HTML = """
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Voice Agent</title>

<style>
*{
    margin:0;
    padding:0;
    box-sizing:border-box;
    font-family:Arial,sans-serif;
}

body{
    background:#000;
    color:#fff;
    display:flex;
    justify-content:center;
    align-items:center;
    height:100vh;
}

.container{
    text-align:center;
}

h2{
    font-size:2.5rem;
    margin-bottom:40px;
}

button{
    width:120px;
    height:120px;
    border-radius:50%;
    border:none;
    background:white;
    color:black;
    font-size:18px;
    font-weight:bold;
    cursor:pointer;
    transition:.3s;
}

button:hover{
    transform:scale(1.08);
    box-shadow:0 0 25px rgba(255,255,255,.5);
}

#status{
    margin-top:30px;
    font-size:18px;
    color:#ccc;
}
</style>

</head>

<body>

<div class="container">
    <h2>Voice Agent</h2>

    <button onclick="start()">
        Speak
    </button>

    <p id="status"></p>
</div>

<script>

const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
const statusText = document.getElementById("status");

async function send(command){

    let response = await fetch("/agent",{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({
            text_command:command
        })
    });

    let data = await response.json();

    if(data.error){
        statusText.innerText = data.error;
        return;
    }

    statusText.innerText="Opening...";
    window.open(data.url,"_blank");
}

function start(){

    if(!SR){
        alert("Please use Chrome or Edge.");
        return;
    }

    const rec = new SR();

    rec.lang="en-US";

    rec.onstart=()=>{
        statusText.innerText="Listening...";
    };

    rec.onresult=(e)=>{

        const text=e.results[0][0].transcript;

        statusText.innerText=text;

        send(text);
    };

    rec.onerror=(e)=>{
        statusText.innerText=e.error;
    };

    rec.start();
}

</script>

</body>
</html>
"""


def find_first_video_id(query):
    try:
        req = urllib.request.Request(
            "https://www.youtube.com/results?search_query=" +
            urllib.parse.quote_plus(query),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-US"
            }
        )

        html = urllib.request.urlopen(req, timeout=5).read().decode()

        match = re.search(r'"videoId":"([A-Za-z0-9_-]{11})"', html)

        if match:
            return match.group(1)

        return None

    except Exception as e:
        print(e)
        return None


def build_youtube_target(cmd):

    play = "play" in cmd

    query = re.sub(
        r"(open youtube|play|search|search for|on youtube)",
        "",
        cmd,
        flags=re.I
    ).strip()

    if not query:
        return "https://www.youtube.com"

    if play:

        video = find_first_video_id(query)

        if video:
            return f"https://www.youtube.com/watch?v={video}&autoplay=1"

    return (
        "https://www.youtube.com/results?search_query=" +
        urllib.parse.quote_plus(query)
    )


def build_gmail_target(cmd):

    to = ""
    body = ""

    email = re.search(r"to\s+([a-zA-Z0-9._%+-]+)", cmd)

    if email:
        to = email.group(1)

        if "@" not in to:
            to += "@gmail.com"

    message = re.search(r"(type|saying)\s+(.*)", cmd)

    if message:
        body = message.group(2)

    if not to and not body:
        return "https://mail.google.com"

    params = urllib.parse.urlencode({
        "view": "cm",
        "fs": "1",
        "to": to,
        "body": body
    })

    return "https://mail.google.com/mail/u/0/?" + params


@app.route("/")
def home():
    return render_template_string(HTML)


@app.post("/agent")
def agent():

    data = request.get_json(silent=True)

    if not data or "text_command" not in data:
        abort(400, description="Missing command")

    cmd = data["text_command"].lower().strip()

    if "youtube" in cmd or "play" in cmd:
        return jsonify(
            action="open_tab",
            url=build_youtube_target(cmd)
        )

    if any(word in cmd for word in ["gmail", "mail", "email"]):
        return jsonify(
            action="open_tab",
            url=build_gmail_target(cmd)
        )

    return jsonify(
        error="Only YouTube and Gmail commands are supported."
    )


if _name_ == "_main_":
    app.run(debug=True, port=8000)
