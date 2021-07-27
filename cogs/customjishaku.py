from discord.ext import commands

from jishaku.cog import STANDARD_FEATURES, OPTIONAL_FEATURES

class CustomJishaku(*OPTIONAL_FEATURES, *STANDARD_FEATURES):
    pass

def setup(bot: commands.Bot):
    bot.add_cog(CustomJishaku(bot=bot))