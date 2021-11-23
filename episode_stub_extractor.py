#!/usr/bin/python3

import requests
import xml.etree.ElementTree as ET
from operator import itemgetter
from dateutil.parser import parse as parseDate
import sys, os

# optional imports
try:
    from tqdm import tqdm  # for progress logging
except ImportError:
    def tqdm(*args):
        return args[0]


XML_URL = "https://feed.podbean.com/nonewnotifications/feed.xml"


def get_text(e):
    return e.text


def strip_tag(tagname, el):
    return el.replace(f"<{tagname}>", "").replace(f"</{tagname}>", "")


def parse_episode(episode):
    epnum = int(episode.find("itunes:episode", namespaces).text)
    airDate = parseDate(episode.find("pubDate").text)
    airDate = airDate.strftime("%B %-d, %Y")

    title = episode.find("title").text
    title = title.replace("START LISTENING HERE", "")
    if " - " in title: title = title.split(" - ")[-1]

    deschtml = episode.find("description").text
    lines = [line for line in deschtml.split("\n") if line]
    desc = strip_tag("p", lines[0])
    desc2 = strip_tag("p", lines[1]) if len(lines) > 1 else ""

    duration = episode.find("itunes:duration", namespaces).text
    if duration.count(":") == 1:
        m, s = map(int, duration.split(":"))
        if s >= 30: m += 1
        dstr = f"{m} minute"
        if m > 1: dstr += 's'
    else:
        h, m, s = map(int, duration.split(":"))
        if s > 30: m += 1
        dstr = f"{h} hour" 
        if h > 1: dstr += 's'
        if m != 0:
            dstr += f" {m} minute" 
            if m > 1: dstr += 's'
    duration = dstr

    return epnum, dict(epnum=epnum,
                       airDate=airDate,
                       title=title,
                       desc=desc,
                       desc2=desc2,
                       duration=duration)


def get_episode_link(data, epnum):
    ep = data.get(epnum)
    if ep is None:
        return "-"
    else:
        return "[[" + ep["title"] + "]]"


def log(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


episode_fandom_template = """
{{{{Episode
 | title           = {title}
 | episodeNumber   = {epnum}
 | airDate         = {airDate}
 | length          = {duration}
 | previousEpisode = {prv}
 | nextEpisode     = {nxt}
}}}}

==='''Episode Description'''===

{desc}

[
{desc2}
]

<br />
[[Category:Episodes|{epnum}]]
{{{{DEFAULTSORT:{title}}}}}
"""


if __name__ == "__main__":

    helpargs = {"-h", "--help", "?", "help"}
    if helpargs.intersection(sys.argv[1:]):
        print(f"usage: {sys.argv[0]} [-a|--print-all]")
        print("\ndisclaimers")
        print("  * human inspection of episode stubs advised")
        print("  * only picks up at most two paragraphs of episode description")
        print("  * tries to clean up epsiode titles",
                  "(numbering, START LISTENING HERE)")
        sys.exit(0)

    PRINT_ALL = False
    if len(sys.argv) > 1:
        PRINT_ALL = sys.argv[1] in ["-a", "--print-all"]

    log("fetching feed xml...")
    response = requests.get(XML_URL)

    xml_file = "temp_rss.xml"
    log("saving to", xml_file)
    with open(xml_file, 'w') as f: f.write(response.content.decode())

    log("parsing xml namespaces")
    namespaces = dict(map(itemgetter(1), ET.iterparse(xml_file, events=['start-ns'])))

    tree = ET.parse(xml_file)
    root = tree.getroot()

    data = dict()
    items = root.findall("./channel/item")
    for item in tqdm(items, "parsing episodes"):
        epnum, epdata = parse_episode(item)
        data[epnum] = epdata

    fstr = episode_fandom_template
    log("printing episode stubs")
    last_episode = max(data.keys())
    for item in sorted(data.keys()):
        prv = get_episode_link(data, item-1)
        nxt = get_episode_link(data, item+1)
        if PRINT_ALL or item == last_episode:
            print(fstr.format(prv=prv, nxt=nxt, **data[item]))

    log("cleaning up")
    os.remove(xml_file)
