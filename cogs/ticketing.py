import traceback

from discord import Color, Embed, HTTPException, User, PermissionOverwrite
from ink.core import squidcommand
from ink.utils import TextMember, LinePaginator, Embed, ErrorEmbed
from discord.ext import commands


class Ticketing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _get_overwrites(self, ctx, roles):
        overwrites = {
            await ctx.guild.default_role(): PermissionOverwrite(read_messages=False)
        }

        for role in roles:
            role = await ctx.guild.get_role(role)
            if role:
                overwrites[role] = PermissionOverwrite(
                    read_messages=True,
                    read_message_history=True,
                    send_messages=True,
                    embed_links=True,
                    attach_files=True,
                    add_reactions=True,
                )

        return overwrites

    @commands.bot_has_permissions(
        manage_channels=True,
        manage_roles=True,
        read_messages=True,
        read_message_history=True,
        send_messages=True,
        embed_links=True,
        attach_files=True,
        add_reactions=True,
    )
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    @squidcommand(description="Set up tickets", usage="ticketsetup")
    async def ticketsetup(self, ctx):
        msg = await ctx.send(embed=Embed("Setting up..."))

        data = await tools.get_data(self.bot, ctx.guild.id)
        if await ctx.guild.get_channel(data[2]):
            await msg.edit(ErrorEmbed("The bot has already been set up."))
            return

        overwrites = await self._get_overwrites(ctx, data[3])
        category = await ctx.guild.create_category(
            name="ModMail", overwrites=overwrites
        )
        logging_channel = await ctx.guild.create_text_channel(
            name="modmail-log", category=category
        )

        async with self.bot.pool.acquire() as conn:
            await conn.execute(
                "UPDATE data SET category=$1, logging=$2 WHERE guild=$3",
                category.id,
                logging_channel.id,
                ctx.guild.id,
            )

        await ctx.send(
            Embed(
                "Setup",
                "Everything has been set up! Next up, you can give your staff access to Tickets"
                f"commands using `{ctx.prefix}accessrole [roles]` (by default, any user with the "
                f"administrator permission has full access). You can also test things out by "
                f"direct messaging me. Check out more information and configurations with "
                f"`{ctx.prefix}help`.",
            )
        )


def setup(bot):
    bot.add_cog(Ticketing(bot))
