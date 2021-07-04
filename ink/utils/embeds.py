import discord 
from datetime import datetime

__all__ = ("ErrorEmbed","Embed")

class Embed(discord.Embed):
    def __init__(self, *args, **kwargs):
        if "colour" not in kwargs:
            kwargs["colour"] = discord.Color.blurple() # discord red

        if kwargs.get("timestamp", False) is True:
            kwargs["timestamp"] = datetime.utcnow()

        if len(args) == 2:
            kwargs["title"] = args[0]
            kwargs["description"] = args[1]
        elif len(args) == 1:
            kwargs["description"] = args[0]

        super().__init__(**kwargs)

    def set_author(self, name=discord.Embed.Empty, icon_url=discord.Embed.Empty, **kwargs):
        super().set_author(name=name, icon_url=icon_url, **kwargs)

    def set_footer(self, text=discord.Embed.Empty, icon_url=discord.Embed.Empty):
        super().set_footer(text=text, icon_url=icon_url)

    def set_thumbnail(self, url=discord.Embed.Empty):
        super().set_thumbnail(url=url)

    def add_field(self, name=discord.Embed.Empty, value=discord.Embed.Empty, inline=True):
        super().add_field(name=name, value=value, inline=inline)

class ErrorEmbed(Embed):
    def __init__(self, *args, **kwargs):
        if "colour" not in kwargs:
            kwargs["colour"] = 0xED4245 # discord red

        super().__init__(*args, **kwargs)
