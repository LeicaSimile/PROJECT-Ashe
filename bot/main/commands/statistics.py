import datetime
import io
import os
import re

import discord
from discord.ext import commands
import multidict
from wordcloud import WordCloud
from matplotlib.image import imread
from spacy.lang.en.stop_words import STOP_WORDS

from main.settings import Settings
from main.status import CommandStatus

def get_word_frequencies(text):
    fullTermsDict = multidict.MultiDict()
    tempDict = {}
    text = text.lower()
    text = re.sub(r"[^\w\s]+", "", text)

    for word in text.split(" "):
        if len(word) < 3 or word in STOP_WORDS:
            continue
        val = tempDict.get(word, 0)
        tempDict[word] = val + 1

    for key in tempDict:
        fullTermsDict.add(key, tempDict[key])

    return fullTermsDict

class Statistics(commands.Cog):
    """Analyze various statistics related to the server."""

    def __init__(self, bot):
        """
        Args:
            bot(Bot): Bot instance.
            
        """
        self.bot = bot

    @commands.command(
        description=Settings.command_settings("wordcloud").get("description"),
        usage=Settings.command_settings("wordcloud").get("usage"))
    async def wordcloud(self, context):
        arguments = context.message.content.split()
        messages = []
        channels = context.guild.text_channels
        now = datetime.datetime.now()
        days = 14
        user = None
        subject = context.guild.name

        if context.message.mentions:
            user = context.message.mentions[0]
            subject = user.display_name
        if context.message.channel_mentions:
            channels = [context.message.channel_mentions[0]]
            subject = f"#{channels[0].name}"

        report = await context.channel.send(f"Scanning {subject}'s past {days} days...")

        for channel in channels:
            try:
                async for m in channel.history(limit=None, after=(now - datetime.timedelta(days=days)), oldest_first=False):
                    if user:
                        if m.author == user:
                            messages.append(m.clean_content)
                        continue
                    if m.author.bot:
                        continue
                    messages.append(m.clean_content)
            except discord.errors.Forbidden:
                print(f"Can't access {channel.name}")
        
        if "picture provided" == "":
            img_mask = imread("wordcloud/mask.png")
            wc = WordCloud(background_color=None, mask=img_mask, contour_width=2, contour_color="white")
        else:
            wc = WordCloud(width=1000, height=400, max_words=500)

        frequencies = get_word_frequencies(" ".join(messages))
        wc.generate_from_frequencies(frequencies)
        
        wc_dir = f"wordcloud/{context.message.guild.id}"
        os.makedirs(wc_dir, exist_ok=True)

        wc_filename = f"{now:%Y%m%d%H%M%S}.png"
        wc_filepath = os.path.join(wc_dir, wc_filename)
        wc.to_file(wc_filepath)

        await report.delete()
        await context.channel.send(f"A wordcloud for {subject}'s past {days} days:", file=discord.File(wc_filepath))
        return CommandStatus.COMPLETED
