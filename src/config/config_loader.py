import yaml
from pydantic import BaseModel
from typing import List

class SourceItem(BaseModel):
    name: str
    url: str
    type: str
    priority: int
    category: str

def load_sources(path: str = "sources.yaml") -> List[SourceItem]:
    with open(path, "r") as f:
        config = yaml.safe_load(f)
    return [SourceItem(**s) for s in config["sources"]]