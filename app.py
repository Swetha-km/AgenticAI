import os
import re
import urllib.parse
import urllib.request

from flask import Flask, request, jsonify, abort, render_template_string

app = Flask(_name_)

HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
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
    background:#fff;
    color:#000;
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
const status = document.getElementById("status");

async function send(command){

    const response = await fetch("/agent",{
        method:"POST",
        headers:{
            "Content-Type":"application/json"
        },
        body:JSON.stringify({
            text_command:command
        })
    });

    const data = await response.json();

    if(data.error){
        status.innerText = data.error;
        return;
    }

    status.innerText="Opening...";
    window.open(data.url,"_blank");
}

function start(){

    if(!SR){
        alert("Please use Chrome or Microsoft Edge.");
        return;
    }

    const rec = new SR();

    rec.lang="en-US";

    rec.onstart=()=>{
        status.innerText="Listening...";
    };

    rec.onresult=(e)=>{

        const text=e.results[0][0].transcript;

        status.innerText=text;

        send(text);
    };

    rec.onerror=(e)=>{
        status.innerText=e.error;
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
            "https://www.youtube.com/results?search_query="
            + urllib.parse.quote_plus(query),
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "en-US"
            }
        )

        html = urllib.request.urlopen(req, timeout=5).read().decode()

        match = re.search(r'"videoId":"([A-Za-z0-9_-]{11})"', html)

        if match:
            return match.group(1)

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
        vid = find_first_video_id(query)

        if vid:
            return f"https://www.youtube.com/watch?v={vid}&autoplay=1"

    return (
        "https://www.youtube.com/results?search_query="
        + urllib.parse.quote_plus(query)
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


@app.route("/agent", methods=["POST"])
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
        error="Only YouTube and Gmail commands are currently supported."
    )


if _name_ == "_main_":
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 8000)),
        debug=True
    )
