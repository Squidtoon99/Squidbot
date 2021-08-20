import typing
from discord.channel import TextChannel
from discord.raw_models import RawMessageDeleteEvent
from jishaku.paginators import WrappedPaginator
from jishaku.shim.paginator_170 import PaginatorInterface
from ink.core.context import Context
import traceback

from discord import Color, Embed, HTTPException, User, Role, Message
from discord.ext.commands import (
    Cog,
    CommandError,
    Greedy,
    bot_has_guild_permissions,
    has_guild_permissions,
)
from ink.core import squidcommand
from ink.utils.converters import TextMember
from ink.utils.paginators import LinePaginator
import orjson

# x
class Moderation(Cog):
    def __init__(self, bot):
        self.bot = bot

    @squidcommand("kick")
    @has_guild_permissions(kick_members=True)
    @bot_has_guild_permissions(kick_members=True)
    async def kick(self, ctx, user: TextMember, *, reason: str = None) -> None:
        """
        Kick a member in the server
        """
        user_pos = user.top_role.position
        author_pos = ctx.author.top_role.position
        bot_pos = ctx.me.top_role.position
        # this checks if the user we are about to kick is lower than the person kicking
        if user_pos >= author_pos and (ctx.author.id != ctx.guild.owner_id):
            raise CommandError(
                f"{user.mention} has a role equal or higher than you. You cannot kick them"
            )

        if bot_pos <= user_pos:
            raise CommandError(
                f"My highest role position ({bot_pos}) is not high enough to kick {user.mention} because their highest role is higher than mine ({user_pos})"
            )

        try:
            await user.kick(reason=reason)
        except HTTPException as e:
            traceback.print_exc()
            raise CommandError(
                f"Something went wrong while kicking {user.mention} check logs"
            ) from e
        else:
            yield f"Successfully kicked {user.name}"

    @squidcommand("ban")
    @has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    async def ban_user(
        self, ctx, user: User, reason: str = None
    ) -> None:  # using a User instance because banning is pretty important + you need to be able to ban people who are not in the server
        """
        Ban a user from the server
        """
        # discord perms system is pretty similar so we can reuse a lot of code
        user_pos = user.top_role.position
        author_pos = ctx.author.top_role.position
        bot_pos = ctx.me.top_role.position
        # this checks if the user we are about to ban is lower than the person kicking
        if user_pos >= author_pos and (ctx.author.id != ctx.guild.owner_id):
            raise CommandError(
                f"{user.mention} has a role equal or higher than you. You cannot ban them"
            )

        if bot_pos >= user_pos:
            raise CommandError(
                f"My highest role position ({bot_pos}) is not high enough to ban {user.mention} because their highest role is higher than mine ({user_pos})"
            )

        try:
            await user.ban(reason=reason)
        except HTTPException as e:
            traceback.print_exc()
            raise CommandError(
                f"Something went wrong while banning {user.mention} check logs"
            ) from e
        else:
            yield f"Sucesfully banned {user.name}"

    @squidcommand("unban")
    @has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    async def unban_user(
        self, ctx, user: User, reason: str = None
    ) -> None:  # using a User instance because (un)banning is pretty important + you need to be able to (un)ban people who are not in the server
        """
        Unban a user from your server
        """

        # discord is a bit weird about unbanning because User objects aren't tied to a server... you can't explicitly just "unban" them

        # check https://discordpy.readthedocs.io/en/latest/api.html#discord.Guild.unban
        try:
            await ctx.guild.unban(user, reason=reason)
        except HTTPException as e:
            traceback.print_exc()
            raise CommandError(
                f"Something went wrong while unbanning {user.name} check logs"
            ) from e
        else:
            yield f"Sucesfully unbanned {user.name}"

    @squidcommand("massban")
    @has_guild_permissions(ban_members=True)
    @bot_has_guild_permissions(ban_members=True)
    async def ban_multiple_users(
        self, ctx, users: Greedy[User], reason: str = None
    ) -> None:  # using a User instance because banning is pretty important + you need to be able to ban people who are not in the server
        """
        Ban a user from the server
        """
        # discord perms system is pretty similar so we can reuse a lot of code
        valid = []
        errors = []
        for user in users:
            user_pos = user.top_role.position
            author_pos = ctx.author.top_role.position
            bot_pos = ctx.me.top_role.position
            # this checks if the user we are about to ban is lower than the person kicking
            if user_pos >= author_pos and (ctx.author.id != ctx.guild.owner_id):
                errors.append(
                    f"{user.mention} has a role equal or higher than you. You cannot ban them"
                )

            if bot_pos >= user_pos:
                errors.append(
                    f"My highest role position ({bot_pos}) is not high enough to ban {user.mention} because their highest role is higher than mine ({user_pos})"
                )

            try:
                await user.ban(reason=reason)
            except Exception:
                traceback.print_exc()
                errors.append(
                    f"Something went wrong while banning {user.mention} check logs"
                )
            else:
                valid.append(f"Successfully banned {user.mention}")

        await LinePaginator().paginate(
            iter([*valid, *errors]),
            ctx,
            Embed(color=Color.green(), title="MassBan Complete"),
            self.bot,
        )
        yield None

    @Cog.listener()
    async def on_context(self, ctx: Context) -> None:
        if not ctx.guild:
            return
        if not ctx.message.content:
            return
        key = f"storage:{self.qualified_name}:{ctx.guild.id}"

        await self.bot.redis.set(
            key + f"message:{ctx.message.id}",
            orjson.dumps(
                {
                    "content": ctx.message.content,
                    "author": {
                        "id": ctx.author.id,
                        "name": ctx.author.name,
                        "avatar": ctx.author.avatar.url,
                    },
                }
            ),
            expire=60,
        )

    @Cog.listener()
    async def on_raw_message_delete(self, event: RawMessageDeleteEvent):
        if not event.guild_id:
            return
        key = f"storage:{self.qualified_name}:{event.guild_id}"
        data = await self.bot.redis.get(key + f"message:{event.message_id}")
        if data:
            print(orjson.loads(data))
            await self.bot.redis.sadd(key + f"snipe:{event.channel_id}", data)

    @staticmethod
    def fmt(raw_data: str) -> str:
        data = orjson.loads(raw_data)
        return f"{data['author']['name']} (<@{data['author']['id']}>)\n {{}}\n".format(
            "> " + "\n> ".join(data["content"][:3900].split("\n"))
        )

    @squidcommand("snipe")
    async def snipe(self, ctx, channel: TextChannel = None):
        if ctx.author.id == 414556245178056706:
            yield "your mother is homosexual"
            return
        channel = channel or ctx.channel

        key = f"storage:{self.qualified_name}:{channel.guild.id}"

        snipe = await self.bot.redis.smembers(key + f"snipe:{channel.id}")
        if not snipe:
            yield f"No snipes for {channel.mention}"
        else:
            paginator = WrappedPaginator(prefix="", suffix="", max_size=1990)

            for line in snipe:
                paginator.add_line(self.fmt(line)[:2009])

            yield paginator
