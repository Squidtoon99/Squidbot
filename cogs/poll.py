from ink.core import squidcommand
from discord.ext import commands
import discord


def to_emoji(c):
    base = 0x1F1E6
    return chr(base + c)


class Polls(commands.Cog):
    """Quick voting commands"""

    def __init__(self, bot) -> None:
        self.bot = bot

        self.yes = "✅"
        self.no = "❌"

    @squidcommand("poll")
    @commands.bot_has_guild_permissions(add_reactions=True, send_messages=True)
    async def poll(self, ctx: commands.Context, question: str) -> dict:
        """
        Quickly create a poll
        """

        # description is a required field
        embed = discord.Embed(description=question).set_author(
            name=ctx.author.name, icon_url=ctx.author.avatar_url
        )

        msg = await ctx.reply(
            embed=embed,
        )
        await msg.add_reaction(self.yes)
        await msg.add_reaction(self.no)


def setup(bot) -> None:
    bot.add_cog(Polls(bot))
