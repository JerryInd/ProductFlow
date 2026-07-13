from app.utils.logger import logger

class PublishEngine:
    async def publish(self, destination_group_id: str, caption: str, media_paths: list[str], video_paths: list[str]) -> bool:
        # TODO: delegate to WhatsApp service to send message
        logger.info(f"Would publish to {destination_group_id}: {len(media_paths)} media, {len(video_paths)} videos")
        return True

    async def publish_album(self, destination_group_id: str, caption: str, media_paths: list[str]) -> bool:
        return await self.publish(destination_group_id, caption, media_paths, [])

publish_engine = PublishEngine()
