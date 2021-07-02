from ink.core import squidcommand
from discord.ext import commands


class Utility(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @squidcommand()
    async def source(self, ctx):
        yield "https://github.com/Squidtoon99/SquidBot"

    @squidcommand()
    async def ping(self, ctx):
        yield "Bot Latency: `{:,}` ms".format(int(self.bot.latency * 1000))


def setup(bot):
    bot.add_cog(Utility(bot))
