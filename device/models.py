from typing import Optional
from .db_connection import database, metadata
import ormar
from uuid import uuid4

def generate_uuid():
    return str(uuid4())

class DeviceModel(ormar.Model):

    class Meta:
        database = database
        metadata = metadata

    id: int = ormar.Integer(primary_key=True, autoincrement=True)
    name: str = ormar.Text()
    ip: str = ormar.Text(unique=True)
    port: Optional[int] = ormar.Integer(default=4370)
    description: str = ormar.Text()

# class StatusModel(ormar.Model):

    # class Meta:
    #     database = database
    #     metadata = metadata
    
    # id:int = ormar.Integer(primary_key=True)
    # device:DeviceModel = ormar.ForeignKey(unique=True)
    # connected:bool = ormar.Boolean(default=False)
    # busy:bool = ormar.Boolean(default=True)
