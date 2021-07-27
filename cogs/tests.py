from typing import AsyncIterable, Optional
from discord.ext import commands
from ink.core import squidcommand
import random


class Tests(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @squidcommand()
    async def testmessage(self, _) -> AsyncIterable[str]:
        yield "This is a message!"

    @squidcommand()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def testmax(self, _) -> str:
        return "this is more than 2k characters\n" * 500

    @squidcommand()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def testgen(self, _, amount: int = 5) -> AsyncIterable[int]:
        for i in range(min(amount, 15)):
            yield i

    @squidcommand()
    @commands.has_permissions(
        administrator=True, manage_guild=True, view_channel=True, manage_messages=True
    )
    async def testperm(self, _) -> AsyncIterable[str]:
        yield str("You do have admin perms")

    @squidcommand()
    async def teststorage(
        self, ctx: commands.Context, key: str, value: str
    ) -> AsyncIterable[Optional[int]]:
        async with ctx.storage as storage:
            storage["myvalue"] = {"a": "b", "b": random.random(), "c": [1, 2, 3]}
            storage[key] = value
            x = storage[key]
            y = storage["myvalue"]

        yield ({key: await storage[key]})

    @squidcommand("testreload")
    async def testreload(self, _, d: int):
        yield f"Reloaded! - a -b - c - {d} "
