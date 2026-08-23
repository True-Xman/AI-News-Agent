import feedparser
import time
import logging
from ..models.raw_signal import RawSignal
from ..storage.operations import insert_raw_signal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def collect_rss(source_item):
    logger.info(f"Fetching {source_item.name} from {source_item.url}")
    feed = feedparser.parse(source_item.url)
    
    if feed.bozo:
        logger.warning(f"Feed parsing warning for {source_item.name}: {feed.bozo_exception}")
    
    if not feed.entries:
        logger.error(f"No entries found for {source_item.name} at {source_item.url}")
        return []

    signals = []
    for entry in feed.entries:
        try:
            signal = RawSignal(
                url=entry.link,
                title=entry.title,
                source=source_item.name,
                source_id=source_item.priority,
                found_at=time.mktime(entry.get("published_parsed", time.localtime())),
                snippet=entry.get("summary", "")
            )
            insert_raw_signal(signal)
            signals.append(signal)
        except Exception as e:
            logger.error(f"Failed to process entry in {source_item.name}: {e}")
            
    logger.info(f"Successfully collected {len(signals)} signals from {source_item.name}")
    return signals