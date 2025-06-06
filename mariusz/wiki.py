"""Common functions used by our bot in order to process Github wikis."""

import urllib.parse

import dateutil.parser
import lxml.etree as E
import httpx

NS = "{http://www.w3.org/2005/Atom}"


async def get_wiki_entries(url: str):
    """Returns all Wiki entries for a given URL."""
    async with httpx.AsyncClient() as client:
        r = await client.get(url, timeout=10)
        r.raise_for_status()
        text = r.text.encode()
    tree = E.fromstring(text)
    entry_f = E.ETXPath(NS + "entry")
    entries = entry_f(tree)
    updated_f = E.ETXPath(".//" + NS + "updated/text()")
    entries.sort(key=lambda e: dateutil.parser.parse(updated_f(e)[0]))
    return entries


async def build_wiki_message() -> str:
    """Builds a message describing the current state of the wiki."""
    wiki_url = "https://github.com/hakierspejs/wiki/wiki.atom"
    try:
        entries = await get_wiki_entries(wiki_url)
        if not entries:
            return ""
        latest = entries.pop()
    except E.XMLSyntaxError:
        return ""
    title_raw = E.ETXPath(".//" + NS + "link/@href")(latest)[0]
    title = title_raw.split("/hakierspejs/wiki/wiki")[1] or "Home"
    title = urllib.parse.unquote(title.lstrip("/"))
    author = E.ETXPath(".//" + NS + "author/*/text()")(latest)[0]
    commit = E.ETXPath(".//" + NS + "id/text()")(latest)[0].split("/")[-1]
    base_url = "https://github.com/hakierspejs/wiki/wiki"
    url = base_url + f"/{title}/_compare/{commit}%5E...{commit}"
    return (
        f'Wiki: {author} zmienił(a) "{title.replace("-", " ")}".\n\n'
        f"Sprawdź zmianę tutaj: {url}"
    )


if __name__ == "__main__":
    print(build_wiki_message())
