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
        bot.on_command_error = self.error_handler

    async def error_handler(self, ctx, error, bypass=False):
        if (
            hasattr(ctx.command, "on_error")
            or (ctx.command and hasattr(ctx.cog, f"_{ctx.command.cog_name}__error"))
            and not bypass
        ):
            return
        n = '\n'
        if isinstance(error, commands.CommandNotFound):
            return
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send(embed=
                ErrorEmbed("No DM Command", "This command cannot be used in direct message.")
            )
        elif isinstance(error, commands.PrivateMessageOnly):
            await ctx.send(embed=
                ErrorEmbed(
                    "DM Only Command",
                    "This command can only be used in direct message.",
                )
            )
        elif isinstance(error, commands.MissingRequiredArgument) or isinstance(
            error, commands.BadArgument
        ):
            embed = ErrorEmbed(
                "Incorrect Arguments",
                "Check the arguments you provided for the command"
                f"`{ctx.prefix}support` if you don't know what went wrong.",
            )
            usage = "\n".join([ctx.prefix + x.strip() for x in ctx.command.usage.split("\n")])
            embed.add_field("Usage", f"```{usage}```")
            await ctx.send(embed=embed)
        elif isinstance(error, commands.NotOwner):
            await ctx.send(embed=
                ErrorEmbed("Permission Denied", "You do not have permission to use this command.")
            )
        elif isinstance(error, commands.MissingPermissions):
            for check in ctx.command.checks:
                try:
                    # You can pretty much loop these to get all checks from the command.
                    check(0) # This would raise an error, because `0` is passed as ctx
                except Exception as e:
                    *_, last_frame = traceback.walk_tb(e.__traceback__) # Iterate through the generator and get the last element
                    frame = last_frame[0] # get the first element to get the trace
                    permissions = frame.f_locals.get('perms') # Output: {'administrator': True, 'manage_messages': True}
                    if permissions and all([perm in permissions for perm in error.missing_permissions]):
                        break

            await ctx.send(embed=
                ErrorEmbed(
                    "Permission Denied",
                    "You do not have permission to use this command. ```diff\n"
                    f"{n.join(['+ ' + perm_format(x) for x in permissions if x not in error.missing_permissions])}".strip() + n +
                    f"{n.join(['- ' + perm_format(x) for x in error.missing_permissions])}".strip() + 
                    "\n```",

                )
            )
        elif isinstance(error, commands.BotMissingPermissions):
            for check in ctx.command.checks:
                try:
                    # You can pretty much loop these to get all checks from the command.
                    check(0) # This would raise an error, because `0` is passed as ctx
                except Exception as e:
                    *_, last_frame = traceback.walk_tb(e.__traceback__) # Iterate through the generator and get the last element
                    frame = last_frame[0] # get the first element to get the trace
                    permissions = frame.f_locals.get('perms') # Output: {'administrator': True, 'manage_messages': True}
                    if permissions and all([perm in permissions for perm in error.missing_permissions]):
                        break
            await ctx.send(embed=
                ErrorEmbed(
                    "Squid Missing Permissions",
                    "I do not have the correct permissions to execute this command. ```diff\n"
                    f"{n.join(['+ ' + perm_format(x) for x in permissions if x not in error.missing_permissions])}".strip() + n +
                    f"{n.join(['- ' + perm_format(x) for x in error.missing_permissions])}".strip() + 
                    "\n```",

                )
            )
        elif isinstance(error, discord.HTTPException):
            await ctx.send(embed=
                ErrorEmbed(
                    "Unknown HTTP Exception",
                    f"Please report this in the support server.\n```{error.text}````",
                )
            )
        elif isinstance(error, commands.CommandInvokeError):
            log.error(
                f"{error.original.__class__.__name__}: {error.original} (In {ctx.command.name})\n"
                f"Traceback:\n{''.join(traceback.format_tb(error.original.__traceback__))}"
            )

            try:
                await ctx.send(embed=
                    ErrorEmbed(
                        "Unknown Error",
                        "Please report this in the support server.\n"
                        f"```{error.original.__class__.__name__}: {error.original}```",
                    )
                )
            except discord.HTTPException:
                pass


def setup(bot):
    bot.add_cog(ErrorHandler(bot))