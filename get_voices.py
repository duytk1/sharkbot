import edge_tts
import asyncio


async def list_voices():
    voices = await edge_tts.list_voices()
    for voice in voices:
        print({'country': voice.get('FriendlyName', 'N/A'),
               'gender': voice.get('Gender', 'N/A'),
               'code': voice.get('ShortName', 'N/A')})

asyncio.run(list_voices())
