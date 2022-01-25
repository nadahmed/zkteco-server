import asyncio
import typing
from uuid import UUID
import zk

class Device:
    def __init__(self, id: str, name:str, ip:str, description:str, port=4370, *args, **kwargs, ) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.ip = ip
        self.port = port
        self._connection = zk.ZK(self.ip, port=self.port, timeout=5, password=0, ommit_ping=False, verbose= True)
        self._live_capture_lock = asyncio.Lock()
        self._device_lock = asyncio.Lock()
        self.live_events: typing.List[asyncio.Queue] = []
        
    async def live_capture_loop(self):
        while True:
            async with self._live_capture_lock:
                print("Starting Live Capture")                  
                async for attendance in self._connection.live_capture():
                    print(F"User: {attendance.user_id}\nPunch: {attendance.punch}\nTime: {attendance.timestamp}\nStatus: {attendance.status}\n",)
                    for q in self.live_events:
                        data = {
                            "punch": attendance.punch,
                            "status": attendance.status,
                            "timestamp":attendance.timestamp.isoformat(),
                            "uid":attendance.uid,
                            "user_id": attendance.user_id,
                        }
                        await q.put(data)

            print("Should release lock")
            # lock.release()
            # print("Released Locking for Live capture")
            print("Live capture ended")   

    async def connect(self):
        try:
            await self._connection.connect()
            await self._connection.enable_device()
        except zk.base.ZKNetworkError as e:
            print(e)
            print("Trying to connect again in 5 sec")
            raise
        return self

    async def clean_up(self):
        if self._connection is not None and self._connection.is_connect is False:
            await self._connection.disconnect()
        
    # def _setupApp(self):
        # @self._app.middleware("http")
        # async def _device_lock_middleware(request: fastapi.Request, call_next):
        #     if self._device_lock.locked():
        #         return fastapi.responses.JSONResponse({"error": "Device is busy"}, status_code=423)
        #     response = await call_next(request)
        #     return response

    def __str__(self) -> str:
        return "Device: "+ self.name