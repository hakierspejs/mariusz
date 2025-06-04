import urllib.parse


TRIGGERS = {
    "jest moze",
    "jest może",
    "czy jest",
    "czy mamy",
    "mamy może",
    "mamy moze",
    "może mamy",
    "moze mamy",
}


def czymamy(message: str) -> str | None:
    url = None
    hsl_phrases = (
        "w spejse",
        "w spejsie",
        "w hackerspejsie",
        "w hs-ie",
        "w hs",
        "w hsie",
    )
    null_phrases = ("jakiś", "jakis", "może", "moze", "mamy")
    text = message.lower().split("?")[0].strip()
    if "?" in message and any((x in text for x in hsl_phrases)):
        for item in TRIGGERS:
            text = text.replace(item, "")
        for item in hsl_phrases:
            text = text.replace(item, "")
        for item in null_phrases:
            text = text.replace(item, "")
        url = "https://g.hs-ldz.pl/search?query=" + urllib.parse.quote(
            text.strip()
        )
    return url
