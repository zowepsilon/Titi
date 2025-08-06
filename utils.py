from __future__ import annotations

import functools
import traceback
import random

def debuggable(f):
    @functools.wraps(f)
    async def new(self, ctx, *args, **kwargs):
        try:
            await f(self, ctx, *args, **kwargs)
        except Exception as exc:
            if self.bot.config["debug"] and self.bot.is_dev(ctx.author.id):
                await ctx.send(f"Exception lors de l'exécution: ```\n{traceback.format_exc()}```")
            else:
                raise exc

    return new


def sanitize(text: str) -> str:
    return text \
        .replace("@here", "@​here") \
        .replace("@everyone", "@​everyone") \
        .replace("<@&", "<​@​&​")


class NicknameCache:
    def __init__(self, cursor, table_name):
        self.cursor = cursor
        self.table_name = table_name

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                GuildId int,
                UserId int,
                Name VARCHAR(255),
                PRIMARY KEY (GuildId, UserId)
            );
        """)

    def get_nick(self, guild_id: int, user_id: int) -> str:
        self.cursor.execute(f"""
            SELECT Name
            FROM {self.table_name}
            WHERE GuildId = ?
            AND UserId = ?;
        """, [user_id, guild_id])
        
        result = self.cursor.fetchone()
        return "<unknown>" if result is None else result[0]

    def get_user_from_nick(self, nick: str, guild_id: int) -> int | None:
        self.cursor.execute(f"""
            SELECT UserId
            FROM {self.table_name}
            WHERE GuildId = ?
            AND Name = ?;
        """, [guild_id, nick])
        
        result = self.cursor.fetchone()
        return None if result is None else result[0]


    def set_nick(self, guild_id: int, user_id: int, nick: str):
        self.cursor.execute(f"""
            INSERT INTO {self.table_name}
            VALUES(?, ?, ?)
            ON CONFLICT
            DO UPDATE
            SET Name = ?;
        """,  [guild_id, user_id, nick, nick])

class TexitCompatDb:
    def __init__(self, cursor, table_name):
        self.cursor = cursor
        self.table_name = table_name

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                GuildId int,
                UserId int,
                TexitDisabled int,
                PRIMARY KEY (GuildId, UserId)
            );
        """)

    def get(self, guild_id: int, user_id: int) -> bool | None:
        self.cursor.execute(f"""
            SELECT TexitDisabled
            FROM {self.table_name}
            WHERE GuildId = ?
            AND UserId = ?;
        """, [guild_id, user_id])
        
        result = self.cursor.fetchone()
        return None if result is None else result[0] != 0

    def set(self, guild_id: int, user_id: int, texit_disabled: bool):
        self.cursor.execute(f"""
            INSERT INTO {self.table_name}
            VALUES(?, ?, ?)
            ON CONFLICT
            DO UPDATE
            SET TexitDisabled = ?;
        """,  [guild_id, user_id, texit_disabled, texit_disabled])

    def dbg(self):
        self.cursor.execute(f"""SELECT * FROM {self.table_name}""")
        print(self.cursor.fetchall())
