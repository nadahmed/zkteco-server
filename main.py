from asyncio import tasks
from typing import Coroutine, List
import fastapi
from device import Device
import asyncio
from pydantic import BaseModel
from zk.exception import ZKErrorConnection, ZKNetworkError
from fastapi import status
from fastapi.middleware.cors import CORSMiddleware
from device_router import DeviceRouter


app = fastapi.FastAPI()

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

devices_conf = [
    {"id": 1,
        "name": "test1",
    "ip": "192.168.50.166",
    "description":"This is test device 1",
    "state": "ready",
    "connected": True},
    {"id": 2,
    "name": "test2",
    "ip": "192.168.50.227",
    "port":7332,
    "description":"This is test device 2",
    "state": "unknown",
    "connected": False},
    {"id": 3,
    "name": "test3",
    "ip": "192.168.52.166",
    "description":"This is test device 3",
    "state": "busy",
    "connected": True},
    # {"id": 4,
    # "name": "test4",
    # "ip": "192.168.53.166",
    # "description":"This is test device 4",
    # "state": "unknown",
    # "connected": False},
    ]

devices: List[Device]= []
for device in devices_conf:
    d = Device(**device)
    devices.append(d)
    # devApp = d.getApp()

    # app.mount("/devices/"+ str(d.id), devApp)
dr = DeviceRouter(devices)

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
