import hashlib
import os.path
import re
import functools
from enum import Enum
from typing import List

import requests


class EUnit(Enum):
    GiB = "GiB"
    MiB = "MiB"


G_LINK = "link"
G_TITLE = "title"
G_SIZE = "size"
G_UNIT = "unit"


class Game:
    def __init__(self, match: re.Match):
        self.link = match.group(G_LINK)
        self.title = match.group(G_TITLE)
        self.size = float(match.group(G_SIZE))

        unit = match.group(G_UNIT)
        unit_set = False
        for unit_value in EUnit:
            if unit == str(unit_value.value):
                self.unit = unit_value
                unit_set = True
                break
        if not unit_set:
            raise Exception(f"Failed to parse unit '{unit}'")

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f"{self.size} {self.unit.value} - '{self.title}' | ({self.link})"

    def __eq__(self, other: 'Game'):
        return self.title == other.title and self.size == other.size and self.unit == other.unit

    def __hash__(self):
        return self.title.__hash__() * 11 + \
            self.size.__hash__() * 17 + \
            self.size.__hash__() * self.unit.value.__hash__()

    @property
    def gib(self) -> float:
        if self.unit == EUnit.GiB:
            return self.size
        if self.unit == EUnit.MiB:
            return self.size / 1024
        raise Exception("Invalid unit")

    @property
    def mib(self) -> float:
        if self.unit == EUnit.MiB:
            return self.size
        if self.unit == EUnit.GiB:
            return self.size * 1024
        raise Exception("Invalid unit")


def _parse_games(content: str) -> List[Game]:
    pattern = rf'<tr><td><a href=\"(?P<{G_LINK}>.+)\" title=\".*\">(?P<{G_TITLE}>.*)</a></td><td>(?P<{G_SIZE}>.+) (?P<{G_UNIT}>MiB|GiB)</td><td>.*</td></tr>'
    return [Game(m) for m in re.finditer(pattern, content)]


def parse_file(filepath: str) -> List[Game]:
    with open(filepath, "r") as f:
        text = f.read()
    return _parse_games(text)


def parse_urls(*urls: str, invalidate_cache: bool = False) -> List[Game]:
    result = []
    for url in urls:
        result += parse_url(url, invalidate_cache)
    return result


def parse_url(url: str, invalidate_cache: bool = False) -> List[Game]:
    keep_characters = (' ', '.', '_')
    conformed_url = "".join(c for c in url if c.isalnum() or c in keep_characters).rstrip()
    cache_dir = "cache"
    if not os.path.isdir(cache_dir):
        os.mkdir(cache_dir)
    file_path = cache_dir + os.sep + conformed_url + "__" + hashlib.md5(url.encode('utf-8')).hexdigest() + ".html"
    if invalidate_cache and os.path.exists(file_path):
        os.remove(file_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return parse_file(file_path)
    else:
        text = requests.get(url).text
        with open(file_path, "w") as f:
            f.write(text)
        return _parse_games(text)


def print_info(games: List[Game], name: str | None = None):
    if name:
        print(name)
    print("Amount:", len(games))
    print("Size:", round(functools.reduce(lambda a, b: a + b.gib, games, 0), 1), "GiB")
    print()


if __name__ == '__main__':
    regular_games = parse_url("https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Nintendo%203DS%20(Decrypted)/")
    new_3ds_games = parse_url("https://myrient.erista.me/files/No-Intro/Nintendo%20-%20New%20Nintendo%203DS%20(Decrypted)/")
    eshop_games = parse_url("https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Nintendo%203DS%20(Digital)%20(CDN)/")

    combined_games = []
    combined_games += regular_games
    combined_games += new_3ds_games
    combined_games += eshop_games

    print_info(combined_games, "All")
    print_info([g for g in combined_games if "Europe" in g.title], "Only Europe")
    print_info([g for g in combined_games if "USA" in g.title], "Only USA")
    print_info([g for g in combined_games if "Japan" not in g.title], "No Japan")
    print_info([g for g in combined_games if g.gib < 1], "Only games < 1 GiB")
    print_info([g for g in combined_games if g.gib < 0.7], "Only games < 0.7 GiB")
    print_info([g for g in combined_games if g.gib < 0.4], "Only games < 0.4 GiB")
    print_info(eshop_games, "Only eshop games")
    print_info(regular_games + new_3ds_games, "Only non-eshop games")
    print_info([g for g in combined_games if "(Demo)" in g.title], "Only demos")
    print_info([g for g in combined_games if "Doko Demo Honya-san" in g.title], "Only \"Doko Demo Honya-san\" games (wtf)")
