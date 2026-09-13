import yaml
from pydantic import BaseModel


class SourceItem(BaseModel):
    name: str
    url: str
    type: str
    priority: int
    category: str


def load_sources(path: str = "sources.yaml") -> list[SourceItem]:
    with open(path, "r", encoding="utf-8") as f:
        config = yaml.safe_load(f)
    return [SourceItem(**s) for s in config["sources"]]
