from ipaddress import ip_address
from sqlite3 import IntegrityError
import typing
import fastapi
import pydantic
from device.device import Device
import asyncio

from device.models import DeviceModel

import zk
from zk.base import ZK_helper

class DeviceRouter:
    def __init__(self, devices: typing.List[Device]):
        self._devices = devices
        self._router = fastapi.APIRouter(
            prefix="/devices",
            tags=["ZKTeco"]
        )
        self._sub_router = fastapi.APIRouter(
            prefix="/{deviceId}"
        )

        self._setupRouter()
        self._setupSubRouter()
        self._router.include_router(self._sub_router)

    def _device_check(self, deviceId: str = fastapi.Path(...)):
        try:
            device = [el for el in self._devices if el.id == deviceId][0]
        except IndexError:
            raise fastapi.HTTPException(404, detail="device not found")

        if device._device_lock.locked():
            raise fastapi.HTTPException(detail={"error": "Device is busy"}, status_code=423)
        return device
        # pass

    def getRouter(self):
        return self._router

    def _setupRouter(self):
        @self._router.get("", response_model=typing.List[DeviceModel])
        async def get_all_devices():
            return await DeviceModel.objects.all()
        

        class DeviceCreateModel(pydantic.BaseModel):
            name: str
            ip: str
            port : typing.Optional[int] = 4370
            description: str
        
        @self._router.post("", response_model=DeviceModel ,status_code=fastapi.status.HTTP_201_CREATED)
        async def add_device(device: DeviceCreateModel):
            """
            TODO: Connect device on add
            """
            try:
                device.ip = str(ip_address(device.ip))
                d = await DeviceModel.objects.create(**device.dict())
                self._devices.append(Device(**d.dict()))
                return d
            except IntegrityError as e:
                raise fastapi.exceptions.HTTPException(fastapi.status.HTTP_400_BAD_REQUEST, str(e))
            except ValueError as e:
                raise fastapi.exceptions.HTTPException(fastapi.status.HTTP_400_BAD_REQUEST, str(e))

        class PingAddress(pydantic.BaseModel):
            ip: str
            port: typing.Optional[int] = 4370
        
        @self._router.post("/ping", status_code=fastapi.status.HTTP_201_CREATED, summary="Ping any device")
        async def ping_device(address:PingAddress):
            helper = ZK_helper(address.ip, address.port)
            if helper.test_ping():
                return fastapi.Response("Pinging device was successful")
            else:
                raise fastapi.HTTPException(detail="Failed to ping device", status_code=fastapi.status.HTTP_408_REQUEST_TIMEOUT)
            
    def _setupSubRouter(self):

        class DeviceUpdateModel(pydantic.BaseModel):
            name: typing.Optional[str]
            description: typing.Optional[str]

        @self._sub_router.put("", response_model=DeviceModel ,status_code=fastapi.status.HTTP_201_CREATED)
        async def update_device(deviceModel: DeviceUpdateModel, device: Device = fastapi.Depends(self._device_check)):
            try:
                d = await DeviceModel.objects.get_or_none(id=device.id)
                if d is not None:
                    d.name = deviceModel.name if deviceModel.name else d.name
                    d.description = deviceModel.description if deviceModel.description else d.description
                    return await d.update()
                raise fastapi.exceptions.HTTPException(fastapi.status.HTTP_400_BAD_REQUEST, "Device does not exist.")
            except IntegrityError as e:
                raise fastapi.exceptions.HTTPException(fastapi.status.HTTP_400_BAD_REQUEST, str(e))

        @self._sub_router.delete("")
        async def remove_device(device: Device = fastapi.Depends(self._device_check)):
            """
            TODO: Disconnect device and remove from array         
            """            

            await DeviceModel.objects.delete(id=device.id)
            self._devices.remove(device)
            return fastapi.responses.JSONResponse({"id": str(device.id)}, status_code=fastapi.status.HTTP_202_ACCEPTED)
        
        @self._sub_router.get("/stream")
        async def live_capture(device: Device = fastapi.Depends(self._device_check)):
            import json
            async def get_value():
                q = asyncio.Queue(1)                
                try:
                    device.live_events.append(q)
                    while True:
                        yield json.dumps(await q.get()) + "\n"
                finally:
                    device.live_events.remove(q)
            return fastapi.responses.StreamingResponse(get_value(), media_type='application/json')

        @self._sub_router.get("/voice/{voiceId}", summary="Voice")
        async def test_voice(voiceId:int, device: Device = fastapi.Depends(self._device_check)):        
            """
                play test voice:\n
                0 Thank You\n
                1 Incorrect Password\n
                2 Access Denied\n
                3 Invalid ID\n
                4 Please try again\n
                5 Dupicate ID\n
                6 The clock is flow\n
                7 The clock is full\n
                8 Duplicate finger\n
                9 Duplicated punch\n
                10 Beep kuko\n
                11 Beep siren\n
                12 -\n
                13 Beep bell\n
                14 -\n
                15 -\n
                16 -\n
                17 -\n
                18 Windows(R) opening sound\n
                19 -\n
                20 Fingerprint not emolt\n
                21 Password not emolt\n
                22 Badges not emolt\n
                23 Face not emolt\n
                24 Beep standard\n
                25 -\n
                26 -\n
                27 -\n
                28 -\n
                29 -\n
                30 Invalid user\n
                31 Invalid time period\n
                32 Invalid combination\n
                33 Illegal Access\n
                34 Disk space full\n
                35 Duplicate fingerprint\n
                36 Fingerprint not registered\n
                37 -\n
                38 -\n
                39 -\n
                40 -\n
                41 -\n
                42 -\n
                43 -\n
                43 -\n
                45 -\n
                46 -\n
                47 -\n
                48 -\n
                49 -\n
                50 -\n
                51 Focus eyes on the green box\n
                52 -\n
                53 -\n
                54 -\n
                55 -\n
            """

            async with device._device_lock:
                await device._connection.close_live_capture()
                async with device._live_capture_lock:
                    await device._connection.test_voice(voiceId)

        @self._sub_router.delete("/users", summary="Delete All Users")
        async def users_delete(device: Device = fastapi.Depends(self._device_check)):
            '''Delete All Users'''
            
            async with device._device_lock:
                print("Device Unlocked")
                await device._connection.close_live_capture()
                print("Closed Live capture")
                async with device._live_capture_lock:
                    print("Aquired Live capture lock")
                    await device._connection.disable_device()
                    for u in await device._connection.get_users():
                        u: zk.base.User = u
                        await device._connection.delete_user(u.uid, u.user_id)
                    await device._connection.enable_device()
                    return fastapi.Response("Clear " + "OK")

        @self._sub_router.get("/users")
        async def get_all_users(device: Device = fastapi.Depends(self._device_check)):
            
            async with device._device_lock:
                await device._connection.close_live_capture()
                async with device._live_capture_lock:
                    users = []
                    await device._connection.disable_device()
                    import json
                    for user in await device._connection.get_users():
                        user:zk.base.User = user
                        users.append(user.to_dict())
                    await device._connection.enable_device()
                    return fastapi.responses.JSONResponse(users)
                        

        @self._sub_router.delete("/users/{userId}")
        async def delete_user(userId:int, device: Device = fastapi.Depends(self._device_check)):
            
            async with device._device_lock:
                await device._connection.close_live_capture()
                async with device._live_capture_lock:
                    try:
                        await device._connection.disable_device()
                        await device._connection.delete_user(user_id=userId)
                        return fastapi.responses.JSONResponse({"user_id": userId})
                    except:
                        return fastapi.responses.JSONResponse({"error": f"Could not delete user #{userId}"})
                    finally:
                        await device._connection.enable_device()

        @self._sub_router.post("/unlock_door")
        async def unlock_door(device: Device = fastapi.Depends(self._device_check)):
            
            async with device._device_lock:
                await device._connection.close_live_capture()
                async with device._live_capture_lock:
                    try:
                        await device._connection.unlock()
                        return {"status": "door unlocked"}
                    except zk.base.ZKErrorResponse:
                        return fastapi.responses.JSONResponse({"error": "Unable to open the door"}, status_code=417)


        @self._sub_router.post("/users/{userid}/enroll",summary="New User with ID - Fingerprint Enroll")
        async def enroll(userid:int, device: Device = fastapi.Depends(self._device_check)):
            
            async with device._device_lock:
                await device._connection.close_live_capture()
                async with device._live_capture_lock:
                    print("Locked for enrollment")
                    try:
                        enrolled = await asyncio.wait_for(device._connection.enroll_user(user_id=userid), 60)
                        payload = {"user_id": userid, "Enrolled": enrolled}
                        return payload
                    except (TimeoutError, asyncio.TimeoutError):
                        await device._connection.cancel_capture()
                        return fastapi.Response("Timed out")
                    except zk.base.ZKErrorResponse:
                        return fastapi.responses.JSONResponse({"error": f"Cant enroll user #{userid}"}, status_code=409)
        
        @self._sub_router.on_event("startup")
        async def bg_task():
            loop = asyncio.get_event_loop()
            
            for device in self._devices:
                try:
                    await device.connect()
                    loop.create_task(device.live_capture_loop())
                except zk.base.ZKNetworkError:
                    pass


        @self._sub_router.on_event("shutdown")
        async def clean_up():
            for device in self._devices:
                try:
                    await device.clean_up()
                except zk.base.ZKErrorConnection:
                    pass