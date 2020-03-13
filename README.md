MariuszBot
=========

Nasz bot do Telegrama. Projekt integracyjny - jego celem było:

1. przetestowanie wspólnej pracy,
2. ogarnięcie jak się w Telegramie robi boty,
3. śmieszkowanie

Bot reaguje na różne wiadomości i komendy. Informuje o najbliższym zaplanowanym
spotkaniu, po restarcie pisze wszystkim osobom które z nim gadały na prywatnym
kanale o tym, że załadował nową wersję.

Szczegóły implementacyjne / wymagania
=====================================

**Ta sekcja może się szybko zdezaktualizować. Kod ma zawsze pierwszeństwo nad
informacjami z tej sekcji. Jeśli widzisz, że jakiś fragment jest nieaktualny,
usuń go albo zrób pull request z sugestią zmiany.**

Bot wymaga uprawnień do przypinania wiadomości na kanale, na którym ma
operować. Inaczej może zcrashować, a jeśli był uruchomiony z
--restart=unless-required, może wpaść w dziwną pętlę i zaspamować kanał.

Bot wymaga dostępu do katalogu .git. Wrzuciliśmy do Dockerfile taki hack,
że w oddzielnym stage'u .git jest wciągany, żeby ustalić jaka jest aktualna
wersja budowanego kodu. Jeśli odpalasz projekt bez Dockera, po prostu nie
usuwaj katalogu .git.

Stan trzymany jest bazie sqlite, do której ścieżka powinna być podana w
zmiennej środowiskowej SCIEZKA\_DO\_BAZY\_CHATOW. Klucz do Telegrama podaje
się przez zmienną środowiskową API\_KEY.

W razie problemów z postawieniem bota samodzielnie, zerknij tutaj:

https://stackoverflow.com/questions/50204633/allow-bot-to-access-telegram-group-messages

Deployment
==========

**Ta sekcja może się szybko zdezaktualizować. Rzeczywistość ma zawsze
pierwszeństwo nad informacjami z tej sekcji. Jeśli widzisz, że jakiś fragment
jest nieaktualny usuń go albo zrób pull request z sugestią zmiany.**

Bota hostuje d33tah na swoim domowym PC na Retkinii. ISP to Toya (ADSL).

Jeśli bot jest niegrzeczny, należy go ubić - uprawnienia admina na głównym
kanale ma poza d33tahem ma @gazowany\_smalec oraz @BluRaf.

Bot ma ustawionego autobuilda na Docker Hubie, więc 10min po pushnięciu czegoś
do mastera zbuduje się obraz hakierspejs/mariusz. Na PC d33taha jest też
postawiony watchtower:

https://github.com/containrrr/watchtower

Sprawdza on co minutę czy obraz został zmieniony i jeśli tak, restartuje
kontener. W praktyce oznacza to, że commit na mastera może spowodować
automatyczne załadowanie nowej wersji kodu na produkcję bez interwencji admina.

**Dzięki temu każdy może zmieniać co chce jeśli należy do organizacji
Hakierspejs i inny członek HSu mu zrobi recenzję kodu.**
