import traceback

from discord import Color, Embed, HTTPException, User
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
        if user_pos >= author_pos:
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
        if user_pos >= author_pos:
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
            if user_pos >= author_pos:
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
