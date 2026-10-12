"""Retries limitados apenas de GET; nunca repetir escritas ou erros de validação."""
import asyncio
import httpx


async def get_com_retry(client, url, **kwargs):
    for tentativa in range(3):
        try:
            resposta = await client.get(url, **kwargs)
            if resposta.status_code not in (429, 502, 503, 504) or tentativa == 2:
                return resposta
            await resposta.aclose()
        except (httpx.TimeoutException, httpx.NetworkError):
            if tentativa == 2:
                raise
        await asyncio.sleep(0.25 * (2 ** tentativa))
