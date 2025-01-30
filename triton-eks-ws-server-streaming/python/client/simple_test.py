import websockets
import asyncio

async def test_connection():
    uri = "ws://ab2c89d3704f3499e9350563e87f167b-00015305edd17ba4.elb.us-east-1.amazonaws.com:8080"
    try:
        async with websockets.connect(uri) as ws:
            print("Connection successful!")
    except Exception as e:
        print(f"Connection failed: {str(e)}")

asyncio.run(test_connection())
