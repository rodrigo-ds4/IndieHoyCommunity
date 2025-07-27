"""
Debug test for sold out show issue
"""

import pytest
from app.services.discount_prefilter import DiscountPreFilter


@pytest.mark.asyncio
async def test_debug_sold_out_prefilter(test_db, complex_test_shows):
    """Debug específico para entender por qué el PreFilter no rechaza Abel Pintos"""
    
    # Crear PreFilter
    prefilter = DiscountPreFilter(test_db)
    
    # Datos del request
    request_data = {
        "user_email": "sebastian.valido@test.com",
        "show_description": "Abel Pintos Sold Out"
    }
    
    print("\n=== DEBUG SOLD OUT SHOW ===")
    
    # Paso 1: Verificar que el show existe en la DB
    from app.models.database import Show
    abel_shows = test_db.query(Show).filter(Show.title.like('%Abel%')).all()
    print(f"\n🔍 Shows con 'Abel' en DB: {len(abel_shows)}")
    for show in abel_shows:
        remaining = show.get_remaining_discounts(test_db)
        print(f"  - {show.title} | Max: {show.max_discounts} | Remaining: {remaining}")
    
    # Paso 2: Test directo del método _find_shows_with_discounts
    candidate_shows = prefilter._find_shows_with_discounts("Abel Pintos Sold Out")
    print(f"\n🔍 Candidate shows encontrados: {len(candidate_shows)}")
    for show in candidate_shows:
        print(f"  - {show['title']} | Remaining: {show['remaining_discounts']}")
    
    # Paso 3: Test completo del PreFilter
    result = prefilter.validate_request(request_data)
    print(f"\n🔍 Resultado PreFilter:")
    print(f"  - Approved: {result.approved}")
    print(f"  - Rejected: {result.rejected}")
    print(f"  - Reason: {result.reason}")
    
    # Verificar que fue rechazado
    assert result.rejected == True, f"El PreFilter debería rechazar, pero approved={result.approved}, reason={result.reason}" 