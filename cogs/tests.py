from discord.ext import commands 
from ink.core import squidcommand 

class Tests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
    
    @squidcommand() 
    async def testmax(self, ctx):
        return "this is more than 2k characters\n" * 1000

    @squidcommand() 
    async def testgen(self, ctx):
        for i in range(5):
            yield i

def setup(bot) -> None:
    bot.add_cog(Tests(bot))