import asyncio
import discord
import os
import requests

from datetime import date
from dotenv import load_dotenv
from discord.ext import commands
from sheets import DiscordDB, Requirements
from StringProgressBar import progressBar

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('GUILD_ID')
ROKSTATS_API = os.getenv('ROKSTATS_API')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="/", intents=intents)
objDiscordGuildID = discord.Object(id=int(GUILD))

discord_db = DiscordDB()
requirements = Requirements()
bot.remove_command("help")

START_DATE = "2023-07-24"
SNAPSHOT_DATE = "2023-06-28"

async def find_status(kills_percentage, deads_percentage):
    """
    Determine player status based on kill and death percentages.

    Args:
        kills_percentage (int): Percentage of kills.
        deads_percentage (int): Percentage of deaths.

    Returns:
        str: Player status.
    """
    if kills_percentage >= 100 and deads_percentage >= 100:
        return "MGE Competitor"
    elif kills_percentage > 50 and deads_percentage > 100:
        return "Safe"
    elif deads_percentage > 50 and kills_percentage > 100:
        return "Safe"
    elif kills_percentage > 50 and deads_percentage < 100:
        return "Warning"
    elif deads_percentage > 50 and kills_percentage < 100:
        return "Warning"
    elif kills_percentage <= 100 and deads_percentage <= 100:
        return "Probation"
    else:
        return "Unknown"

async def check_id(gov_id: int):
    """
    Check a governor's stats using ROKSTATS API.

    Args:
        gov_id (int): Governor's ID.

    Returns:
        dict: Governor's statistics.
        False: If governor not found.
    """
    today = date.today()
    url = f"https://rokstats.online/api/governor/{gov_id}/summary?apiKey={ROKSTATS_API}&startDate={START_DATE}&endDate={today}&initialSnapshotDate={SNAPSHOT_DATE}"
    response = requests.get(url)
    data = response.json()
    return data if data else False

async def send_id_stats(response, author_id, interaction: discord.Interaction=None, channel=None):
    """
    Send governor's stats information.

    Args:
        response (dict): Governor's statistics.
        author_id (int): Author's ID.
        interaction (discord.Interaction, optional): Interaction object. Defaults to None.
        channel (discord.TextChannel, optional): Channel to send the message to. Defaults to None.
    """
    last_scan = response['SnapshotTime']
    date_only = last_scan.split('T')[0]
    gov_id = response['GovernorId']
    name = response['Name']
    alliance = response['Alliance']
    kp = response["KillPoints"]["Total"]
    totdeads = response["Dead"]
    power = response['Power']
    initial_snapshot_data = response['initialSnapshot']
    power_initial_snapshot = initial_snapshot_data.get('Power')
    CurrentT4 = response["killPointsDiff"]["T4"]
    CurrentT5 = response["killPointsDiff"]["T5"]
    CurrentDeads = response["deadDiff"]
    CurrentKills = int(CurrentT4) + int(CurrentT5)
    kill_req, deads_req = requirements.find_requirements(power_initial_snapshot)

    kills_percentage = CurrentKills * 100 // int(kill_req)
    deads_percentage = CurrentDeads * 100 // int(deads_req)
    player_status = await find_status(kills_percentage, deads_percentage)

    total = 100
    size = 15
    killsbar = progressBar.filledBar(total, kills_percentage, size)
    deadsbar = progressBar.filledBar(total, int(deads_percentage), size)
    
    if response:
        embed = discord.Embed(color=0x00ffe5)
        embed.title = "KvK Personal stats"
        embed.set_author(name="TheMaxi7", url="https://github.com/TheMaxi7",
                        icon_url="https://avatars.githubusercontent.com/u/102146744?v=4")
        embed.set_thumbnail(url=f"https://rokstats.online/img/governors/{gov_id}.jpg")

        description = (
            f"Governor: {name if name else '0'}\n"
            f"Power snapshot: {power_initial_snapshot if power_initial_snapshot else '0'}\n"
            f"Current power: {power if power else '0'}\n"
            f"Governor ID: {gov_id if gov_id else '0'}\n"
            f"Alliance: {alliance if alliance else '0'}\n"
            f"Account KP: {kp if kp else '0'}\n"
            f"Account deads: {totdeads if totdeads else '0'}\n"
            f"Account status: {player_status if player_status else '0'}\n"
        )
        embed.description = description

        embed.add_field(name="KILLS REQUIRED", value=kill_req, inline=True)
        embed.add_field(name="DEADS REQUIRED", value=deads_req, inline=True)

        kills_field = f"{CurrentKills}\n{killsbar[0]}   {int(killsbar[1])}%"
        embed.add_field(name="CURRENT KILLS", value=kills_field, inline=False)

        deads_field = f"{CurrentDeads}\n{deadsbar[0]}   {int(deadsbar[1])}%"
        embed.add_field(name="CURRENT DEADS", value=deads_field, inline=False)

        footer_text = (
            f"Scan date: {date_only} - Requested by @{author_id}\n\n"
            f"Data from www.rokstats.online made by @ibugbear\n"
        )
        embed.set_footer(text=footer_text, icon_url="https://rokstats.online/ico/apple-icon-76x76.png")

        if interaction:
            await interaction.response.send_message(embed=embed)
        elif channel:
            await channel.send(embed=embed)
    else:
        if interaction:
            await interaction.response.send_message("Bro, this ID does not exist", ephemeral=True)
        elif channel:
            await channel.send("Bro, this ID does not exist", ephemeral=True)


@bot.event
async def on_message(msg: discord.Message):
    """
    Event handler for received messages.

    Args:
        msg (discord.Message): Received message.
    """
    author=msg.author
    author_id = author.id
    content = msg.content
    channel = msg.channel
    today = date.today()
    content = content.split(" ")
    if len(content) == 1:
        request = content[0].lower()
        if request == "stats":
            id_from_db = discord_db.get_id_from_discord(author_id=author_id)
            if id_from_db:
               url=f"https://rokstats.online/api/governor/{id_from_db}/summary?apiKey={ROKSTATS_API}&startDate={START_DATE}&endDate={today}&initialSnapshotDate={SNAPSHOT_DATE}"
               response = requests.get(url)
               await send_id_stats(response.json(), channel=channel, author_id=int(author_id))
            else:
                await channel.send(content = "Your ID has not been registered yet. Write 'stats <your id>' to save your ID before using 'stats'. (Example: Stats 12345678)")
    elif len(content) == 2:
        request = content[0].lower()
        id = content[1]
        if request == "stats" and id:
            try:
                player_id = int(id)
            except Exception as e:
                print(e)
            response = await check_id(player_id)
            if response is not False:
                await send_id_stats(response, channel=channel, author_id=int(author_id))
                await discord_db.save_dc_id(author_id, player_id)
            else:
                await channel.send("Bro, this ID does not exist")


async def main():
    await bot.start(TOKEN, reconnect=True)

asyncio.run(main())


