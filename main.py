from typing import List
from databases import Database
import fastapi
from device.device import Device
import asyncio
from fastapi.middleware.cors import CORSMiddleware
from device.device_router import DeviceRouter
from device.db_connection import database
from device.models import DeviceModel
import zk


app = fastapi.FastAPI()
app.state.database = database

origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

devices: List[Device]= []

dr = DeviceRouter(devices)


@app.on_event("startup")
async def startup() -> None:
    global dr
    database_:Database = app.state.database
    if not database_.is_connected:
        await database_.connect()
    for device in await DeviceModel.objects.all():
        d = Device(**device.dict())
        devices.append(d)
    dr = DeviceRouter(devices)
    
@app.on_event("shutdown")
async def shutdown() -> None:
    database_:Database = app.state.database
    if database_.is_connected:
        await database_.disconnect()

@app.exception_handler(zk.base.ZKErrorConnection)
async def unicorn_exception_handler(request: fastapi.Request, exc: zk.base.ZKErrorConnection):
    return fastapi.responses.JSONResponse(
        status_code=418,
        content={"detail": f"Oops! We failed to communicate with the device."},
    )

@app.middleware("http")
async def timeout_middleware(request: fastapi.Request, call_next):
    REQUEST_TIMEOUT_ERROR = 60
    try:
        return await asyncio.wait_for(call_next(request), timeout=REQUEST_TIMEOUT_ERROR)

    except asyncio.TimeoutError:
        return fastapi.responses.JSONResponse({
            'detail': 'Request processing time excedeed limit'
            },
        status_code=fastapi.status.HTTP_504_GATEWAY_TIMEOUT)

app.include_router(dr.getRouter())
