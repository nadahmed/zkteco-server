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

    id: str = ormar.String(default=generate_uuid, primary_key= True, max_length=38)
    name: str = ormar.Text()
    ip: str = ormar.Text(unique=True)
    port: Optional[int] = ormar.Integer(default=4370)
    description: str = ormar.Text()
