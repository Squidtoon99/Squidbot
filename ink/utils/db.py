import asyncio
from typing import List, Optional, Tuple, Union
import orjson
from discord.ext import commands

__all__ = ("get_storage", "get_config", "RedisStorage", "RedisDict")


class RedisStorage:
    def __init__(self, guild_id, plugin_name, redis, extra_prefix=None):
        self.guild_id = guild_id
        self.plugin_name = plugin_name

        self.prefix = "{}.{}:".format(plugin_name, guild_id)
        if extra_prefix:
            self.prefix += extra_prefix

        self.redis = redis

    def set(self, key, value, ex=None):
        key = self.prefix + key
        if not ex:
            return self.redis.set(
                key,
                value,
            )
        else:
            return self.redis.setex(key, ex, value)

    def get(self, key, *a, **k):
        key = self.prefix + key
        return self.redis.get(key, *a, **k)

    def delete(self, *keys):
        keys = [self.prefix + keyitem for keyitem in keys]
        return self.redis.delete(*keys)

    def smembers(self, key, *a, **k):
        key = self.prefix + key
        return self.redis.smembers(key, *a, **k)

    def sadd(self, key, *values, **k):
        key = self.prefix + key
        return self.redis.sadd(key, *values, **k)

    def srem(self, key, *values, **k):
        key = self.prefix + key
        return self.redis.srem(key, *values, **k)

    def exists(self, key, *a, **k):
        key = self.prefix + key
        return self.redis.exists(key, *a, **k)

    def scan_iter(self, *ar, match="", **kw):
        match = self.prefix + match
        return self.redis.scan_iter(*ar, match=match, **kw)

    def hmset(self, key, value, *a, **k):
        key = self.prefix + key
        return self.redis.hmset(key, value, *a, **k)

    def incr(self, key, *a, **k):
        return self.redis.incr(self.prefix + key, *a, **k)

    def decr(self, key, *a, **k):
        return self.redis.incr(self.prefix + key, *a, **k)

    def ttl(self, key, *a, **k):
        return self.redis.ttl(self.prefix + key, *a, **k)

    def expire(self, key, *a, **k):
        return self.redis.expire(self.prefix + key, *a, **k)

    def zincrby(self, name, key, value, *a, **k):
        return self.redis.zincrby(self.prefix + name, key, value, *a, **k)

    def zadd(self, name, *a, **k):
        return self.redis.zadd(self.prefix + name, *a, **k)

    def zrevrange(self, name, *a, **k):
        return self.redis.zrevrange(self.prefix + name, *a, **k)

    def zrem(self, name, value, *values, **k):
        return self.redis.zrem(self.prefix + name, value, *values, **k)

    def zscore(self, name, *a, **k):
        return self.redis.zscore(self.prefix + name, *a, **k)

    def zcount(self, name, *a, **k):
        return self.redis.zcount(self.prefix + name, *a, **k)

    def zscan_iter(self, name, *a, **k):
        return self.redis.zscan_iter(self.prefix + name, *a, **k)

    def hget(self, name, value):
        return self.redis.hget(self.prefix + name, value)

    def hset(self, name, value=None, *a, **k):
        return self.redis.hset(self.prefix + name, value, *a, **k)


class RedisDict(object):
    def __init__(self, redis, prefix):
        self.pipe = redis.pipeline()
        self._redis_class = redis
        self._redis = redis
        self._result = None
        self._prefix = prefix

    async def __aenter__(self):
        self._redis = self.pipe
        return self

    async def __aexit__(self, *a):
        print(a)
        if self._redis:
            self._result = await self._redis.execute()
            self._redis = self._redis_class
            self.pipe = self._redis.pipeline()

    @property
    def result(self):
        return self._result

    def _loads(self, value, l=False):
        if type(value) not in (list, tuple):
            value = [value]
            l = True
        for p, v in enumerate(value[:]):
            try:
                value[p] = orjson.loads(v)
            except orjson.JSONDecodeError:

                value[p] = v.decode("utf-8") if v else v
        if not l:
            return value
        else:
            return value[0]

    def _dumps(self, value):
        return orjson.dumps(value)

    def __setitem__(self, key: object, value: object) -> None:
        if type(value) is tuple:
            value = value[0]

        return self._redis.hset(self._prefix, self._dumps(key), self._dumps(value))

    async def __getitem__(self, key: object) -> object:
        return self._loads((await self._redis.hget(self._prefix, self._dumps(key))))

    def __repr__(self) -> str:
        return f"<RedisDict redis={repr(self._redis)} prefix='{self._prefix}'>"

    async def __len__(self) -> int:
        return await self._redis.hlen(self._prefix)

    def __delitem__(self, key: object) -> None:
        self._redis.hdel(self._prefix, self._dumps(key))

    def clear(self) -> bool:
        return self._redis.delete(self._prefix)

    def copy(self):
        return self

    def has_key(self, k: object) -> bool:
        return self._redis.hexists(self._prefix, self._dumps(k))

    def update(self, mapping: dict):
        return self._redis.hmset(
            self._prefix, {self._dumps(k): self._dumps(v) for k, v in mapping.items()}
        )

    async def keys(self) -> Optional[List[object]]:
        return self._loads([v for v in await self._redis.hkeys(self._prefix)])

    async def values(self) -> Optional[List[Tuple[object, object]]]:
        return self._loads([v for v in await self._redis.hvals(self._prefix)])

    async def items(self) -> List[Tuple[object]]:
        return [
            (self._loads(key), self._loads(await self._redis.hget(self._prefix, key)))
            for key in await self._redis.hkeys(self._prefix)
        ]

    def pop(self, index: int = 0) -> Union[str, int, bytes]:
        key = list(self.values())[index]
        value = self.__getitem__(key)
        self.__delitem__(key)
        return value

    def __contains__(self, item: str) -> bool:
        return self._loads(item) in self.keys()

    def __iter__(self):
        return iter(self.keys())


def get_storage(
    bot: commands.AutoShardedBot, plugin_name: str, guild_id: int
) -> RedisStorage:
    return RedisDict(redis=bot.redis, prefix=f"{plugin_name}:{guild_id}:storage")


def get_config(bot: commands.AutoShardedBot, guild_id: int) -> RedisStorage:
    return RedisStorage(redis=bot.redis, guild_id=guild_id, plugin_name="Config")
