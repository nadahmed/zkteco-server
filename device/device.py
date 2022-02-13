import asyncio
import typing
import datetime
import zk
from zk.base import ZK_helper
from zk.exception import ZKErrorConnection

class Device:

    connection_status: typing.List[asyncio.Queue] = []

    def __init__(self, id: int, name:str, ip:str, description:str, port=4370, *args, **kwargs, ) -> None:
        self.id = id
        self.name = name
        self.description = description
        self.ip = ip
        self.port = port
        self._connection = zk.ZK(self.ip, port=self.port, timeout=10, password=0, ommit_ping=True, verbose= True)
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
            print("Live capture ended")   

    def live_capture_start_task(self):
        self.live_capture_task = asyncio.create_task(self.live_capture_loop())
        return self.live_capture_task

    def live_capture_cancel_task(self):
        if self.live_capture_task != None:
            self.live_capture_task.cancel()

    def connected_task(self, live_capture=False):
        # if self.connection_task==None or self.connection_task.cancelled():
        loop = asyncio.get_running_loop()
        def cb(task:asyncio.Task):
            try:
                task.result()
            except ZKErrorConnection:
                self.connection_task = loop.create_task(self.keep_connecting(live_capture))
                self.connection_task.add_done_callback(cb)
            except asyncio.CancelledError:
                pass
        
        
        self.connection_task = loop.create_task(self.keep_connecting(live_capture))
        self.connection_task.add_done_callback(cb)
        # self.connection_task.
        print("Created connection task")
    
    def cancel_connected_task(self):
        self.live_capture_cancel_task()
        if self.connection_task != None:
            self.connection_task.cancel()

    async def keep_connecting(self, live_capture = False):
        flag = -1
        while True:
            print("Is connected", self._connection.is_connect)
            if not self._connection.is_connect:
                try:
                    if self._connection.enabled_live_capture:
                        await self._connection.close_live_capture()
                        self.live_capture_cancel_task()
                    loop = asyncio.get_running_loop()
                    print("Trying to connect")
                    
                    await asyncio.wait_for(loop.create_task(self._connection.connect()), timeout=10)
                    await self._connection.enable_device()
                    if live_capture:
                        self.live_capture_start_task()
                    print("Connected!!!")

                except asyncio.TimeoutError:
                    print(f"Timed out! Trying again in 5 seconds...")
                except OSError as e:
                    if e.errno == 113:
                        print(f"Could not connect. Trying again in 5 seconds...")
                    else:
                        raise
            for q in Device.connection_status:
                # if flag != self._connection.is_connect:
                flag = self._connection.is_connect
                self.modified_time = datetime.datetime.now()#.isoformat()
                await q.put({"id":self.id, "connected":flag, 'timestamp':self.modified_time})
            await asyncio.sleep(5)


        
    # async def connect(self, live_capture=False):
    #     await self._connection.connect()
    #     await self._connection.enable_device()
    #     if live_capture:
    #         await self.live_capture_start_task()

    async def clean_up(self):
        if self._connection is not None and self._connection.is_connect is False:
            await self._connection.disconnect()

    def __str__(self) -> str:
        return "Device: "+ self.name