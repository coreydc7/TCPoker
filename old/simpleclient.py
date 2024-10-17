import asyncio
import json

async def send_command(writer, command):
    message = json.dumps({"action": command}).encode('utf-8')
    writer.write(message)
    await writer.drain()

async def handle_server(reader, writer):
    while True:
        data = await reader.read(4096)
        if not data:
            print("Server closed the connection.")
            break
        message = json.loads(data.decode('utf-8'))
        print(f"Received: {message}")

async def main(ip, port):
    reader, writer = await asyncio.open_connection(ip, port)
    asyncio.create_task(handle_server(reader, writer))
    
    valid_commands = ['join', 'status', 'ready', 'exit']
    while True:
        command = input(f"Enter command {valid_commands}: ").strip()
        if command in valid_commands:
            await send_command(writer, command)
            if command == 'exit':
                break
        else:
            print(f"Invalid command. Try {valid_commands}.")

    writer.close()
    await writer.wait_closed()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="TCPoker Client")
    parser.add_argument('-i', '--ip', type=str, required=True, help='Server IP')
    parser.add_argument('-p', '--port', type=int, required=True, help='Server Port')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    args = parser.parse_args()
    
    asyncio.run(main(args.ip, args.port))