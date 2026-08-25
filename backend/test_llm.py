import asyncio
from llm import ask_yandex_gpt

async def main():
    system = "Ты помощник по базам данных. Отвечай кратко."
    user = "Сгенерируй SQL для подсчета количества студентов."
    
    result = await ask_yandex_gpt(system_prompt=system, user_prompt=user)
    print("Ответ YandexGPT:\n", result)

if __name__ == "__main__":
    asyncio.run(main())