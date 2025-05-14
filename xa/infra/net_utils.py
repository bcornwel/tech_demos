"""
This file contains utilities to manage networks
Use asyncio to manage network connections
"""


import platform
import socket
import subprocess

from infra.sys_utils import get_system_id


def verify_connection(host: str) -> bool:
    """
    Verify a connection to a host
    """
    if host in [get_system_id(), '.']:
        return True
    else:
        return resolve_address(host)


def is_host_accessible(host, port=80, timeout=5):
    """
    Check if a host is accessible on the network.

    :param host: The hostname or IP address of the target computer.
    :param port: The port to attempt to connect to (default is 80).
    :param timeout: The timeout for the connection attempt in seconds (default is 5).
    :return: True if the host is accessible, False otherwise.
    """
    try:
        # Create a socket object
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (socket.timeout, socket.error):
        return False


def resolve_address(address: str) -> str:
    """
    Resolve an address to an IP address, verify the route
    """
    if is_host_accessible(address):
        print(f"{address} is accessible via xa-scale")
        return address
    else:
        print(f"{address} is not accessible via xa-scale")
        count = 1
        timeout = 100  # on the same network should be very fast to respond
        param = '-n' if platform.system().lower() == 'windows' else '-c'
        # Construct the ping command
        command = ['ping', param, str(count), '-w', str(timeout), address]
        
        try:
            # Execute the ping command
            print("Running command:", command)
            output = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Check the return code
            return address if output.returncode == 0 else None
        except Exception as e:
            print(f"Unable to connect to {address} because: {e}")
            return None


def listen_mode():
    """
    Listen for incoming connections
    """
    import asyncio
    from aiohttp import web

    async def handle_default(request):
        print("Received request")
        return web.json_response({'message': 'XA-Scale is in listen mode'})

    # Define a function to echo back a message sent in the request
    async def handle_command(request):
        data = await request.json()
        print("Received command:", data.get("command", "No command received"))
        message = data.get('command', 'No command received')
        return web.json_response({'message': message})

    async def main():
        app = web.Application()

        app.router.add_get('/', handle_default)
        app.router.add_post('/command', handle_command)

        runner = web.AppRunner(app)
        await runner.setup()

        site = web.TCPSite(runner, 'localhost', 8865)
        await site.start()

        print("======= Serving on http://localhost:8865/ =======")

        try:
            while True:
                await asyncio.sleep(300)  # Sleep for an hour
        except KeyboardInterrupt:
            pass
        finally:
            await runner.cleanup()
    
    asyncio.run(main())


def control_mode(node, command, args):
    """
    Control the network
    """
    import asyncio
    import aiohttp

    # Define an asynchronous function to get a greeting message from the server
    async def contact_node(node):
        async with aiohttp.ClientSession() as session:
            try:
                async with session.get(f'http://{node}:8865/') as response:
                    if response.status == 200:
                        data = await response.json()
                        print(f"Contacted {node}:", data['message'])
                        return True
                    else:
                        print(f"Failed to get response from {node}:", response.status)
                        return False
            except Exception as e:
                print(f"Failed to contact {node} because: {e}")
                return False

    # Define an asynchronous function to send a message to the server and get an echo
    async def send_cmd(node, cmd, args):
        async with aiohttp.ClientSession() as session:
            async with session.post(f'http://{node}:8865/command', json={"command": cmd, "args": args}) as response:
                if response.status == 200:
                    data = await response.json()
                    resp = data.get("message", "No response")
                    print("Command response:", resp)
                    return resp
                else:
                    print("Failed to send command:", response.status)
                    return None

    async def main():
        node = "localhost"
        node = resolve_address(node)
        assert node, "Failed to resolve address"
        assert (await contact_node(node)), "Failed to get response from server"
        result = await send_cmd(node, command, args)
        print("Result:", result)
        
    asyncio.run(main())


def deploy_xa(node:str):
    assert verify_connection(node)
    # ssh to the node and deploy xa-scale in listen mode


if __name__ == "__main__":
    print("Running command")
    control_mode("localhost", "run", "a schedule")