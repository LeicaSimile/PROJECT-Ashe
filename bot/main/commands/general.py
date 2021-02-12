import discord
from discord.ext import commands
from requests.utils import requote_uri

from main import settings
from main import utils

class General(commands.Cog):
    """General purpose commands."""

    def __init__(self, bot):
        """
        Args:
            bot(Bot): Bot instance.
            
        """
        self.bot = bot

    @commands.command(description="Gives the definition of a word", usage="[word]")
    async def define(self, context):
        args = context.message.clean_content.split(maxsplit=1)
        if 2 > len(args):
            await context.channel.send(f"Type `{context.prefix}{context.command.name} {context.command.usage}` to look up a term in the dictionary.")
            return

        search_term = args[1].strip()
        search_results = utils.dictionary.regular_lookup(search_term)

        if search_results:
            search_url = requote_uri(f"{settings.DICT_REGULAR_URL}{search_term}")
            reply = discord.Embed(title=search_term, url=search_url)
            reply.set_footer(text=search_url)
            try:
                definitions = []
                for i, entry in enumerate(search_results):
                    if i > 2:
                        break

                    is_offensive = " *(offensive)*" if entry.is_offensive else ""
                    definitions.append("**{search_term} ({i}){is_offensive}**")
                    definitions.append("\n".join(entry.short_definitions))
                    definitions.append("\n")
                
                reply.description = "\n".join(definitions)
            except AttributeError:
                # Suggested search terms
                reply.url = ""
                suggestions = "\n".join(search_results)
                reply.description = f"**Did you mean...**\n*{suggestions}*"

            context.channel.send(embed=reply)
        else:
            await context.channel.send(f"Couldn't find a definition for `{search_term}`.")
