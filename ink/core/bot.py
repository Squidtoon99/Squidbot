import inspect
import discord
from discord.ext import commands
from discord.ext.commands import errors
import types
import asyncio
from jishaku.repl import AsyncCodeExecutor, all_inspections
from jishaku.functools import AsyncSender
from jishaku.paginators import PaginatorInterface, WrappedPaginator
import logging, traceback
import io 

from jishaku.repl.scope import Scope
__all__ = ("SquidBot",)

class SquidBot(commands.AutoShardedBot):
    def __init__(self, *, config: dict):

        # config
        self.config = config

        # config 
        self.log = logging.getLogger(type(self).__name__)

        # scope for jsk 
        self.scope = Scope()

        super().__init__(allowed_mentions=discord.AllowedMentions.none(), **config)

        for ext in config.get('extensions',[]):
            try:
                self.load_extension(ext)
            except:
                traceback.print_exc() 
                if config.get('raise-extension-error', False):
                    raise
        
        self.run(config['token'], reconnect=True)

    async def on_ready(self) -> None:
        print("Connected!\n"+ '\n'.join([
            f"Extensions: {self.config.get('extensions')}",
            f"Prefix: {self.config.get('command_prefix')}",
            f"User: {self.user.name} ({self.user.id})",
            f"Guilds: {len(self.guilds)}",
            f"Users: {sum([i.member_count for i in self.guilds])}",
        ]))

    async def invoke(self, ctx):
        if ctx.command is not None:
            self.dispatch('command', ctx)
            try:
                if await self.can_run(ctx, call_once=True):
                    resp = ctx.command.invoke(ctx)
                    if inspect.iscoroutine(resp):
                        yield await resp 
                    else:
                        async for _yield in resp:
                            yield _yield
                else:
                    raise errors.CheckFailure('The global check once functions failed.')
            except errors.CommandError as exc:
                await ctx.command.dispatch_error(ctx, exc)
        elif ctx.invoked_with:
            exc = errors.CommandNotFound(f'Command "{ctx.invoked_with}" is not found')
            self.dispatch('command_error', ctx, exc)
        yield None
        #else:
            #await super(self, commands.AutoShardedBot).invoke(ctx)

    async def on_message(self, message : discord.Message) -> None:
        if message.author.bot:
            return

        ctx = await self.get_context(message)
        coro = self.invoke(ctx)

        await self.process_output(ctx, coro)

    async def on_command_error(self, ctx, error):
        await ctx.reply(f"{type(error).__name__}: {error}")
        raise error

    async def process_output(self, ctx : commands.Context, coro ): 
         
        cmd = "async for _yield in coro:\n yield _yield"
        arg_dict = {'coro':coro}

        scope = self.scope

        executor = AsyncCodeExecutor(cmd, scope, arg_dict=arg_dict)
        async for send, result in AsyncSender(executor):
        
            if result is None:
                continue

            self.last_result = result

            if isinstance(result, discord.File):
                send(await ctx.reply(file=result))
            elif isinstance(result, discord.Embed):
                send(await ctx.reply(embed=result))
            elif isinstance(result, PaginatorInterface):
                send(await result.send_to(ctx))
            else:
                if not isinstance(result, str):
                    # repr all non-strings
                    result = repr(result)

                if len(result) <= 2000:
                    if result.strip() == '':
                        result = "\u200b"

                    send(await ctx.reply(result.replace(self.http.token, "[token omitted]")))

                elif len(result) < 50_000:  # File "full content" preview limit
                    # Discord's desktop and web client now supports an interactive file content
                    #  display for files encoded in UTF-8.
                    # Since this avoids escape issues and is more intuitive than pagination for
                    #  long results, it will now be prioritized over PaginatorInterface if the
                    #  resultant content is below the filesize threshold
                    send(await ctx.reply(file=discord.File(
                        filename="output.py",
                        fp=io.BytesIO(result.encode('utf-8'))
                    )))

                else:
                    # inconsistency here, results get wrapped in codeblocks when they are too large
                    #  but don't if they're not. probably not that bad, but noting for later review
                    paginator = WrappedPaginator(prefix='```py', suffix='```', max_size=1985)

                    paginator.add_line(result)

                    interface = PaginatorInterface(ctx.bot, paginator, owner=ctx.author)
                    
                    send(await interface.send_to(ctx))
        scope.clear_intersection(arg_dict)