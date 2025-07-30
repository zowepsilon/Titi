from __future__ import annotations

import discord
from discord.ext import commands

import io
import typst
import asyncio
import concurrent.futures

from utils import debuggable, TexitOptionDb

layout = """
#set page(
  height: auto,
  margin: 5pt,
  fill: none,
)

#set align(left)

#set page(width: 250pt)

#set text(
  fill: white,
)

{}
"""

def compile_to_png(source: str) -> io.BytesIO:
    return io.BytesIO(typst.compile(bytes(source, encoding="utf-8"), format="png", ppi=400.0))


class Typst(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.repeat = True

        self.db = TexitCompatDb(self.bot.cursor, "TexitCompat")

        self.renders: dict[int, (int, discord.Message)] = {}

    async def process(self, ctx, message_id: int, user_id: int, content: str):
        disable_texit = self.db.get(user_id)
        if disable_texit is None:
            text = "-# Tip : utilise `?math typst` ou `?math latex` pour choisir un mode de rendu à la place d'avoir les deux."
        elif disable_texit:
            text = ""
        else:
            return

        if message_id in self.renders.keys():
            await self.renders[message_id][1].delete()
            del self.renders[message_id]
        
        if content.startswith("?typst "):
            content = content[7:]
        elif content.startswith("$$ "):
            content = content[3:]
        elif content.startswith("$$"):
            content = content[2:]
            

        source = layout.format(content)
        
        try:
            loop = asyncio.get_running_loop()
            with concurrent.futures.ProcessPoolExecutor() as pool:
                rendered = await loop.run_in_executor(pool, compile_to_png, source)
            
        except RuntimeError as e:
            reason = e.args[0].replace("`", "​`")
            self.renders[message_id] = await ctx.send(f"Error while parsing typst:\n```{reason}```")
            return

        file = discord.File(rendered, "rendered.png")
        self.renders[message_id] = (user_id, await ctx.send(text, file=file))
        rendered.close()

    @commands.command()
    @debuggable
    async def typst(self, ctx, *, content: str = None):
        if content is None:
            if ctx.message.reference is None:
                return await ctx.send("Il faut répondre à un message contenant du code ou donner le code en argument !")

            content = (await ctx.fetch_message(ctx.message.reference.message_id)).content
            await self.process(ctx, ctx.message.reference.message_id, ctx.author.id, content)
        else:
            await self.process(ctx, ctx.message.id, ctx.author.id, content)

    async def on_message_bot(self, message):
        if message.author.id != self.config["texit_id"]:
            return

        if len(message.content) < 5:
            return

        if '*' == message.content[0] == message.content[1] == message.content[-1] == message.content[-2]:
            user_id = self.bot.nickname_cache.get_user_from_nick(message.content[2:-2])
            if self.db.get(user_id):
                await message.delete()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return await self.on_message_bot(message)

        if len(message.content) == 0 or message.content[0] == '?' or message.content.startswith(",tex"):
            return
        
        if message.content.count('$') >= 2 and message.content.count('```') == 0:
            await self.process(message.channel, message.id, message.author.id, message.content)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

        if message.author.bot or len(message.content) == 0 or message.content[0] == '?':
            return

        if message.content.count('$') >= 2 and message.content.count('```'):
            await self.process(message.channel, message.id, message.author.id, message.content)
        
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.emoji.name != '❌':
            return

        for (author_id, rendered) in self.renders.values():
            if rendered.id == payload.message_id:

                if author_id == payload.user_id:
                    message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)
                    await message.delete()

                break
            

def setup(bot):
    bot.add_cog(Typst(bot))
