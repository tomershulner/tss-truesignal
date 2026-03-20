from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import message_repo, user_repo
from app.services import session_cache
from app.services.classification_service import ClassificationService
from app.services.vibe_service import VibeService


class MessageService:
    def __init__(self):
        self._classification_svc = ClassificationService()

    async def ingest(
        self,
        db: AsyncSession,
        user_id: int,
        content: str,
    ) -> dict:
        # 1. Insert message
        message = await message_repo.insert_message(db, content)

        # 2. Classify
        result = await self._classification_svc.classify(content)

        # 3. Compute and store vibe score
        vibe_score = VibeService.compute_vibe_score(list(result.scores.values()))
        message.vibe_score = vibe_score
        await db.flush()

        # 4. Update user vibe score
        user = await user_repo.get_user_by_id(db, user_id)
        if user:
            await user_repo.update_user_vibe_score(db, user_id, vibe_score)
            session_cache.set_score(user_id, vibe_score)

        return {
            "message_id": message.message_id,
            "user_id": user_id,
            "vibe_score": vibe_score,
        }
