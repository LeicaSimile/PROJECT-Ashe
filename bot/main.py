# -*- coding: utf-8 -*-
import discord
from discord.ext import commands
import logging
import logging.config

from bot.commands import general
from bot.commands import music
import settings

logging.config.fileConfig("logging.ini")
logger = logging.getLogger("main")
bot = commands.Bot(command_prefix=settings.BOT_PREFIX, description="For humanity!", pm_help=None)

def add_commands():
    bot.add_cog(general.General(bot))
    bot.add_cog(general.Debugging(bot))
    bot.add_cog(music.Music(bot))
    
@bot.event
async def on_ready():
    logger.info("{} is now online.".format(bot.user.name))
    logger.info("ID: {}".format(bot.user.id))
    logger.info("Command prefix: {}".format(settings.BOT_PREFIX))

    add_commands()
    await bot.change_presence(game=discord.Game(name="DDR | {}help".format(settings.BOT_PREFIX)))

@bot.event
async def on_member_join(member):
    server = member.server
    await bot.send_message(server, 'Salvation, bit by bit. Good to have you on our side, {0.mention}'.format(member))


def main():
    bot.run(settings.TOKEN)


if "__main__" == __name__:
    main()