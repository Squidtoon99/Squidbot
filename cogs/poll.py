import discord
from discord.ext import commands
from ink.core import squidcommand
import shlex

def to_emoji(c):
    base = 0x1F1E6
    return chr(base + c)

g = ':blue_square:'

def make_graph(package, listdata):
    count = package[1]
    total = sum(i[1] for i in listdata)
    percent =  int(count / total * 10) 
    return "["+ "=" * (percent) +"]"

class Confirm(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.value = None
    
    async def handler(self, button, interaction):
        v = "Yes" if button.label == "👍" else "No"

        await interaction.response.defer()
        message= await interaction.original_message()
        key =f"quickpoll:results:{interaction.channel_id}:{message.id}"
        await self.bot.redis.hset(key, str(interaction.user.id), v)
        await self.bot.redis.expire(key, 86400 )
        data = await self.bot.redis.hgetall(key)
        listdata = [(i, len([1 for k in data.values() if k == i])) for i in ["Yes", "No"]]

        text = '\n'.join([f"{pkg[0]} | {pkg[1]} votes\n"+make_graph(pkg, listdata) for pkg in listdata])
        embed = message.embeds[0]
        embed.description = text
        await message.edit(embed=embed)
        
    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label="👍", style=discord.ButtonStyle.green, custom_id='poll:confirm:yes')
    async def _confirm(self, button, interaction):
        await self.handler(button, interaction)

    @discord.ui.button(label="👎", style=discord.ButtonStyle.red, custom_id='poll:confirm:no')
    async def confirm(self, button: discord.ui.Button, interaction : discord.Interaction):
        await self.handler(button, interaction)

    # This one is similar to the confirmation button except sets the inner value to `False`
    
    

class QuickPollFlags(commands.FlagConverter):
    choices:int = 1

class PollFlags(commands.FlagConverter, delimiter=' ', prefix='--'):
    hello: str

def quickpoll(_bot, options):
    class QuickPoll(discord.ui.View):
        def __init__(self,bot):
            self.bot = bot
            super().__init__(timeout=None)

        @discord.ui.select(options=[discord.SelectOption(label=i) for i in options], custom_id='quickpoll:selector:options')
        async def selector(self, select : discord.ui.Select, interaction : discord.Interaction):
            
            v = select.values[0] # only one selected 
            await interaction.response.defer()
            message= await interaction.original_message()
            key =f"quickpoll:results:{interaction.channel_id}:{message.id}"
            await self.bot.redis.hset(key, str(interaction.user.id), v)
            await self.bot.redis.expire(key, 86400)
            data = await self.bot.redis.hgetall(key)
            listdata = [(i, len([1 for k in data.values() if k == i])) for i in set(await self.bot.redis.hvals(key))]

            text = '\n'.join([f"{pkg[0]} | {pkg[1]} votes\n"+make_graph(pkg, listdata) for pkg in listdata])
            embed = message.embeds[0]
            embed.description = text
            await message.edit(embed=embed)

    return QuickPoll(_bot)

class Polls(commands.Cog):
    """Quick voting commands"""

    def __init__(self, bot) -> None:
        self.bot = bot

        self.yes = "✅"
        self.no = "❌"

        self.poll_setup = False 
    
    @commands.Cog.listener() 
    async def on_ready(self):
        if not self.poll_setup:
            self.bot.add_view(Confirm(self.bot))
            self.bot.add_view(quickpoll(self.bot, ['a','b','c']))


    @squidcommand("poll")
    @commands.bot_has_guild_permissions(send_messages=True)
    async def poll(self, ctx: commands.Context, question: str, *, flags : PollFlags = None) -> dict:
        """
        Quickly create a poll
        """
        print(flags)
        # description is a required field
        embed = discord.Embed(description='\u200b', color=self.bot.color).set_author(
            name=question, icon_url=ctx.author.avatar.url
        )

        view = Confirm(ctx.bot)
        await ctx.reply(embed=embed, view=view)

    @squidcommand("quickpoll")
    @commands.bot_has_guild_permissions(send_messages=True)
    async def quickpoll(self, ctx: commands.Context, *, question_and_choices: str):
        
        for i in ['|',',']:
            if i in question_and_choices:
                choices = question_and_choices.split(i)
                break 
        else:
            
            choices = shlex.split(question_and_choices)
        
        if len(choices) <= 2:
            raise commands.CommandError("You must have at least `1` question and `2` choices")
        question, *choices = choices
        for pos, choice in enumerate(choices[:]):
            choices[pos] = choice + '\u200b' * pos
        embed = discord.Embed(description='\u200b', color=self.bot.color).set_author(name=question, icon_url=ctx.author.avatar.url)
        view = quickpoll(self.bot, options=choices)
        await ctx.reply(embed=embed, view=view)
