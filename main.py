import os
import sys
import asyncio
import time
import fastapi
from fastapi import Request
from fastapi.responses import JSONResponse, Response
import uvicorn
from zk.exception import ZKErrorResponse, ZKNetworkError
from zk.finger import Finger
from zk.user import User
app = fastapi.FastAPI()

CWD = os.path.dirname(os.path.realpath(__file__))
ROOT_DIR = os.path.dirname(CWD)
sys.path.append(ROOT_DIR)

from zk import ZK
ip ='192.168.50.166'
ip2 = '192.168.31.253'
conn = ZK(ip, port=4370, timeout=5, password=0, ommit_ping=False, verbose= True)


live_capture_lock = asyncio.Lock()
loop = None
device_lock = asyncio.Lock()

# create ZK instance

punch = ["Check in", "Check out","","", "Overtime in", "Overtime out"]


async def live_capture():
    while True:
        async with live_capture_lock:
            print("Starting Live Capture")                  
            async for attendance in conn.live_capture():
                print(F"User: {attendance.user_id}\nPunch: {punch[attendance.punch]}\nTime: {attendance.timestamp}\nStatus: {attendance.status}\n",)
        print("Should release lock")
        # lock.release()
        # print("Released Locking for Live capture")
        print("Live capture ended")    

@app.get("/", summary="Test Health")
async def index():
    async with device_lock:
        print("Device Unlocked")
        print("Might be stuck from view")
        await conn.close_live_capture()
        print("Not stuck from view")
        print("Closed Live capture from view")
        async with live_capture_lock:
            await conn.test_voice(24)
    
    return Response("Running OK")

@app.delete("/users", summary="Delete All Users")
async def users_delete():
    '''Delete All Users'''
    
    async with device_lock:
        print("Device Unlocked")
        await conn.close_live_capture()
        print("Closed Live capture")
        async with live_capture_lock:
            print("Aquired Live capture lock")
            await conn.disable_device()
            for u in await conn.get_users():
                u: User = u
                await conn.delete_user(u.uid, u.user_id)
            await conn.enable_device()
            return Response("Clear " + "OK")

@app.get("/users")
async def get_all_users():
    
    async with device_lock:
        await conn.close_live_capture()
        async with live_capture_lock:
            users = []
            # try:
            await conn.disable_device()
            import json
            for user in await conn.get_users():
                user:User = user
                users.append(user.to_dict())
            await conn.enable_device()
            # print(users)
            return JSONResponse(users)
            # except:
                # return JSONResponse({"error": "Maybe device is not connected"})
            # finally:
                

@app.delete("/users/{id}")
async def delete_user(id:int):
    
    async with device_lock:
        await conn.close_live_capture()
        async with live_capture_lock:
            try:
                await conn.disable_device()
                await conn.delete_user(user_id=id)
                return JSONResponse({"user_id": id})
            except:
                return JSONResponse({"error": f"Could not delete user #{id}"})
            finally:
                await conn.enable_device()

@app.post("/unlock_door")
async def unlock_door():
    
    async with device_lock:
        await conn.close_live_capture()
        async with live_capture_lock:
            try:
                await conn.unlock()
                return {"status": "door unlocked"}
            except ZKErrorResponse:
                return JSONResponse({"error": "Unable to open the door"}, status_code=417)


@app.post("/users/{id}/enroll",summary="New User with ID - Fingerprint Enroll")
async def enroll(id:int):
    
    async with device_lock:
        await conn.close_live_capture()
        async with live_capture_lock:
            print("Locked for enrollment")
            try:
                try:
                    print(id)
                    enrolled = await asyncio.wait_for(conn.enroll_user(user_id=id), 60)
                    payload = {"user_id": id, "Enrolled": enrolled}
                    print(payload)
                    return payload
                except (TimeoutError, asyncio.TimeoutError):
                    await conn.cancel_capture()
                    return Response("Timed out")
                except ZKErrorResponse:
                    return JSONResponse({"error": f"Cant enroll user #{id}"}, status_code=409)
            finally:
                print("Event set")

@app.exception_handler(ZKNetworkError)
async def unicorn_exception_handler(request: Request, exc: ZKNetworkError):
    return JSONResponse(
        status_code=418,
        content={"message": f"Oops! {exc.name}"},
    )

@app.on_event("shutdown")
async def clean_up():
    if conn is not None and conn.is_connect is False:
        await conn.disconnect()

async def try_zk_connection():
        try:
            await conn.connect()
        except ZKNetworkError as e:
            print(e)
            print("Trying to connect again in 5 sec")
            raise ZKNetworkError(e)

async def retry_zk_connection():
    last = time.perf_counter()

    while not conn.is_connect:
        if time.perf_counter()-last > 5:
            try:
                await try_zk_connection()
            except ZKNetworkError:
                last = time.perf_counter()
        await asyncio.sleep(0)

@app.middleware("http")
async def device_lock_middleware(request: Request, call_next):
    if device_lock.locked():
        return JSONResponse({"error": "Device is busy"}, status_code=423)
    response = await call_next(request)
    return response

@app.on_event("startup")
async def bg_task():
    await try_zk_connection() # if connection fails first time. Shutdown.

    loop = asyncio.get_event_loop()
    await conn.enable_device()
    loop.create_task(live_capture())

if __name__ == "__main__":
    # asyncio.run(main())
    uvicorn.run("main:app",
                host = '0.0.0.0',
                port = 8000,
                lifespan = 'on',
                workers = 1,
                log_level = "warning",
                interface = 'asgi3',
                timeout_keep_alive = 5)