from fastapi import APIRouter, Query, Depends
from core.external.kakao import search_keyword, refine_address
from models.user import User
from dependencies import get_current_user

router = APIRouter(prefix="/address", tags=["address"])

@router.get("/search")
async def combined_address_search(
    query: str, 
    current_user: User = Depends(get_current_user)
):
    # 로그인한 사용자만 주소 검색 가능
    # 1. keyword API로 광범위한 검색 (하위 주소까지 포함됨)
    keyword_result = await search_keyword(query)
    keyword_docs = keyword_result.get("documents", [])

    combined_results = []

    for item in keyword_docs:
        address_name = item.get("road_address", {}).get("address_name") or item.get("address_name")

        # 2. address API로 정확한 우편번호, 도로명 가져오기
        if address_name:
            refine_result = await refine_address(address_name)
            refine_doc = (refine_result.get("documents") or [{}])[0] if refine_result.get("documents") else {}

            road_address = refine_doc.get("road_address")
            if road_address:  # 도로명 주소가 있을 때만 추가
                combined_results.append({
                    "display_name": address_name,
                    "zone_no": road_address.get("zone_no"),
                    "road_address": road_address.get("address_name"),
                    "jibun_address": refine_doc.get("address", {}).get("address_name"),
                    "lat": item.get("y"),
                    "lng": item.get("x"),
                })

    # 중복 제거 및 가나다 정렬
    unique = {item["display_name"]: item for item in combined_results}
    sorted_list = sorted(unique.values(), key=lambda x: x["display_name"])

    return sorted_list