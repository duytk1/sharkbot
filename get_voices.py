import edge_tts
import asyncio

async def list_voices():
    voices = await edge_tts.list_voices()
    for voice in voices:
        print(voice)  # Print the entire voice dictionary to inspect available keys

asyncio.run(list_voices())
