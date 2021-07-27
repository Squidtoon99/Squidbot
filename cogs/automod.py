import asyncio
import re
from urllib.parse import urlparse
import time
import discord
import dns.resolver
from discord.ext import commands
from ink.core.command import squidcommand
from ink.core.context import Context
from ink.utils.db import RedisDict
from emoji import UNICODE_EMOJI
import numpy
import unicodedata


def better_round(num: int, base: int = 5) -> int:
    return base * round(num / base)


def principal_period(s):
    i = (s + s).find(s, 1, -1)
    return None if i == -1 else s[:i]


ZALGO_CHAR_CATEGORIES = ["Mn", "Me"]


def is_zalgo(s):
    if len(s) == 0:
        return False
    word_scores = []
    for word in s.split():
        cats = [unicodedata.category(c) for c in word]
        score = sum([cats.count(banned) for banned in ZALGO_CHAR_CATEGORIES]) / len(
            word
        )
        word_scores.append(score)
    total_score = numpy.percentile(word_scores, 75)
    return total_score


class AutoModCheckFailure(commands.CommandError):
    def __init__(self, check: str, context: commands.Context, message: str):
        self.check = check
        self.context = context
        self.message = message


link_crazy = re.compile(
    r"(?i)\b((?:https?:(?:/{1,3}|[a-z0-9%])|[a-z0-9.\-]+[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw|dev|xyz|app)/)(?:[^\s()<>{}\[\]]+|\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\))+(?:\([^\s()]*?\([^\s()]+\)[^\s()]*?\)|\([^\s]+?\)|[^\s`!()\[\]{};:'"
    + '"'
    + r".,<>?«»“”‘’])|(?:(?<!@)[a-z0-9]+(?:[.\-][a-z0-9]+)*[.](?:com|net|org|edu|gov|mil|aero|asia|biz|cat|coop|info|int|jobs|mobi|museum|name|post|pro|tel|travel|xxx|ac|ad|ae|af|ag|ai|al|am|an|ao|aq|ar|as|at|au|aw|ax|az|ba|bb|bd|be|bf|bg|bh|bi|bj|bm|bn|bo|br|bs|bt|bv|bw|by|bz|ca|cc|cd|cf|cg|ch|ci|ck|cl|cm|cn|co|cr|cs|cu|cv|cx|cy|cz|dd|de|dj|dk|dm|do|dz|ec|ee|eg|eh|er|es|et|eu|fi|fj|fk|fm|fo|fr|ga|gb|gd|ge|gf|gg|gh|gi|gl|gm|gn|gp|gq|gr|gs|gt|gu|gw|gy|hk|hm|hn|hr|ht|hu|id|ie|il|im|in|io|iq|ir|is|it|je|jm|jo|jp|ke|kg|kh|ki|km|kn|kp|kr|kw|ky|kz|la|lb|lc|li|lk|lr|ls|lt|lu|lv|ly|ma|mc|md|me|mg|mh|mk|ml|mm|mn|mo|mp|mq|mr|ms|mt|mu|mv|mw|mx|my|mz|na|nc|ne|nf|ng|ni|nl|no|np|nr|nu|nz|om|pa|pe|pf|pg|ph|pk|pl|pm|pn|pr|ps|pt|pw|py|qa|re|ro|rs|ru|rw|sa|sb|sc|sd|se|sg|sh|si|sj|Ja|sk|sl|sm|sn|so|sr|ss|st|su|sv|sx|sy|sz|tc|td|tf|tg|th|tj|tk|tl|tm|tn|to|tp|tr|tt|tv|tw|tz|ua|ug|uk|us|uy|uz|va|vc|ve|vg|vi|vn|vu|wf|ws|ye|yt|yu|za|zm|zw)\b/?(?!@)))"
)
emoji_crazy = re.compile(
    r"<(?P<animated>a?):(?P<name>[a-zA-Z0-9_]{2,32}):(?P<id>[0-9]{18,22})>"
)
invite_crazy = re.compile(
    r"(https?://)?(www.)?(discord.(gg|io|me|li)|discordapp.com/invite)/[^\s/]+?(?=\b)"
)


