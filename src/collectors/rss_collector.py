import feedparser
import time
from ..models.raw_signal import RawSignal
from ..storage.operations import insert_raw_signal

def collect_rss(source_item):
    feed = feedparser.parse(source_item.url)
    signals = []
    for entry in feed.entries:
        signal = RawSignal(
            url=entry.link,
            title=entry.title,
            source=source_item.name,
            source_id=source_item.priority, # Using priority as id for now
            found_at=time.mktime(entry.get("published_parsed", time.localtime())),
            snippet=entry.get("summary", "")
        )
        insert_raw_signal(signal)
        signals.append(signal)
    return signals