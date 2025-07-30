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
                UserId int PRIMARY KEY,
                Name VARCHAR(255)
            );
        """)

    def get_nick(self, user_id: int) -> str:
        self.cursor.execute(f"""
            SELECT Name
            FROM {self.table_name}
            WHERE UserId = ?;
        """, [user_id])
        
        result = self.cursor.fetchone()
        return "<unknown>" if result is None else result[0]

    def get_user_from_nick(self, nick: str) -> int | None:
        self.cursor.execute(f"""
            SELECT UserId
            FROM {self.table_name}
            WHERE Name = ?;
        """, [nick])
        
        result = self.cursor.fetchone()
        return None if result is None else result[0]


    def set_nick(self, user_id: int, name: str):
        self.cursor.execute(f"""
            INSERT INTO {self.table_name}
            VALUES(?, ?)
            ON CONFLICT(UserId)
            DO UPDATE
            SET Name = ?
        """,  [user_id, name, name])

class TexitCompatDb:
    def __init__(self, cursor, table_name):
        self.cursor = cursor
        self.table_name = table_name

        self.cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {self.table_name} (
                UserId INT PRIMARY KEY,
                TexitDisabled INT
            );
        """)

    def get(self, user_id: int) -> bool | None:
        self.cursor.execute(f"""
            SELECT TexitDisabled
            FROM {self.table_name}
            WHERE UserId = ?;
        """, [user_id])
        
        result = self.cursor.fetchone()
        return None if result is None else result[0] != 0

    def set(self, user_id: int, texit_disabled: bool):
        self.cursor.execute(f"""
            INSERT INTO {self.table_name}
            VALUES(?, ?)
            ON CONFLICT(UserId)
            DO UPDATE
            SET TexitDisabled = ?
        """,  [user_id, texit_disabled, texit_disabled])
