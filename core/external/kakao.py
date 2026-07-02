import httpx
from core.config import KAKAO_REST_API_KEY as KAKAO_API_KEY

_BASE = "https://dapi.kakao.com/v2/local"

async def search_keyword(query: str):
    url = f"{_BASE}/search/keyword.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": query}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    
async def refine_address(address_name: str):
    url = f"{_BASE}/search/address.json"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    params = {"query": address_name}

    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()