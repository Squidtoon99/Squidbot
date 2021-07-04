from discord.ext import commands
from ink.core import squidcommand


class Tests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @squidcommand() 
    async def testmessage(self, ctx):
        yield "This is a message!"

    @squidcommand()
    async def testmax(self, ctx):
        return "this is more than 2k characters\n" * 500

    @squidcommand()
    async def testgen(self, ctx):
        for i in range(5):
            yield i

    @squidcommand()
    @commands.has_permissions(administrator=False, manage_guild=False, view_channel=True, manage_messages=True) 
    async def testperm(self, ctx):
        yield str("You do have admin perms")
