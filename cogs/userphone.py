from discord.ext.commands import Cog
from ink.core import squidcommand
from discord import Embed, Member
from aioredis.pubsub import Receiver
import json
import asyncio
import time


class UserPhone(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.channels = []
        self.reciever = None

    async def on_ready(self):
        if not self.reciever:
            self.reciever = Receiver(loop=self.bot.loop)

    async def user_leave(self, _: Member):
        return

    async def user_join(self, _: Member):
        return

    @squidcommand("phone")
    async def userphone(self, ctx):
        yield "Connected to userphone"

        await self.user_join(ctx.author)

        stop = time.time() + 30
        if not self.reciever:
            await self.on_ready()
        self.channels.append(ctx.channel.id)
        await self.bot.redis.psubscribe("userphone")
        async for channel, msg in self.reciever.iter():
            if time.time() > stop:
                break
            yield f"{channel}: {msg}"

        if ctx.channel.id in self.channels:
            self.channels.remove(ctx.channel.id)

        yield "Your session has expired"
        await self.user_leave(ctx.author)

    @Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        if message.channel.id in self.channels:
            print("publishing")
            await self.bot.redis.publish(
                f"userphone",
                json.dumps(
                    Embed(description=message.content[:200])
                    .set_author(
                        name=message.author.nick, icon_url=message.author.avatar_url
                    )
                    .to_dict()
                ),
            )
