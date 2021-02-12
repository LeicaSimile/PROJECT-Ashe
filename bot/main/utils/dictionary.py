import re
import requests
from main import settings

class DictionaryEntry():
    def __init__(self, data: dict):
        self._raw_data = data
        self.is_offensive = False
        self.short_definitions = []
        self.variants = []

        self._parse_data()

    def _parse_data(self):
        self.is_offensive = self._raw_data["meta"]["offensive"]
        self.short_definitions = self._raw_data.get("shortdef")

class DictionaryCache():
    def __init__(self, limit=1000):
        self._cache = {}
        self.limit = limit

    def add_entries(self, word: str, entries: list):
        self._check_entries()
        self._cache[word] = {"requests": 1, "entries": entries}

    def get_entries(self, word: str):
        """Returns cached list of a given word's entries.

        Can be a list of DictionaryEntry objects or a list of suggested strings to search.
        """
        if word in self._cache:
            self._cache[word]["requests"] += 1
            return self._cache[word]["entries"]
        
        return []

    def _check_entries(self):
        """Remove entry with least amount of requests if cache is at or over limit"""
        if len(self._cache) >= self.limit:
            sorted_cache = [k for k, v in sorted(self._cache.items(), key=lambda item: item[1]["requests"])]
            self._cache.pop(sorted_cache[0], None)


regular_cache = DictionaryCache(limit=settings.DICT_REGULAR_CACHE_LIMIT)
simple_cache = DictionaryCache(limit=settings.DICT_SIMPLE_CACHE_LIMIT)
format_tokens = [
    {
        "start_token": "{b}",
        "end_token": "{\/b}",
        "pattern": r"",
        "start_sub": "**",
        "end_sub": "**"
    }
]

def format_text(text: str):
    pass

def regular_lookup(word: str):
    """Looks up given word in Merriam-Webster Collegiate dictionary
    
    Args:
        word(str): Word to look up in dictionary.

    Returns:
        list: Can be a list of DictionaryEntry objects or a list of suggested strings to search up
              (in case of misspelling)

    """
    entries = []
    entries = regular_cache.get_entries(word)
    if not entries:
        req_location = f"{settings.DICT_REGULAR_API_URL}{word}?key={settings.DICT_REGULAR_API_KEY}"
        response = requests.get(req_location, timeout=30)
        res_data = response.json()
        if not res_data:
            return None # Word not found

        clean_word = re.sub(r"\s+", " ", word.strip().lower())
        for entry in res_data:
            if re.match(
                    r"{word}(?:\:[\d\w]+)?$".format(word=clean_word),
                    entry.get("meta", {"id": ""})["id"],
                    re.I):
                try:
                    # Check for spelling variants
                    if not entry.get("shortdef") and entry.get("cxs"):
                        for variant in regular_lookup(entry["cxs"][0]["cxtis"][0]["cxt"]):
                            entries.append(variant)
                    else:
                        entries.append(DictionaryEntry(entry))
                except (IndexError, KeyError) as e:
                    continue
            else:
                entries.append(entry)

        regular_cache.add_entries(word, entries)
        
    return entries
