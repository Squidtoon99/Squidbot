import asyncio
import functools
import inspect
from typing import Optional

from discord.ext.commands import Command, CommandError, CommandInvokeError
from discord.ext.commands._types import _BaseCommand
from discord.ext.commands.cooldowns import CooldownMapping

__all__ = ("SquidCommand", "squidcommand")


def hooked_wrapped_callback(command, ctx, coro):
    @functools.wraps(coro)
    async def wrapped(*args, **kwargs):
        try:
            if inspect.isasyncgenfunction(coro):
                async for _yield in coro(*args, **kwargs):
                    yield _yield
            else:
                yield await coro(*args, **kwargs)
        except CommandError:
            ctx.command_failed = True
            raise
        except asyncio.CancelledError:
            ctx.command_failed = True
            yield None
        except Exception as exc:
            ctx.command_failed = True
            raise CommandInvokeError(exc) from exc
        finally:
            if command._max_concurrency is not None:
                await command._max_concurrency.release(ctx)

            await command.call_after_hooks(ctx)

    return wrapped


class SquidCommand(Command):
    def __init__(self, func, **kwargs):
        self.name = name = kwargs.get("name") or func.__name__
        if not isinstance(name, str):
            raise TypeError("Name of a command must be a string.")

        self.callback = func
        self.enabled = kwargs.get("enabled", True)

        help_doc = kwargs.get("help")
        if help_doc is not None:
            help_doc = inspect.cleandoc(help_doc)
        else:
            help_doc = inspect.getdoc(func)
            if isinstance(help_doc, bytes):
                help_doc = help_doc.decode("utf-8")

        self.help = help_doc

        self.brief = kwargs.get("brief")
        self.usage = kwargs.get("usage")
        self.rest_is_raw = kwargs.get("rest_is_raw", False)
        self.aliases = kwargs.get("aliases", [])

        if not isinstance(self.aliases, (list, tuple)):
            raise TypeError(
                "Aliases of a command must be a list or a tuple of strings."
            )

        self.description = inspect.cleandoc(kwargs.get("description", ""))
        self.hidden = kwargs.get("hidden", False)

        try:
            checks = func.__commands_checks__
            checks.reverse()
        except AttributeError:
            checks = kwargs.get("checks", [])
        finally:
            self.checks = checks

        try:
            cooldown = func.__commands_cooldown__
        except AttributeError:
            cooldown = kwargs.get("cooldown")
        finally:
            self._buckets = CooldownMapping(cooldown)

        try:
            max_concurrency = func.__commands_max_concurrency__
        except AttributeError:
            max_concurrency = kwargs.get("max_concurrency")
        finally:
            self._max_concurrency = max_concurrency

        self.require_var_positional = kwargs.get("require_var_positional", False)
        self.ignore_extra = kwargs.get("ignore_extra", True)
        self.cooldown_after_parsing = kwargs.get("cooldown_after_parsing", False)
        self.cog = None

        # bandaid for the fact that sometimes parent can be the bot instance
        parent = kwargs.get("parent")
        self.parent = parent if isinstance(parent, _BaseCommand) else None

        try:
            before_invoke = func.__before_invoke__
        except AttributeError:
            self._before_invoke = None
        else:
            self.before_invoke(before_invoke)

        try:
            after_invoke = func.__after_invoke__
        except AttributeError:
            self._after_invoke = None
        else:
            self.after_invoke(after_invoke)

    async def invoke(self, ctx) -> Optional[dict]:
        await self.prepare(ctx)

        # terminate the invoked_subcommand chain.
        # since we're in a regular command (and not a group) then
        # the invoked subcommand is None.
        ctx.invoked_subcommand = None
        ctx.subcommand_passed = None
        injected = hooked_wrapped_callback(self, ctx, self.callback)
        if inspect.isasyncgenfunction(injected):
            async for _yield in injected(*ctx.args, **ctx.kwargs):
                yield _yield
        else:
            yield await injected(*ctx.args, **ctx.kwargs)

    async def reinvoke(self, ctx, *, call_hooks=False):
        ctx.command = self
        await self._parse_arguments(ctx)

        if call_hooks:
            await self.call_before_hooks(ctx)

        ctx.invoked_subcommand = None
        try:
            resp = await self.callback(*ctx.args, **ctx.kwargs)
        except:
            ctx.command_failed = True
            raise
        finally:
            if call_hooks:
                await self.call_after_hooks(ctx)
            return resp


def squidcommand(name=None, cls=SquidCommand, **attrs):
    def decorator(func):
        if isinstance(func, Command):
            raise TypeError("Callback is already a command.")
        return cls(func, name=name, **attrs)

    return decorator
