import logging
import traceback

import discord
from datetime import datetime
from discord.ext import commands
from ink.utils import ErrorEmbed

log = logging.getLogger(__name__)


def perm_format(perm):
    return perm.replace("_", " ").replace("guild", "server").title()


class ErrorHandler(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.on_command_error = self.error_handler

    async def error_handler(self, ctx, error, bypass=False):
        n = "\n"
        if hasattr(ctx.command, "on_error") and not bypass:
            async for _yield in ctx.command.on_error(ctx, error):
                yield _yield
            return
        if hasattr(ctx.cog, "on_error"):
            async for _yield in ctx.cog.on_error(ctx, error) and not bypass:
                yield _yield

        elif isinstance(error, commands.CommandNotFound):
            yield None  # nothing here handlers will ignore
        elif isinstance(error, commands.NoPrivateMessage):
            yield ErrorEmbed(
                "No DM Command", "This command cannot be used in direct message."
            )

        elif isinstance(error, commands.PrivateMessageOnly):
            yield ErrorEmbed(
                "DM Only Command",
                "This command can only be used in direct message.",
            )

        elif isinstance(
            error, (commands.MissingRequiredArgument, commands.BadArgument)
        ):
            embed = ErrorEmbed(
                "Incorrect Arguments",
                "Check the arguments you provided for the command"
                # f"`{ctx.prefix}support` if you don't know what went wrong.",
            )
            usage = (
                "\n".join(
                    [
                        ctx.prefix + ctx.command.qualified_name + " " + x.strip()
                        for x in ctx.command.usage.split("\n")
                    ]
                )
                if ctx.command.usage
                else f"{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}"
            )
            embed.add_field("Usage", f"```{usage}```")
            yield embed
        elif isinstance(error, commands.NotOwner):
            yield ErrorEmbed(
                "Permission Denied", "You do not have permission to use this command."
            )

        elif isinstance(error, commands.MissingPermissions):
            for check in ctx.command.checks:
                try:
                    # You can pretty much loop these to get all checks from the command.
                    check(0)  # This would raise an error, because `0` is passed as ctx
                except Exception as e:
                    *_, last_frame = traceback.walk_tb(
                        e.__traceback__
                    )  # Iterate through the generator and get the last element
                    frame = last_frame[0]  # get the first element to get the trace
                    permissions = frame.f_locals.get(
                        "perms"
                    )  # Output: {'administrator': True, 'manage_messages': True}
                    if permissions and all(
                        perm in permissions for perm in error.missing_permissions
                    ):
                        break

            yield ErrorEmbed(
                "Permission Denied",
                "You do not have permission to use this command. ```diff\n"
                f"{n.join(['+ ' + perm_format(x) for x in permissions if x not in error.missing_permissions])}".strip()
                + n
                + f"{n.join(['- ' + perm_format(x) for x in error.missing_permissions])}".strip()
                + "\n```",
            )

        elif isinstance(error, commands.BotMissingPermissions):
            for check in ctx.command.checks:
                try:
                    # You can pretty much loop these to get all checks from the command.
                    check(0)  # This would raise an error, because `0` is passed as ctx
                except Exception as e:
                    *_, last_frame = traceback.walk_tb(
                        e.__traceback__
                    )  # Iterate through the generator and get the last element
                    frame = last_frame[0]  # get the first element to get the trace
                    permissions = frame.f_locals.get(
                        "perms"
                    )  # Output: {'administrator': True, 'manage_messages': True}
                    if permissions and all(
                        perm in permissions for perm in error.missing_permissions
                    ):
                        break
            yield ErrorEmbed(
                "Squid Missing Permissions",
                "I do not have the correct permissions to execute this command. ```diff\n"
                f"{n.join(['+ ' + perm_format(x) for x in permissions if x not in error.missing_permissions])}".strip()
                + n
                + f"{n.join(['- ' + perm_format(x) for x in error.missing_permissions])}".strip()
                + "\n```",
            )

        elif isinstance(error, discord.HTTPException):
            yield ErrorEmbed(
                "Unknown HTTP Exception",
                f"Please report this in the support server.\n```{error.text}````",
            )

        elif isinstance(error, commands.CommandInvokeError):
            log.error(
                f"{error.original.__class__.__name__}: {error.original} (In {ctx.command.name})\n"
                f"Traceback:\n{''.join(traceback.format_tb(error.original.__traceback__))}"
            )

            yield ErrorEmbed(
                "Unknown Error",
                "Please report this in the support server.\n"
                f"```{error.original.__class__.__name__}: {error.original}```",
            )


def setup(bot):
    bot.add_cog(ErrorHandler(bot))
