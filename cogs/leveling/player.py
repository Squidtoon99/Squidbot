import redis
import discord

lvls_xp = [5 * (i ** 2) + 50 * i + 100 for i in range(200)]


def get_level_from_xp(xp):
    remaining_xp = int(xp)
    lvl = 0
    while remaining_xp >= lvls_xp[lvl]:
        remaining_xp -= lvls_xp[lvl]
        lvl += 1
    return lvl


class Player:
    def __init__(
        self, member: discord.Object, guild: discord.Object, redis: redis.StrictRedis
    ):
        self.member_id: int = member.id
        self.guild_id: int = guild.id
        self.key = f"lb:{self.guild_id}"
        self._storage = redis

    @property
    def lvl(self) -> int:
        return get_level_from_xp(self.xp)

    @property
    def rank(self) -> int:
        return int(self._storage.zrevrank(self.key, "{}:xp".format(self.member_id))) + 1

    @property
    def xp(self) -> int:
        return int(self._storage.zscore(self.key, "{}:xp".format(self.member_id)) or 0)

    @xp.setter
    def xp(self, xp) -> int:
        return self._storage.zadd(self.key, {"{}:xp".format(self.member_id): xp})
