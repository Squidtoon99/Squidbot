import asyncio
import importlib
import inspect
import io
import logging
import sys
import traceback
import types
import aioredis
import discord
from discord.ext import commands
from discord.ext.commands import errors
from discord.ext.commands.bot import _is_submodule
from jishaku.functools import AsyncSender
from jishaku.paginators import PaginatorInterface, WrappedPaginator
from jishaku.repl import AsyncCodeExecutor, all_inspections
from jishaku.repl.scope import Scope
import locale

locale.setlocale(locale.LC_ALL,'en_US.UTF-8')
__all__ = ("SquidBot",)


class SquidBot(commands.AutoShardedBot):
    def __init__(self, *, config: dict):

        # config
        self.config = config

        # config
        self.log = logging.getLogger(type(self).__name__)
        self.color = getattr(discord.Color, self.config.get('color','blurple'), discord.Color.blurple)()
        self.mention_author = self.config.get('mention-author', False)

        # databases 
        self.redis = None
        # scope for jsk
        self.scope = Scope()

        super().__init__(allowed_mentions=discord.AllowedMentions.none(), **config)

        for ext in config.get("extensions", []):
            try:
                self.load_extension(ext)
            except:
                traceback.print_exc()
                if config.get("raise-extension-error", False):
                    raise
            else:
                self.log.info(f"Loaded {ext}")

        self.run(config["token"], reconnect=True)

    async def create(self):
        self.redis = await aioredis.create_redis(
            self.config['redis-uri'],
            encoding='utf8'
        )
        await self.redis.ping()

    def load_extension(self, name, *, package=None):
        name = self._resolve_name(name, package)
        if name in self._BotBase__extensions:
            raise errors.ExtensionAlreadyLoaded(name)

        spec = importlib.util.find_spec(name)
        if spec is None:
            raise errors.ExtensionNotFound(name)

        self._load_from_module_spec(spec, name)

    def unload_extension(self, name, *, package=None):
        name = self._resolve_name(name, package)
        lib = self._BotBase__extensions.get(name)
        if lib is None:
            raise errors.ExtensionNotLoaded(name)

        self._remove_module_references(lib.__name__)
        self._call_module_finalizers(lib, name)

    def reload_extension(self, name, *, package=None):
        name = self._resolve_name(name, package)
        lib = self._BotBase__extensions.get(name)
        if lib is None:
            raise errors.ExtensionNotLoaded(name)

        # get the previous module states from sys modules
        modules = {
            name: module
            for name, module in sys.modules.items()
            if _is_submodule(lib.__name__, name)
        }

        try:
            # Unload and then load the module...
            self._remove_module_references(lib.__name__)
            self._call_module_finalizers(lib, name)
            self.load_extension(name)
        except Exception:
            # if the load failed, the remnants should have been
            # cleaned from the load_extension function call
            # so let's load it from our old compiled library.
            setup = getattr(lib, "setup", None)
            if setup:
                setup(self)
            else:
                
                for obj_name in dir(lib):
                    if obj_name.startswith('_') or obj_name in ["Cog", "CogMeta"]:
                        continue 
                    obj = getattr(lib, obj_name)
                    if isinstance(obj, commands.CogMeta):
                        self.add_cog(obj(self))
                    
            self._BotBase__extensions[name] = lib

            # revert sys.modules back to normal and raise back to caller
            sys.modules.update(modules)
            raise

    def _load_from_module_spec(self, spec, key):
        # precondition: key not in self.__extensions
        lib = importlib.util.module_from_spec(spec)
        sys.modules[key] = lib
        try:
            spec.loader.exec_module(lib)
        except Exception as e:
            del sys.modules[key]
            raise errors.ExtensionFailed(key, e) from e

        setup = getattr(lib, "setup", None)
            
        try:
            if setup:
                setup(self)
            else:
                c = True
                for obj_name in dir(lib):
                    if obj_name.startswith('_') or obj_name in ["Cog", "CogMeta"]:
                        continue
                    obj = getattr(lib, obj_name)
                    if isinstance(obj, commands.CogMeta):
                        self.add_cog(obj(self))
                        c = False
                
                if c:
                    raise errors.NoEntryPointError(key)
        except Exception as e:
            del sys.modules[key]
            self._remove_module_references(lib.__name__)
            self._call_module_finalizers(lib, key)
            raise errors.ExtensionFailed(key, e) from e
        else:
            self._BotBase__extensions[key] = lib



    async def on_ready(self) -> None:
        await self.create()
        self.log.info(
            "Connected!\n"
            + "\n".join(
                [
                    f"Extensions: {self.config.get('extensions')}",
                    f"Prefix: {self.config.get('command_prefix')}",
                    f"User: {self.user.name} ({self.user.id})",
                    f"Guilds: {len(self.guilds)}",
                    f"Users: {sum([i.member_count for i in self.guilds])}",
                ]
            )
        )

    async def invoke(self, ctx):
        if ctx.command is not None:
            self.dispatch("command", ctx)
            try:
                if await self.can_run(ctx, call_once=True):
                    resp = ctx.command.invoke(ctx)
                    if inspect.iscoroutine(resp):
                        yield await resp
                    else:
                        async for _yield in resp:
                            yield _yield
                else:
                    raise errors.CheckFailure("The global check once functions failed.")
            except errors.CommandError as exc:
                if "ErrorHandler" in self.cogs.keys():
                    async for _yield in self.cogs['ErrorHandler'].on_command_error(ctx, exc):
                        yield _yield
                else:
                    self.dispatch("command_error", ctx, exc)
        elif ctx.invoked_with:
            exc = errors.CommandNotFound(f'Command "{ctx.invoked_with}" is not found')
            if "ErrorHandler" in self.cogs.keys():
                async for _yield in self.cogs['ErrorHandler'].on_command_error(ctx, exc):
                    yield _yield
            else:
                self.dispatch("command_error", ctx, exc)
        yield None
        # else:
        # await super(self, commands.AutoShardedBot).invoke(ctx)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return

        ctx = await self.get_context(message)
        coro = self.invoke(ctx)

        await self.process_output(ctx, coro)

    async def process_output(self, ctx: commands.Context, coro):

        cmd = "async for _yield in coro:\n yield _yield"
        arg_dict = {"coro": coro}

        scope = self.scope

        executor = AsyncCodeExecutor(cmd, scope, arg_dict=arg_dict)
        async for send, result in AsyncSender(executor):

            if result is None:
                continue

            self.last_result = result

            if isinstance(result, discord.File):
                send(await ctx.reply(file=result, mention_author=self.mention_author))
            elif isinstance(result, discord.Embed) and ctx.channel.permissions_for(ctx.me).embed_links:
                send(await ctx.reply(embed=result, mention_author=self.mention_author))
            elif isinstance(result, PaginatorInterface):
                send(await result.send_to(ctx))
            else:
                o_embed = None
                if isinstance(result, discord.Embed):
                    o_embed = result
                    result = result.description 
                if not isinstance(result, str):
                    # repr all non-strings
                    result = repr(result)

                if len(result) <= 4050:
                    if result.strip() == "":
                        result = "\u200b"
                    kwargs = dict(mention_author=self.mention_author)
                    perms = ctx.channel.permissions_for(ctx.me)
                    if not perms.send_messages:
                        if perms.add_reactions:
                            try:
                                await ctx.message.add_reaction('‼️')
                            except:
                                pass
                        dest = ctx.author.send 
                        kwargs['content'] = "I cannot send messages in that channel!\n"
                        kwargs['embed'] = o_embed or discord.Embed(
                                description=result.replace(self.http.token, "[token omitted]")
                            , color=self.color)
                    else:
                        dest = ctx.reply

                        if not perms.embed_links:
                            kwargs['content'] = result 
                        else:
                            kwargs['embed'] = discord.Embed(
                                description=result.replace(self.http.token, "[token omitted]")
                            , color=self.color)

                    send(
                        await dest(**kwargs)
                    )

                elif len(result) < 50_000:  # File "full content" preview limit
                    # Discord's desktop and web client now supports an interactive file content
                    #  display for files encoded in UTF-8.
                    # Since this avoids escape issues and is more intuitive than pagination for
                    #  long results, it will now be prioritized over PaginatorInterface if the
                    #  resultant content is below the filesize threshold
                    send(
                        await ctx.reply(
                            file=discord.File(
                                filename="output.py",
                                fp=io.BytesIO(result.encode("utf-8")),
                            )
                        )
                    )

                else:
                    # inconsistency here, results get wrapped in codeblocks when they are too large
                    #  but don't if they're not. probably not that bad, but noting for later review
                    paginator = WrappedPaginator(
                        prefix="```py", suffix="```", max_size=1985
                    )

                    paginator.add_line(result)

                    interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)

                    send(await interface.send_to(ctx))
        scope.clear_intersection(arg_dict)
