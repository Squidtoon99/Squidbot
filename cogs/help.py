from discord.ext import commands
import discord
import json 

class MySelect(discord.ui.Select):
    def __init__(self, bot,  options, *, custom_id="CommandRuleList:selector:1", ):
        super().__init__(custom_id=custom_id, )
        self.bot = bot
        for i in options:
            self.add_option(**i)
        
    async def callback(self, interaction : discord.Interaction):
        await interaction.response.defer()
        
        msg = await interaction.original_message()

        
        embed = msg.embeds[0]
        if embed.author.name != interaction.user.name:
            return # can't respond twice stupid discord # await interaction.response.send_message("This is not your selector", ephemeral=True)
        view = CommandRuleList(self.bot, selected=self.values[0])
        data = json.loads(self.values[0])
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
    def __init__(self, bot, selected=None):
    
        self.back = {"label":"back", "value":json.dumps({"type":"selector", "value":"back"})}
        super().__init__(timeout=None)
        items = [dict(label = key, value = json.dumps({"type":"plugin", "value":key})) for key in bot.plugins.keys()]
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
                
                items = [dict(label = cmd.qualified_name, value=json.dumps({"type":"command", "value":cmd.qualified_name, "plugin":cmd.cog.qualified_name})) for cmd in sorted(bot.get_cog(v).walk_commands(), key= lambda cmd : cmd.qualified_name)] + [self.back]
            
        self.add_item(MySelect(bot, list(items)))

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self._original_help_command = bot.help_command
        self._view = None
        bot.help_command = None
        #bot.help_command.cog = self

    @commands.command() 
    async def help(self, ctx):
        await ctx.send(embed=discord.Embed(description='Select a `Plugin`', color=self.bot.color).set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url), view=self.view)

    @property 
    def view(self):
        if not self._view:
            self._view = CommandRuleList(self.bot)
            self.bot.add_view(self._view)
        return self._view
    
    @commands.Cog.listener()
    async def on_ready(self):
        self.view 

    def cog_unload(self):
        self.bot.help_command = self._original_help_command