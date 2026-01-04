async def get_ai_response(user_id: int, text: str) -> str:
    """Используем бесплатные публичные API"""
    try:
        # Пробуем разные бесплатные эндпоинты
        # 1. ChatGPT Free API
        response = requests.post(
            "https://chatgpt-api.shn.hk/v1/",
            json={
                "model": "gpt-3.5-turbo",
                "messages": [{"role": "user", "content": text}],
                "temperature": 0.7
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except:
        pass
    
    try:
        # 2. DeepSeek через публичный прокси (может работать)
        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": "deepseek-chat",
                "messages": [{"role": "user", "content": text}],
                "max_tokens": 500,
                "temperature": 0.7
            },
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
    except:
        pass
    
    return "🤖 ИИ временно недоступен. Попробуй позже!"
