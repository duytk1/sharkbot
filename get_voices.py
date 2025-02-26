import edge_tts
import asyncio


async def list_voices():
    voices = await edge_tts.list_voices()
    for voice in voices:
        # print(f"Name: {voice.get('ShortName', 'N/A')}")
        # print(f"  Gender: {voice.get('Gender', 'N/A')}")
        # print(f"  Locale: {voice.get('Locale', 'N/A')}")
        print({'country': voice.get('Locale', 'N/A'),
               'gender': voice.get('Gender', 'N/A'),
               'code': voice.get('ShortName', 'N/A')})

asyncio.run(list_voices())
