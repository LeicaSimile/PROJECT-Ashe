import re
import discord
from discord.ext import commands
from requests.utils import requote_uri

from main.settings import Settings
from main import utils

class General(commands.Cog):
    """General purpose commands."""

    def __init__(self, bot):
        """
        Args:
            bot(Bot): Bot instance.
            
        """
        self.bot = bot

    @commands.command(
        description=Settings.command_settings("define").get("description"),
        usage=Settings.command_settings("define").get("description"))
    async def define(self, context):
        args = context.message.clean_content.split(maxsplit=1)
        if 2 > len(args):
            await context.channel.send(f"Type `{context.prefix}{context.command.name} {context.command.usage}` to look up a term in the dictionary.")
            return

        search_term = re.sub(r"\s+", " ", args[1].strip())
        search_results = utils.dictionary.regular_lookup(search_term)

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

            await context.channel.send(embed=reply)
        else:
            await context.channel.send(f"Couldn't find a definition for `{search_term}`.")
