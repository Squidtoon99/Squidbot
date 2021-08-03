import inspect
import os
import traceback
from asyncio import set_event_loop
from discord.ext.commands import Cog
from discord.ext.tasks import loop
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

__all__ = (
    "CustomEventHandler",
    "Watcher",
)


class CustomEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        print(f"event type: {event.event_type}  path : {event.src_path}")

    """
    The event handler for file changes
    """

    def __init__(
        self,
        bot,
    ):
        self.bot = bot
        self.log = bot.log.getChild("FileReloader")
        self.set_loop = False
        self.modules = bot.extensions

    def dispatch(self, event):
        print(event)
        if event.is_directory:
            return
        if not event.src_path.endswith(".py"):
            return

        if not self.set_loop:
            set_event_loop(self.bot.loop)
            self.set_loop = True

        module = event.src_path[:-3].replace("\\", ".")[2:]
        if module in self.modules.keys():
            self.log.debug(f"Reloading {module}")
            try:
                self.bot.reload_extension(module)
            except BaseException:
                self.log.warning(f"Could not reload {module}")
                traceback.print_exc()
            else:
                self.log.info(f"Reloaded {module}")


class Watcher(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.log = bot.log.getChild(type(self).__name__)
        self.path = "."
        self.observer = Observer()
        self.observer.schedule(CustomEventHandler(bot), self.path, recursive=True)
        self.start()

    def start(self):
        self.log.debug("Watching for plugin reloads")
        self.observer.start()

    def stop(self):
        self.observer.stop()
        self.observer.join()

    def cog_unload(self):
        self.stop()


class MonkeyWatcher(Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cache = {}
        self.log = bot.log.getChild(type(self).__name__)

        self.watcher.start()

    @loop(seconds=1)
    async def watcher(self):
        for name, module in self.bot.extensions.copy().items():
            folder = False
            if module.__file__.endswith("__init__.py"):
                # it's a folder
                folder = True
                fpath = module.__file__[:-11]
            if folder:
                stat = {
                    name: int(os.stat(os.path.join(fpath, name)).st_mtime)
                    for name in os.listdir(fpath)
                    if name.endswith(".py")
                }
            else:
                stat = int(os.stat(inspect.getfile(module)).st_mtime)

            if name not in self.cache:
                self.cache[name] = stat
                continue

            if stat != self.cache.get(name):
                self.cache[name] = stat
                self.log.debug(f"Reloading: {name}")
                try:
                    self.bot.reload_extension(name)
                except:
                    traceback.print_exc()
                else:
                    self.log.info(f"Reloaded: {name}")

    @watcher.before_loop
    async def waiter(self):
        await self.bot.wait_until_ready()
        return True

    def cog_unload(self):
        self.watcher.stop()


def setup(bot):
    import sys

    if sys.platform == "win32":
        cog = Watcher(bot)
    else:
        cog = MonkeyWatcher(bot)

    bot.add_cog(cog)
