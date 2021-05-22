from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from asyncio import set_event_loop
from discord.ext.commands import Cog
import traceback

__all__ = (
    "CustomEventHandler",
    "Watcher",
)


class CustomEventHandler(FileSystemEventHandler):
    def on_modified(self, event):
        print(f'event type: {event.event_type}  path : {event.src_path}')
    """
    The event handler for
    """

    def __init__(self, bot,):
        self.bot = bot
        self.log = bot.log.getChild("FileReloader")
        self.set_loop = False
        self.modules = bot.extensions

    def dispatch(self, event):
        
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

def setup(bot):
    bot.add_cog(Watcher(bot))