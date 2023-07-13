import hashlib
import os.path
import re
import functools
from enum import Enum
from typing import List, Set, Optional, Collection

import requests


class EUnit(Enum):
    GiB = "GiB"
    MiB = "MiB"
    KiB = "KiB"


G_LINK = "link"
G_TITLE = "title"
G_SIZE = "size"
G_UNIT = "unit"


class BaseEntry:
    def __init__(self, name: str):
        self.name = name

    @property
    def games(self) -> Set['Game']:
        raise NotImplementedError()


class UrlEntry(BaseEntry):
    def __init__(self, url: str, name: str):
        super().__init__(name)
        self._games = set(parse_url(url))

    @property
    def games(self) -> Set['Game']:
        return self._games


class CollectionEntry(BaseEntry):
    def __init__(self, name: str, entries: List[BaseEntry]):
        super().__init__(name)
        self.entries = entries

    @property
    def games(self) -> Set['Game']:
        def reduce_func(previous: Set['Game'], addend: Set['Game']) -> Set['Game']:
            return previous.union(addend)

        return functools.reduce(reduce_func, [entry.games for entry in self.entries], set())


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
        if self.unit == EUnit.KiB:
            return self.size / 1024 / 1024
        raise Exception("Invalid unit")

    @property
    def mib(self) -> float:
        if self.unit == EUnit.KiB:
            return self.size / 1024
        if self.unit == EUnit.MiB:
            return self.size
        if self.unit == EUnit.GiB:
            return self.size * 1024
        raise Exception("Invalid unit")


def _parse_games(content: str) -> List[Game]:
    pattern = rf'<tr><td><a href=\"(?P<{G_LINK}>.+)\" title=\".*\">(?P<{G_TITLE}>.*)</a></td><td>(?P<{G_SIZE}>.+) (?P<{G_UNIT}>KiB|MiB|GiB)</td><td>.*</td></tr>'
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


def print_entry_info(entry: BaseEntry, depth: int = 0,
                     sub_entries_depth_limit: Optional[int] = None):
    games = entry.games
    print_games_info(games, entry.name, depth, newline=False)

    if (sub_entries_depth_limit is None or depth < sub_entries_depth_limit) \
            and isinstance(entry, CollectionEntry) and len(entry.entries) > 0:
        for child_entry in entry.entries:
            print_entry_info(child_entry, depth=depth + 1,
                             sub_entries_depth_limit=sub_entries_depth_limit)
    else:
        print()


def print_games_info(games: Collection[Game], name: str, depth: int = 0, newline: bool = True):
    prefix = depth * "   "
    print(prefix + name)
    print(prefix + "Amount:", len(games))
    games_sum = functools.reduce(lambda a, b: a + b.mib, games, 0)
    if games_sum > 1024:
        print(prefix + "Size:", round(games_sum / 1024, 1), "GiB")
    else:
        print(prefix + "Size:", round(games_sum, 1), "MiB")
    if newline:
        print()


def run_gba():
    print("GBA")
    gba_games = parse_url(
        "https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Game%20Boy%20Advance/")

    combined_games = []
    combined_games += gba_games

    print_games_info(combined_games)


if __name__ == '__main__':
    atari_2600 = UrlEntry(
        "https://myrient.erista.me/files/No-Intro/Atari%20-%202600/",
        "Atari 2600"
    )

    g3ds_reg = UrlEntry(
        "https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Nintendo%203DS%20(Decrypted)/",
        "Regular")
    g3ds_new = UrlEntry(
        "https://myrient.erista.me/files/No-Intro/Nintendo%20-%20New%20Nintendo%203DS%20(Decrypted)/",
        "New 3DS")
    g3ds_eshop = UrlEntry(
        "https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Nintendo%203DS%20(Digital)%20(CDN)/",
        "Digital")
    g3ds = CollectionEntry("3DS", [g3ds_reg, g3ds_eshop, g3ds_new])

    ds_reg = UrlEntry(
        "https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Nintendo%20DS%20(Decrypted)/",
        "Regular")
    dsi = UrlEntry(
        "https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Nintendo%20DSi%20(Decrypted)/",
        "DSi")
    ds_digital = UrlEntry(
        "https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Nintendo%20DSi%20(Digital)/",
        "Digital")
    download_play = UrlEntry(
        "https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Nintendo%20DS%20(Download%20Play)/",
        "Download play")
    ds = CollectionEntry("DS", [ds_reg, dsi, ds_digital, download_play])

    gba = UrlEntry(
        "https://myrient.erista.me/files/No-Intro/Nintendo%20-%20Game%20Boy%20Advance/",
        "GBA")

    gc = UrlEntry(
        "https://myrient.erista.me/files/Redump/Nintendo%20-%20GameCube%20-%20NKit%20RVZ%20[zstd-19-128k]/",
        "GameCube")

    wii = UrlEntry(
        "https://myrient.erista.me/files/Redump/Nintendo%20-%20Wii%20-%20NKit%20RVZ%20[zstd-19-128k]/",
        "Wii")

    wii_u = UrlEntry(
        "https://myrient.erista.me/files/Redump/Nintendo%20-%20Wii%20U%20-%20WUX/",
        "Wii U")

    all_games = CollectionEntry("All", [atari_2600, gba, gc, ds, g3ds, wii, wii_u])

    # Print data

    print_entry_info(all_games)

    # print_games_info([g for g in g3ds.games if "Europe" in g.title], "Only Europe")
    # print_games_info([g for g in g3ds.games if "USA" in g.title], "Only USA")
    # print_games_info([g for g in g3ds.games if "Japan" not in g.title], "No Japan")
    # print_games_info([g for g in g3ds.games if g.gib < 1], "Only games < 1 GiB")
    # print_games_info([g for g in g3ds.games if g.gib < 0.7], "Only games < 0.7 GiB")
    # print_games_info([g for g in g3ds.games if g.gib < 0.4], "Only games < 0.4 GiB")
    # print_games_info(g3ds_eshop.games, "Only eshop games")
    # print_games_info(set.union(g3ds_reg.games, g3ds_new.games), "Only non-eshop games")
    # print_games_info([g for g in g3ds.games if "(Demo)" in g.title], "Only demos")
    # print_games_info([g for g in g3ds.games if "Doko Demo Honya-san" in g.title],
    #                  "Only \"Doko Demo Honya-san\" games (wtf)")
