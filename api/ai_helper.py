

async def chamar_anthropic(prompt: str, max_tokens: int = 500) -> str:
    """Chamada centralizada para Anthropic API."""
    import anthropic
    from api.config import settings
    cliente = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    msg = cliente.messages.create(
        model="claude-haiku-4-5",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}]
    )
    return msg.content[0].text
