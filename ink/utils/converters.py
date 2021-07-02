from discord import Member, Role, utils
from discord.ext.commands import (
    BadArgument,
    CommandError,
    Converter,
    MemberConverter,
    MemberNotFound,
    RoleConverter,
    RoleNotFound,
)
from fuzzywuzzy import process

__all__ = (
    "TextMember",
    "TextRole",
)


class TextMember(
    Converter
):  # so users don't have to type entire names / ping for members
    async def convert(self, ctx, argument) -> Member:
        try:
            return await MemberConverter().convert(ctx, argument)
        except (BadArgument, MemberNotFound):
            result = utils.find(
                lambda x: x.name.lower() == argument.lower(), ctx.guild.members
            )

            if result is not None:
                return result

            name, ra = process.extractOne(argument, [i.name for i in ctx.guild.members])

            if ra >= 60:  # lower because member's have f*cked up names
                result = utils.get(
                    ctx.guild.members, name=name
                )  # this could be dangerous with multiple members
                return result
        raise CommandError(f"I couldn't find a member in your server named {argument}")


class TextRole(Converter):
    async def convert(self, ctx, argument) -> Role:
        if argument:
            argument = argument.strip()
        try:
            return await RoleConverter().convert(ctx, argument)
        except (BadArgument, RoleNotFound):
            result = utils.find(
                lambda x: x.name.lower() == argument.lower(), ctx.guild.roles
            )
            if result is not None:
                return result
            try:
                name, ra = process.extractOne(
                    argument, [x.name for x in ctx.guild.roles]
                )
            except:
                pass
            else:
                if ra >= 60:  # loop?
                    result = utils.get(ctx.guild.roles, name=name)
                    return result
        raise RoleNotFound(argument)
