import asyncio
import typing
from uuid import UUID
import datetime
from aiosqlite import connect
import zk
from zk.base import ZK_helper

class Device:

    connection_status: typing.List[asyncio.Queue] = []

    def __init__(self, id: int, name:str, ip:str, description:str, port=4370, *args, **kwargs, ) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.ip = ip
        self.port = port
        self._connection = zk.ZK(self.ip, port=self.port, timeout=5, password=0, ommit_ping=False, verbose= True)
        self._live_capture_lock = asyncio.Lock()
        self._device_lock = asyncio.Lock()
        self.live_events: typing.List[asyncio.Queue] = []
        self.live_capture_task = None
        self.connection_task = None
        self.modified_time = datetime.datetime.now()#.isoformat()



    async def live_capture_loop(self):
        while True:
            async with self._live_capture_lock:
                print("Starting Live Capture")                  
                async for attendance in self._connection.live_capture():
                    punch =['check_in','check_out',None,None,'overtime_in','overtime_out']
                    print(attendance.punch)
                    data = {
                            "punch": punch[attendance.punch],
                            "status": attendance.status,
                            "timestamp":attendance.timestamp.isoformat(),
                            "uid":attendance.uid,
                            "user_id": attendance.user_id,
                        }
                    print(data)
                    await self._connection.test_voice(0)
                    for q in self.live_events:
                        await q.put(data)

            print("Should release lock")
            # lock.release()
            # print("Released Locking for Live capture")
            print("Live capture ended")   

    def live_capture_start_task(self):
        if self.live_capture_task == None or self.live_capture_task.cancelled():
            self.live_capture_task = asyncio.create_task(self.live_capture_loop())
        return self.live_capture_task

    def live_capture_cancel_task(self):
        if self.live_capture_task != None and not self.live_capture_task.cancelled():
            self.live_capture_task.cancel()

    def connected_task(self, live_capture=False):
        if self.connection_task==None or self.connection_task.cancelled():
            self.connection_task = asyncio.create_task(self.keep_connecting(live_capture))
    
    def cancel_connected_task(self):
        self.live_capture_cancel_task()
        if self.connection_task!=None and not self.connection_task.cancelled():
            self.connection_task.cancel()

    def keep_trying_connection_task(self, live_capture=False):
        self.connection_task = asyncio.create_task(self.ping_keep_connecting(live_capture))

    async def ping_keep_connecting(self, live_capture = False):
        h = ZK_helper(self.ip, self.port)
        flag = -1
        while True:
            connected = await h.test_ping()
            print("Pinging device")
            if connected:
                if not self._connection.is_connect:
                    await self.connect(live_capture)
            else:
                print("Ping Failed")
                print("Is connect:", self._connection.is_connect)
                if self._connection.is_connect:
                    print("Trying to close live capture on lost connection")
                    await self._connection.close_live_capture()
                    self.live_capture_cancel_task()
                    await self._connection.disconnect()

            for q in Device.connection_status:
                print("Putting in q")
                if flag != self._connection.is_connect:
                    flag = self._connection.is_connect
                    self.modified_time = datetime.datetime.now()#.isoformat()
                    await q.put({"id":self.id, "connected":flag, 'timestamp':self.modified_time})
            await asyncio.sleep(5)

    async def keep_connecting(self, live_capture = False):
        while True:
            try:
                await self.connect(live_capture)
                break
            except zk.base.ZKNetworkError:
                await asyncio.sleep(5)

    async def connect(self, live_capture=False):
        # try:
        await self._connection.connect()
        await self._connection.enable_device()
        if live_capture:
            self.live_capture_start_task()
        # except zk.base.ZKNetworkError as e:
        #     print(e)
        #     print("Trying to connect again in 5 sec")
        #     raise
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