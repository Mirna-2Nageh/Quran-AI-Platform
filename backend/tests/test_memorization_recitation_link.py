from unittest.mock import AsyncMock

import pytest
from app.services.memorization import MemorizationService


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("recitation", "expected"),
    [
        (None, "not_found"),
        (
            {
                "surah_number": 1,
                "ayah_number": 2,
                "end_ayah_number": 4,
            },
            "valid",
        ),
        (
            {
                "surah_number": 2,
                "ayah_number": 2,
                "end_ayah_number": 4,
            },
            "out_of_range",
        ),
        (
            {
                "surah_number": 1,
                "ayah_number": 1,
                "end_ayah_number": 4,
            },
            "out_of_range",
        ),
        (
            {
                "surah_number": 1,
                "ayah_number": 2,
                "end_ayah_number": 6,
            },
            "out_of_range",
        ),
    ],
)
async def test_validate_recitation_link(recitation, expected):
    repository = AsyncMock()
    repository.get_by_id_for_user.return_value = recitation

    service = MemorizationService(AsyncMock())

    result = await service.validate_recitation_link(
        user_id="user-1",
        plan={
            "surah_number": 1,
            "start_ayah": 2,
            "end_ayah": 5,
        },
        recitation_session_id="507f1f77bcf86cd799439011",
        recitation_repository=repository,
    )

    assert result == expected
    repository.get_by_id_for_user.assert_awaited_once_with(
        user_id="user-1",
        session_id="507f1f77bcf86cd799439011",
    )
