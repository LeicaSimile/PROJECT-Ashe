from contextlib import contextmanager
import psycopg2
from psycopg2 import pool, sql
from main import settings

db_pool = pool.SimpleConnectionPool(1, 10, dsn=settings.DATABASE_URL, sslmode="require")


class InactiveMember():
    def __init__(self, guild_id, member_id, last_notified=None, is_exempt=False, user=None):
        self.guild_id = guild_id
        self.member_id = member_id
        self.last_notified = last_notified
        self.is_exempt = is_exempt
        self.user = user


@contextmanager
def db():
    conn = db_pool.getconn()
    cur = conn.cursor()
    try:
        yield conn, cur
    finally:
        cur.close()
        db_pool.putconn(conn)

def setup():
    with db() as (conn, cur):
        query = """CREATE SCHEMA IF NOT EXISTS core;
        
        CREATE TABLE IF NOT EXISTS core.Default_Config (
            default_config_id SMALLSERIAL PRIMARY KEY,
            config_key VARCHAR(30) NOT NULL,
            config_value VARCHAR NULL
        );

        CREATE TABLE IF NOT EXISTS core.Guild_Config (
            guild_config_id SERIAL PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            config_key VARCHAR(30) NOT NULL,
            config_value VARCHAR NULL
        );

        CREATE TABLE IF NOT EXISTS core.Permission (
            permission_id SMALLINT PRIMARY KEY,
            permission_name VARCHAR(32)
        );

        CREATE TABLE IF NOT EXISTS core.Guild_Role_Permission (
            role_permission_id SERIAL PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            role_id INTEGER NOT NULL,
            permission_level SMALLINT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS core.Guild_Member_Permission (
            member_permission_id SERIAL PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            permission_level SMALLINT NOT NULL
        );
        
        CREATE TABLE IF NOT EXISTS core.Inactive_Member (
            inactive_member_id SERIAL PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL,
            last_notified TIMESTAMPTZ NULL
        );

        CREATE TABLE IF NOT EXISTS core.Exemption (
            exempt_member_id SERIAL PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            member_id INTEGER NOT NULL
        );
        """
        cur.execute(query)
        conn.commit()

def add_config_record(key, value):
    return

def get_config_value(key):
    return

def update_config_value(key, value):
    return

def delete_config_record(key):
    return

def get_all_inactive_members(guild_id):
    """Gets all inactive members within a guild.

    Args:
        guild_id(int): Guild ID according to Discord API.
    
    Returns:
        dict: Dictionary of inactive members within specified guild {member_id: InactiveMember}.

    """
    inactive_members = []
    results = []
    with db() as (conn, cur):
        query = sql.SQL("""SELECT guild_id, member_id, last_notified, is_exempt
            FROM core.Inactive_Member WHERE guild_id = {}""".format(guild_id))
        cur.execute(query)
        results = cur.fetchall()
    
    if results:
        inactive_members = {r[1]: InactiveMember(r[0], r[1], r[2], r[3]) for r in results}

    return inactive_members

def get_inactive_members(guild_id):
    return

def update_inactive_member(guild_id, member_id, **kwargs):
    return

def add_inactive_member(guild_id, member_id):
    """Adds an inactive member record to the database.

    Args:
        guild_id(int): Guild ID according to Discord API.
        member_id(int): Member ID according to Discord API.
    
    """
    with db() as (conn, cur):
        try:
            query = sql.SQL("""INSERT INTO core.Inactive_Member
                (guild_id, member_id) VALUES ({}, {})""".format(guild_id, member_id)
            )
            cur.execute(query)
            conn.commit()
            print(f"Added member ID {member_id} to Inactive_Member table.")
        except psycopg2.DatabaseError as e:
            print(e.diag.message_primary)
            conn.rollback()
            
    return

def remove_inactive_member(guild_id, member_id):
    with db() as (conn, cur):
        try:
            query = sql.SQL("""DELETE FROM core.Inactive_Member
                WHERE guild_id = {} AND member_id = {}""".format(guild_id, member_id)
            )
            cur.execute(query)
            conn.commit()
            print(f"Removed member ID {member_id} from Inactive_Member table.")
        except psycopg2.DatabaseError as e:
            print(e.diag.message_primary)
            conn.rollback()

    return

def get_exemptions(guild_id):
    """Gets members that are exempt and excused within a guild.
    
    Args:
        guild_id(int): Guild ID according to Discord API.
    
    Returns:
        list: Collection of exempt member IDs within specified guild.

    """
    exemptions = []
    with db() as (conn, cur):
        query = sql.SQL("""SELECT member_id
            FROM core.Exemption WHERE guild_id = {}""".format(guild_id)
        )
        cur.execute(query)
        exemptions = cur.fetchall()
    
    if exemptions:
        exemptions = [e[0] for e in exemptions]

    return exemptions

def add_exemption(guild_id, member_id):
    with db() as (conn, cur):
        try:
            query = sql.SQL("""INSERT INTO core.Exemption
                (guild_id, member_id) VALUES ({}, {})""".format(guild_id, member_id)
            )
            cur.execute(query)
            conn.commit()
        except psycopg2.DatabaseError as e:
            print(e.diag.message_primary)
            conn.rollback()
    
    return

def remove_exemption(guild_id, member_id):
    with db() as (conn, cur):
        try:
            query = sql.SQL("""DELETE FROM core.Exemption
                WHERE guild_id = {} AND member_id = {}""".format(guild_id, member_id)
            )
            cur.execute(query)
            conn.commit()
        except psycopg2.DatabaseError as e:
            print(e.diag.message_primary)
            conn.rollback()

    return
