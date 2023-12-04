import unittest
import parameterized

from .gnujdb import czymamy


class TestCzyMamyGnuj(unittest.TestCase):
    @parameterized.parameterized.expand(
        [
            ("Mamy może czas na to?", None),
            (
                "Mamy może w hs-ie nożyce do metalu? ",
                "https://g.hs-ldz.pl/search?query=no%C5%BCyce%20do%20metalu",
            ),
            (
                "Mamy w hs-ie nożyce do metalu? ",
                "https://g.hs-ldz.pl/search?query=no%C5%BCyce%20do%20metalu",
            ),
            (
                "Mamy w hs-ie nożyce ? Bo szukałem cośtamcośtam.",
                "https://g.hs-ldz.pl/search?query=no%C5%BCyce",
            ),
            ("Czy jest na to czas?", None),
            ("Czy jest w hs miarka?", "https://g.hs-ldz.pl/search?query=miarka"),
            ("Czy jest w hs miarka ", None),
            (
                "Mamy może miarkę w spejsie?",
                "https://g.hs-ldz.pl/search?query=miark%C4%99",
            ),
        ]
    )
    def test_method(self, message, result):
        self.assertEqual(czymamy(message), result)


if __name__ == "__main__":
    unittest.main()
