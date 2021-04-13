"""General commands"""
import re
import discord
from discord.ext import commands
from requests.utils import requote_uri

from main.settings import Settings
from main import utils
from . import dictionary

class General(commands.Cog):
    """General purpose commands."""

    def __init__(self, bot):
        """
        Args:
            bot(Bot): Bot instance.

        """
        self.bot = bot

    @commands.command()
    async def define(self, context):
        """Get dictionary entry of a given term"""
        args = context.message.clean_content.split(maxsplit=1)
        if len(args) < 2:
            prefix = context.prefix
            command_name = context.command.name
            command_usage = context.command.usage
            hint = f"Type `{prefix}{command_name} {command_usage}` to look up a term in the dictionary."
            await utils.say(context.channel, content=hint)
            return

        search_term = re.sub(r"\s+", " ", args[1].strip())
        search_results = dictionary.regular_lookup(search_term)

        if search_results:
            base_url = Settings.command_settings("define")["base_url"]
            search_url = requote_uri(f"{base_url}{search_term}")
            reply = discord.Embed(title=f'Define "{search_term}"', url=search_url)
            reply.set_footer(text=f"Source: {search_url}")
            try:
                num_entries = len(search_results)
                definitions = []
                for i, entry in enumerate(search_results):
                    if i > 2:
                        break

                    is_offensive = " *(offensive)*" if entry.is_offensive else ""
                    term_type = entry.term_type
                    definitions.append(f"**{search_term}** {i + 1}/{num_entries} *({term_type})*{is_offensive}")
                    definitions.append("".join([
                        "*", "\n\n".join(entry.short_definitions), "*"
                    ]))
                    definitions.append("\n")

                reply.description = "\n".join(definitions)
            except AttributeError:
                # Suggested search terms
                reply.url = ""
                suggestions = "\n".join(search_results)
                reply.description = f"**Did you mean...**\n*{suggestions}*"

            await utils.say(context.channel, embed=reply)
        else:
            await utils.say(context.channel, content=f"Couldn't find a definition for `{search_term}`.")
