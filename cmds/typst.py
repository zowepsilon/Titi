from __future__ import annotations

import discord
from discord.ext import commands

import io
import typst
import asyncio
import concurrent.futures
import re

from utils import debuggable, TexitCompatDb

layout = """
#set page(
  height: auto,
  width: auto,
  margin: (x: 5pt, y: 5pt),
  fill: rgb("#070709"),
)

#set text(
  fill: white,
)

#let fit(body) = context {{
  let (width,) = measure(body)
  let max_width = 350pt

  block(width: calc.min(width, max_width))[
    #body
  ]
}}

#show: fit
{}
"""

tag_regex = re.compile(r"<@([0-9]+)>")

def compile_to_png(source: str) -> io.BytesIO:
    return io.BytesIO(typst.compile(bytes(source, encoding="utf-8"), format="png", ppi=400.0))


class Typst(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.repeat = True

        self.db = TexitCompatDb(self.bot.cursor, "TexitCompat")

        self.renders: dict[int, (int, discord.Message)] = {}

    async def process(self, ctx, guild_id: int, message_id: int, user_id: int, content: str):
        disable_texit = self.db.get(guild_id, user_id)
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

        def process(m):
            user_id = int(m.group(1))
            print(f"{user_id = }")
            nick = self.bot.nickname_cache.get_nick(guild_id, int(m.group(1)))
            print(f"{nick = }")
            nick = nick.replace('`', r'\`')
            print(f"{nick = }")

            return f"`@{nick}`"
            
        content = re.sub(tag_regex, process, content)

        source = layout.format(content)
        
        try:
            loop = asyncio.get_running_loop()
            with concurrent.futures.ProcessPoolExecutor() as pool:
                rendered = await loop.run_in_executor(pool, compile_to_png, source)
            
        except RuntimeError as e:
            reason = e.args[0].replace("`", "​`")
            self.renders[message_id] = (user_id, await ctx.send(f"{text}\nErreur typst:\n```{reason}```"))
            return

        file = discord.File(rendered, "rendered.png")
        self.renders[message_id] = (user_id, await ctx.send(text, file=file))
        rendered.close()

    async def on_message_bot(self, message):
        if message.author.id != self.bot.config["texit_id"]:
            return

        if len(message.content) < 5:
            return
    
        name = message.content.split('\n')
        
        if '*' == name[0] == name[1] == name[-1] == name[-2]:
            user_id = self.bot.nickname_cache.get_user_from_nick(message.guild.id, message.content[2:-2])
            if self.db.get(message.guild.id, user_id):
                await message.delete()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return await self.on_message_bot(message)

        if len(message.content) == 0 or message.content[0] == '?' or message.content.startswith(",tex"):
            return
        
        if message.content.count('$') >= 2 and message.content.count('```') == 0:
            await self.process(message.channel, message.guild.id, message.id, message.author.id, message.content)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        message = await self.bot.get_channel(payload.channel_id).fetch_message(payload.message_id)

        if message.author.bot or len(message.content) == 0 or message.content[0] == '?':
            return

        if message.content.count('$') >= 2 and message.content.count('```') == 0:
            await self.process(message.channel, message.guild.id, message.id, message.author.id, message.content)
        
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

    @commands.command()
    @debuggable
    async def typst(self, ctx, *, content: str = None):
        if content is None:
            if ctx.message.reference is None:
                return await ctx.send("Il faut répondre à un message contenant du typst ou le donner en argument !")

            content = (await ctx.fetch_message(ctx.message.reference.message_id)).content
            await self.process(ctx, ctx.guild.id, ctx.message.reference.message_id, ctx.author.id, content)
        else:
            await self.process(ctx, ctx.guild.id, ctx.message.id, ctx.author.id, content)
            
    @commands.command()
    @debuggable
    async def math(self, ctx, mode: str = None):
        mode = None if mode is None else mode.lower()

        if mode == "typst":
            self.db.set(ctx.guild.id, ctx.author.id, True)
            await ctx.send("Tu utilises maintenant Typst sur ce serveur !")
        elif mode == "latex" or mode == "texit":
            self.db.set(ctx.guild.id, ctx.author.id, False)
            await ctx.send("Tu utilises maintenant LaTeX sur ce serveur !")
        else:
            await ctx.send("Modes : `typst` et `latex`")

def setup(bot):
    bot.add_cog(Typst(bot))