def repeated_text(s):

    # size of string
    n = len(s)

    m = dict()

    for i in range(n):
        string = ""
        for j in range(i, n):
            string += s[j]
            if string in m.keys():
                m[string] += 1
            else:
                m[string] = 1

    # to store maximum freqency
    maxi = 0

    # To store string which has
    # maximum frequency
    maxi_str = ""

    for i in m:
        if m[i] > maxi:
            maxi = m[i]
            maxi_str = i
        elif m[i] == maxi:
            ss = i
            if len(ss) > len(maxi_str):
                maxi_str = ss

    # return substring which has maximum freq
    return maxi_str


class AutoMod(commands.Cog):
    def __init__(self, bot):
        self.bot: commands.AutoShardedBot = bot

    @squidcommand("automod")
    async def automod_cmd(self, ctx, check: str, choice: bool, action: str):
        checks = [
            "links",
            "caps",
            "mentions",
            "emojis",
            "spam",
            "repeated_text",
            "newlines",
            "images",
            "zalgo",
            "all",
        ]
        if check not in checks:
            yield "invalid choice"
            return

        if check == "all":
            async with ctx.storage as s:
                for i in checks:
                    s[f"check_{i}"] = {"actions": {action: True}}
        if choice:
            async with ctx.storage as s:
                s[f"check_{check}"] = {"actions": {action: True}}
        else:
            await ctx.storage.clear()
        yield await ctx.storage.keys()

    async def handle_checkfailure(self, error: AutoModCheckFailure, actions: dict):
        print(
            f"{error.check} check failed with message: {error.message}\n Message Content: {error.context.message.content}"
        )
        coros = []
        ctx = error.context
        for action, values in actions.items():
            if action == "delete":
                if ctx.channel.permissions_for(ctx.me).manage_messages:
                    coros.append(ctx.message.delete())
                if (
                    ctx.channel.permissions_for(ctx.me).send_messages
                    and ctx.channel.permissions_for(ctx.me).embed_links
                ):
                    coros.append(
                        ctx.send(
                            embed=discord.Embed(
                                color=self.bot.color,
                                title=f"Automod {error.check}",
                                description="\u200b" + error.message,
                            ).set_author(
                                icon_url=ctx.author.avatar.url,
                                name=ctx.message.content[:10]
                                + ("..." if len(ctx.message.content) > 10 else ""),
                            ),
                            delete_after=3,
                        )
                    )
            if action == "infraction":
                self.bot.dispatch(
                    "member_infraction", ctx.author, values.get("infractions", 1)
                )
            if action == "kick":
                if (
                    ctx.me.guild_permissions.kick_members
                    and ctx.me.top_role > ctx.author.top_role
                ):
                    coros.append(
                        ctx.author.kick(
                            reason=f"Automod Check [{error.check}]:\n{error.message}"
                        )
                    )
            if action == "ban":
                if (
                    ctx.me.guild_permissions.ban_members
                    and ctx.me.top_role > ctx.author.top_role
                ):
                    coros.append(
                        ctx.author.ban(
                            reason=f"Automod Check [{error.check}]:\n{error.message}"
                        )
                    )
            if action == "quarantine":
                self.bot.dispatch("member_quarantine", ctx.author, values)
        if coros:
            resp = await asyncio.gather(*coros, return_exceptions=True)
            print(resp)

    async def validate_bypass(self, ctx: commands.Context, bypass: dict):
        for check, group in bypass.items():
            if check == "role":
                id = group.get("id")
                if id in [i.id for i in ctx.author.roles]:
                    return True
            if check == "permissions":
                if getattr(
                    ctx.channel.permissions_for(ctx.author), group.get("id"), False
                ):
                    return True
            if check == "member":
                if ctx.author.id == group.get("id"):
                    return True

            if check == "channel":
                if ctx.channel.id == group.get("id"):
                    return True
        return False

    # Checks

    async def check_links(self, context: commands.Context, data: dict):
        amount = data.get("amount", 1)
        per = data.get("per", 5)

        links = link_crazy.findall(context.message.content)
        print("links:", links)
        linkCount = 0
        for link in set(links):
            p = urlparse(link)
            link = p.netloc or link.split("/")[0]
            try:
                dns.resolver.resolve(link)
            except Exception as exc:
                print("link failed", exc)
                # not a link
                continue
            else:
                linkCount += 1
        if not linkCount:
            return

        key = f"check_links:{context.guild.id}:{context.author.id}:{better_round(int(time.time()), base=per)}"  # implementing efficient caching
        actualLinks = int((await self.bot.redis.get(key)) or 0) + linkCount
        await self.bot.redis.set(key, actualLinks, expire=per * 2)
        if actualLinks >= amount:
            raise AutoModCheckFailure("links", context, f"Link detected ({link})")

    async def check_invites(self, context: commands.Context, data: dict):
        amount = data.get("amount", 1)
        per = data.get("per", 5)

        invites = invite_crazy.findall(context.message.content)
        print("Invites:", invites)
        if not invites:
            return
        key = f"check_invites:{context.guild.id}:{context.author.id}:{better_round(int(time.time()), base=per)}"  # implementing efficient caching
        invites = int((await self.bot.redis.get(key)) or 0) + len(set(invites))
        if invites:
            await self.bot.redis.set(key, invites, expire=per * 2)

        if invites >= amount:
            raise AutoModCheckFailure("invite", context, f"Invite")

    async def check_caps(self, context: commands.Context, data: dict):
        percent = data.get("percent", 70)
        if not context.message.content:
            return
        caps = int(
            100
            * (
                len([i for i in context.message.content if i.isupper()])
                / len(context.message.content)
            )
        )
        print(caps, "%")
        if caps > percent and len(context.message.content) > 3:
            raise AutoModCheckFailure(
                "caps", context, f"Excessive use of caps ({caps}%)"
            )

    async def check_zalgo(self, context: commands.Context, data: dict):
        percent = data.get("percent", 70)

    async def check_newlines(self, context: commands.Context, data: dict):
        amount = data.get("amount", 15)
        per = data.get("per", 3)

        key = f"check_newlines:{context.guild.id}:{context.author.id}:{better_round(int(time.time()), base=per)}"  # implementing efficient caching
        newlines = int(
            (await self.bot.redis.get(key)) or 0
        ) + context.message.content.strip().count("\n")
        if newlines:
            await self.bot.redis.set(key, newlines, expire=per * 2)

        if newlines > amount:
            raise AutoModCheckFailure(
                "newlines", context, f"Too many newlines ({newlines}/{per}s)"
            )

    async def check_mentions(self, context: commands.Context, data: dict):
        if not context.message.mentions:
            return
        amount = data.get("amount", 5)
        per = data.get("per", 5)

        key = f"check_mentions:{context.guild.id}:{context.author.id}:{better_round(int(time.time()), base=per)}"  # implementing efficient caching
        mentions = int((await self.bot.redis.get(key)) or 0) + len(
            context.message.mentions
        )
        if mentions:
            await self.bot.redis.set(key, mentions, expire=per * 2)

        print("user mentions", mentions)
        if mentions > amount:
            raise AutoModCheckFailure(
                "mentions", context, f"Too many mentions [{mentions}]"
            )

    async def check_emojis(self, context: commands.Context, data: dict):
        amount = data.get("amount", 7)
        per = data.get("per", 5)

        key = f"check_emojis:{context.guild.id}:{context.author.id}:{better_round(int(time.time()), base=per)}"

        emoji_count = sum(
            1 for _ in emoji_crazy.finditer(context.message.content)
        ) + len([i for i in context.message.content if i in UNICODE_EMOJI["en"]])
        if not emoji_count:
            return
        emojis = max(int((await self.bot.redis.get(key)) or 0), 0) + emoji_count

        await self.bot.redis.set(key, emojis, expire=per * 2)

        print("emoji count", emojis)
        if emojis > amount:
            raise AutoModCheckFailure("emojis", context, f"Too many emojis [{emojis}]")

    async def check_spam(self, context: commands.Context, data: dict):
        amount = data.get("amount", 5)
        per = data.get("per", 3)

        key = f"check_spam:{context.guild.id}:{context.author.id}:{better_round(int(time.time()), base=per)}"
        messages = max(int((await self.bot.redis.get(key)) or 0), 0) + 1

        await self.bot.redis.set(key, messages, expire=per * 2)

        print("message count", messages)
        if messages > amount:
            raise AutoModCheckFailure(
                "spam", context, f"Sending messages too quickly ({messages:,}/{per:,}s)"
            )

    async def check_images(self, context: commands.Context, data: dict):
        amount = data.get("amount", 3)
        per = data.get("per", 8)

        if not context.message.attachments:
            return
        key = f"check_images:{context.guild.id}:{context.author.id}:{better_round(int(time.time()), base=per)}"
        images = max(int((await self.bot.redis.get(key)) or 0), 0) + len(
            context.message.attachments
        )

        await self.bot.redis.set(key, images, expire=per * 2)

        print("image count", images)
        if images > amount:
            raise AutoModCheckFailure(
                "images", context, f"Sending images too quickly ({images:,}/{per:,}s)"
            )

    async def check_repeated_text(self, context: commands.Context, data: dict):
        amount = data.get("amount", 3)
        per = data.get("per", 30)

        # multiple messages
        key = f"check_repeated_text:{context.guild.id}:{better_round(int(time.time()), base=per)}"

        await self.bot.redis.hincrby(key, context.message.content.strip(), 1)
        await self.bot.redis.expire(key, per + 1)

        amn = int(await self.bot.redis.hget(key, context.message.content.strip()))

        c = context.message.content.strip().lower()
        if amn > amount:
            print("repeated text:", amn, c)
            t = context.message.content[:8] + ("..." if len(c) >= 8 else "")
            raise AutoModCheckFailure(
                "repeated_text", context, f"Repeated text [{t}] ({amn}/{per}s)"
            )

        # # single message

        repeated = repeated_text(c)
        if len(repeated.strip()) <= 1:
            return  # useless

        if repeated and (amn := c.count(repeated)) > amount:
            print("repeated second check", "[", repeated, "]", context.message.content)
            t = context.message.content[:8] + (
                "..." if len(context.message.content) >= 8 else ""
            )
            raise AutoModCheckFailure(
                "repeated_text", context, f"Repeated text [{t}] ({amn}/{per}s)"
            )
        else:
            print(amn, c, "[", repeated, "]")

    @commands.Cog.listener("on_context")
    async def automod(self, ctx: Context) -> None:
        if ctx.message.author.bot:
            return
        if not ctx.message.guild:
            return

        ctx._storage = RedisDict(
            self.bot.redis, prefix=f"storage:{self.qualified_name}:{ctx.guild.id}"
        )
        checkNames = await ctx.storage.keys()
        checks = {}
        for checkName in filter(lambda x: x.startswith("check_"), checkNames):
            if check := getattr(self, checkName, None):
                checks[checkName] = check

        for checkName, check in checks.items():
            checkData = await ctx.storage[checkName]
            bypass = await self.validate_bypass(ctx, checkData.get("bypass", {}))
            if bypass:
                continue
            try:
                await check(ctx, checkData)
            except AutoModCheckFailure as exception:
                await self.handle_checkfailure(exception, checkData.get("actions"))
                break

    @squidcommand("check")
    @commands.guild_only()
    async def checkmessage(self, ctx, message: discord.Message):
        if message.author.bot:
            yield "Cannot check bot messages"
            return
        alt_ctx = await ctx.bot.get_context(message)
        checkNames = await ctx.storage.keys()
        checks = {}
        for checkName in filter(lambda x: x.startswith("check_"), checkNames):
            if check := getattr(self, checkName, None):
                checks[checkName] = check

        passed = []
        failed = []

        for checkName, check in checks.items():
            checkData = await ctx.storage[checkName]
            bypass = await self.validate_bypass(ctx, checkData.get("bypass", {}))
            if bypass:
                passed.append(checkName)
                continue
            try:
                await check(alt_ctx, checkData)
            except AutoModCheckFailure as exception:
                failed.append((checkName, exception))
            else:
                passed.append(checkName)

        yield discord.Embed(
            title="Checks Complete",
            description="```diff\n# Passed\n+"
            + "\n+".join(passed)
            + ("\n-" if failed else "")
            + "\n-".join([f"{name}: {e.message}" for (name, e) in failed])
            + "\n```",
        )
