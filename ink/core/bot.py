import importlib
import inspect
import io
import logging
import sys
import traceback
import aioredis
import discord
from discord.ext import commands
from discord.ext.commands import errors
from discord.ext.commands.bot import _is_submodule
from discord.ext.colors import XKCDColor
from jishaku.functools import AsyncSender
from jishaku.paginators import PaginatorInterface, WrappedPaginator
from jishaku.repl import AsyncCodeExecutor
from jishaku.repl.scope import Scope
from jishaku.shim.paginator_170 import PaginatorEmbedInterface
from ink.utils import RedisDict
from .context import Context
import locale
import os 
import aiohttp 
import redis 

locale.setlocale(locale.LC_ALL,'en_US.UTF-8')
__all__ = ("SquidBot",)


class SquidBot(commands.AutoShardedBot):
    def __init__(self, *, config: dict):

        # config
        self.config = config

        # config
        self.log = logging.getLogger(type(self).__name__)
        self.color = getattr(XKCDColor, self.config.get('color','blurple'), discord.Color.blurple)()
        self.mention_author = self.config.get('mention-author', False)

        # databases 
        self.redis = None
        self.sync_redis = None 

        # aiohttp session for downloading 
        self.session = None #
        # scope for jsk
        self.scope = Scope()

        super().__init__(allowed_mentions=discord.AllowedMentions.none(),intents=discord.Intents.all(), **config)

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

    @property 
    def plugins(self):
        return {v:k for v,k in self.cogs.items() if v.lower() in self.config['plugins']}
    def storage(self, plugin_name : str, guild_id : int):
        return RedisDict(self.redis, prefix=f'storage:{plugin_name}:{guild_id}')

    async def create(self):
        uri = os.getenv('redishost', self.config.get('redis-uri'))
        if self.redis is None:
            print("connecting to redis")
            
            self.redis = await aioredis.create_redis(
                uri,
                encoding='utf8'
            )
            await self.redis.ping()

        if self.sync_redis is None:
            print("connecting to sync redis")
            if uri.startswith('redis://'):
                uri = uri[8:]
            hostport, *options = uri.split(",")
            host, _, port = hostport.partition(":")
            arguments = {}
            for option in options:
                opt, _, value = option.partition("=")
                if opt == "port":
                    value = int(value)
                elif opt == "ssl":
                    value = value.lower() == "true"
                elif opt == "abortConnect":
                    continue
                arguments[opt] = value
            self.sync_redis = redis.StrictRedis(host, port=int(port), decode_responses=True, **arguments)
            
            self.sync_redis.ping()

        if self.session is None:
            self.session = aiohttp.ClientSession(loop=self.loop)

    async def close(self):
        await self.session.close()
        return await super().close()

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
                        self.add_cog(obj(bot=self))
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


    async def on_connect(self) -> None:
        await self.create() 

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
        

        ctx = await self.get_context(message, cls=Context)
        self.dispatch("context", ctx)
        coro = self.invoke(ctx)
        if not message.author.bot:
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
            kwargs = {'mention_author':self.mention_author}
            perms = ctx.channel.permissions_for(ctx.me)
            if isinstance(result, discord.File):
                kwargs['file'] = result 
            elif isinstance(result, PaginatorInterface):
                send(await result.send_to(ctx))
                continue
            elif isinstance(result, WrappedPaginator):
                if perms.embed_links or not perms.send_messages:
                    p = PaginatorEmbedInterface(ctx.bot, result, owner=ctx.author)
                else:
                    p = PaginatorInterface(ctx.bot, result, owner=ctx.author)
                
                if perms.send_messages:
                    await p.send_to(ctx)
                else:
                    await p.send_to(ctx.author)
                continue 

            elif isinstance(result, discord.Embed) and ctx.channel.permissions_for(ctx.me).embed_links:
                kwargs['embed'] = result
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
                    perms = ctx.channel.permissions_for(ctx.me)
                    if not perms.send_messages:
                        kwargs['embed'] = o_embed or discord.Embed(
                                description=result.replace(self.http.token, "[token omitted]")
                            , color=self.color)
                    else:

                        if not perms.embed_links:
                            kwargs['content'] = result 
                        else:
                            kwargs['embed'] = discord.Embed(
                                description=result.replace(self.http.token, "[token omitted]")
                            , color=self.color)
                elif len(result) < 50_000:  # File "full content" preview limit
                    # Discord's desktop and web client now supports an interactive file content
                    #  display for files encoded in UTF-8.
                    # Since this avoids escape issues and is more intuitive than pagination for
                    #  long results, it will now be prioritized over PaginatorInterface if the
                    #  resultant content is below the filesize threshold
                    kwargs['file'] = discord.File(
                                filename="output.py",
                                fp=io.BytesIO(result.encode("utf-8")),
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
                    continue
                    
            if kwargs:
                dm = False 
                missing = []
                # checks 
                p = ctx.channel.permissions_for(ctx.me)
                if not p.send_messages:
                    dm = True 
                    missing.append('- Send Messages')
                if kwargs.get('file') and not p.attach_files:
                    dm = True 
                    missing.append('- Attach Files')
                if kwargs.get('embed') and not p.embed_links:
                    dm = True 
                    missing.append('- Embeds')
                
                if dm:
                    if p.add_reactions:
                        try:
                            await ctx.message.add_reaction('‼️')
                        except:
                            pass
                    kwargs['content'] = "**Missing Permissions**\n```diff\n"+ '\n'.join(missing) + "\n```\n" + kwargs.get('content','')
                    dest = ctx.author.send 
                else:
                    dest = ctx.reply 
                
                send(await dest(**kwargs))

        scope.clear_intersection(arg_dict)
