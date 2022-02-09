import unittest

from sqlalchemy import true

from zk.base import ZK
from zk.exception import ZKErrorConnection


class TestConnection(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        pass

    async def asyncSetUp(self):
        self.zk = ZK("192.168.50.166")    
        self.zk = await self.zk.connect()
        
    async def test_zk_connected(self):
        self.assertTrue(self.zk.is_connect, "Should be true")

    async def test_zk_get_info(self):
        name = await self.zk.get_device_name()
        self.assertIn(name,['F22/ID'],"should be string")

    async def test_zk_disconnection(self):
        await self.zk.disconnect()
        self.assertFalse(self.zk.is_connect, "Should be disconnected")

    async def test_raise_on_disconnection(self):
        await self.zk.disconnect()
        with self.assertRaises(ZKErrorConnection, msg="should raise ZKErrorConnection"):
            await self.zk.get_users()

    async def test_network_unplugged(self):
        await self.test_zk_connected()
        import subprocess
        # subprocess.call(['sudo', 'ip', 'link', 'set', 'eth0', 'down'])
        # os.system("ip link set eth0 down")
        with self.assertRaises(ZKErrorConnection, msg="should raise ZKErrorConnection"):
            await self.zk.get_users()
        # subprocess.call(['sudo', 'ip', 'link', 'set', 'eth0', 'up'])
        # os.system("ip link set eth0 up")


    def tearDown(self):
        pass

    async def asyncTearDown(self):
        if self.zk.is_connect:
            await self.zk.disconnect()
        
    async def on_cleanup(self):
        pass

if __name__ == "__main__":
    unittest.main()
    