from databases import Database
import sqlalchemy

database = Database('sqlite+aiosqlite:///test.db')
metadata = sqlalchemy.MetaData()

async def initialize():
    print("Connecting to DB")
    await database.connect()