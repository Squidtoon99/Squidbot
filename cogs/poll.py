import discord
from discord.ext import commands
from discord.enums import ButtonStyle
from ink.core import squidcommand


def to_emoji(c):
    base = 0x1F1E6
    return chr(base + c)


class Confirm(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="👍", style=discord.ButtonStyle.green)
    async def confirm(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label="👎", style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.stop()


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

        view = Confirm()
        await ctx.reply(embed=embed, view=view)

    @commands.Cog.listener()
    async def on_interaction(self, res):
        await res.response.defer(ephemeral=True)
