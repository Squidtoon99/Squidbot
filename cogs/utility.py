from ink.core import squidcommand
from discord.ext import commands


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @squidcommand()
    async def source(self, _):
        yield "https://github.com/Squidtoon99/SquidBot"

    @squidcommand()
    async def ping(self, _):
        yield "Bot Latency: `{:,}` ms".format(int(self.bot.latency * 1000))
