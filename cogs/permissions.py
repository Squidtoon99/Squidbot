from discord.components import SelectOption
from ink.core.command import SquidCommand
from discord.ext import commands 
from ink.core import squidcommand
from discord import ui
import json
import discord  


class MySelect(discord.ui.Select):
    def __init__(self, ctx,  options, *, custom_id="CommandRuleList:selector:1", ):
        super().__init__(custom_id=custom_id, )
        self.bot = ctx.bot
        self.author_id = ctx.author.id 
        self.ctx = ctx
        for i in options:
            self.add_option(**i)
        
    async def callback(self, interaction : discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("This is not your selector", ephemeral=True)
        await interaction.response.defer()
        
        msg = await interaction.original_message()
        view = CommandRuleList(self.ctx, selected=self.values[0])
        data = json.loads(self.values[0])
        embed = msg.embeds[0]
        if data["type"] != "selector":
            embed.title = data["type"].title() + ": " + data["value"].title()
        else:
            embed.title = ""

        if data["type"] == "command":
            cmd = self.bot.get_command(data["value"])
            embed.description = cmd.help
        elif data["type"] == "plugin":
            cog = self.bot.get_cog(data["value"])
            embed.description = "\n".join([f"{pos}. {cmd.qualified_name}" for pos, cmd in enumerate(sorted(cog.walk_commands(), key=lambda x : x.qualified_name), start=1)])
        elif data["type"] == "selector":
            embed.description = "Select a value to get started"
        await msg.edit(view=view, embed=embed)

class CommandRuleList(discord.ui.View):
    def __init__(self, ctx, selected=None):
    
        self.back = {"label":"back", "value":json.dumps({"type":"selector", "value":"back"})}
        super().__init__(timeout=None)
        items = [dict(label = key, value = json.dumps({"type":"plugin", "value":key})) for key in ctx.bot.plugins.keys()]
        if selected:
            data = json.loads(selected)
            t = data.get("type", None)
            v = data.get("value",None)
            if t == "selector":
                if v != "back":
                    pass #idk what to do here 
            elif t in ("plugin", "command"):
                if t == "command":
                    v = data["plugin"]
                
                items = [dict(label = cmd.qualified_name, value=json.dumps({"type":"command", "value":cmd.qualified_name, "plugin":cmd.cog.qualified_name})) for cmd in sorted(ctx.bot.get_cog(v).walk_commands(), key= lambda cmd : cmd.qualified_name)] + [self.back]
            
        self.add_item(MySelect(ctx, list(items)))

class PermissionSelector(discord.ui.View):
    def __init__(self, ctx):
        self.bot = ctx.bot 
        self.ctx= ctx 
        super().__init__(timeout=None)
    
    async def handler(self, b : ui.Button, i : discord.Interaction) -> None:
        
        await i.response.defer()
        msg = await i.original_message()
        components = msg.components
        async with self.ctx.storage as s:
            s[f"{b.custom_id}-{msg.channel.id}-{msg.id}"] = b.values[0]
        
    @discord.ui.select(custom_id="PermissionSelector:listscreen:1", options=[discord.SelectOption(label=i) for i in ["Whitelist", "Blacklist"]])
    async def listselector(self, button : ui.Button, interaction : discord.Interaction) -> None:
        await self.handler(b=button, i=interaction)
    
    @discord.ui.select(custom_id="PermissionSelector:choicescreen:1", options=[discord.SelectOption(label=i) for i in  [
        "Plugin",
        "Command",
    ]])
    async def optionselector(self, button : ui.Button, interaction : discord.Interaction) -> None:
        await self.handler(b=button, i=interaction)

class SortFlags(commands.FlagConverter, delimiter=" ", prefix="--", case_insensitive=True):
    type: str = "all"
    group: str = "all"

class Permissions(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.log = bot.log.getChild(type(self).__name__)
    
    @commands.group("permissions", cls=SquidCommand, aliases=["p"])
    async def perms_base(self, ctx):
        """
        Complex permissions system for the bot.

        Priority (lower overides higher) 

        **Groups**"
        `-` Plugin: 
            A group of commands. Adding a rule to a plugin will affect all commands associated with the plugin 

            :Priority 3 

        `-` Command Group:
            A group of commands that have similar permissions/usage (ban, massban, tempban). Adding a rule to a command group will implement the rule over the entire group 

            :Priority 2

        `-` Command: 
            :A singular command. Adding a rule to it will only affect the command specified.

            :Priorty 1
        """
        if ctx.invoked_subcommand is None:
            yield ctx.command.help
    
    @squidcommand("permissionrules", aliases=["pr"])
    async def permissions_listrules(self, ctx):
        await ctx.reply(embed=discord.Embed(color=self.bot.color, description="Select a value to get started"), view=CommandRuleList(ctx))

    @squidcommand("addrule", aliases=["arule"])
    async def permissionsrules(self, ctx, *, flags : SortFlags):    
        await ctx.reply(embed=discord.Embed(color=self.bot.color, description="\u200b"), view=PermissionSelector(ctx))