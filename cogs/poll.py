import discord
from discord.ext import commands
from discord_components import Button, ButtonStyle
from ink.core import squidcommand


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
            name=ctx.author.name, icon_url=ctx.author.avatar.url
        )

        await ctx.reply(
            embed=embed,
            components=[
                [
                    Button(style=ButtonStyle.green, label="👍", id="yes"),
                    Button(style=ButtonStyle.red, label="👎", id="no"),
                ]
            ],
        )

    @commands.Cog.listener()
    async def on_button_click(self, res):
        await res.respond(content="Poll Recieved", ephimeral=True)
