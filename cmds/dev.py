import discord
from discord.ext import commands
from utils import debuggable

class Developer(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        self.bot.nickname_cache.set_nick(after.id, after.display_name)

    @commands.command()
    @debuggable
    async def reload_names(self, ctx):
        if not self.bot.is_dev(ctx.author.id):
            return await ctx.send("You need to be a developer to do that!")
        async with ctx.message.channel.typing():
            for m in ctx.author.guild.members:
                self.bot.nickname_cache.set_nick(m.id, m.display_name)

            await ctx.send(f"Les noms de {len(ctx.author.guild.members)} membres ont été rechargés !")

    @commands.command()
    @debuggable
    async def debug(self, ctx):
        if not self.bot.is_dev(ctx.author.id):
            return await ctx.send("You need to be a developer to do that!")

        self.bot.config["debug"] = not self.bot.config["debug"]
        await ctx.send(f"Le mode debug a été " + ("activé !" if self.bot.config["debug"] else "désactivé !"))

def setup(bot): 
    bot.add_cog(Developer(bot))
