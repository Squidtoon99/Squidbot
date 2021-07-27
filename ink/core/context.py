from discord.ext.commands import context
from ..utils import RedisDict 

class Context(context.Context):
    def __init__(self, **kwargs):
        super(Context, self).__init__(**kwargs)

        self._storage = None 
    
    @property 
    def storage(self):
        if self._storage is None:
            self._storage = RedisDict(self.bot.redis, prefix=f'storage:{self.cog.qualified_name if self.cog else "cog"}:{self.guild.id if self.guild else self.channel.id}')
        return self._storage