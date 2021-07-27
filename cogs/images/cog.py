from discord.ext import commands
from ink.core import squidcommand


class Images(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


# from wand.image import Image
# from wand.display import display

# with Image() as wand:
#     with Image(filename='./mona-lisa.png') as img:
#         r = 1
#         with img.clone() as i:
#             i.resize(int(i.width * r * 0.25), int(i.height * r * 0.25))

#             i.rotate(r * 90)
#             i.save(filename="./mona-lisa-1.png")
