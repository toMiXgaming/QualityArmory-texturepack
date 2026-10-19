# QualityArmory texturepack (AXON)

Paczka zasobów do QualityArmory na Paper 1.21.4. To kopia domyślnej paczki `QualityArmory-21.zip` (QualityGuns 2.1.9) z autorskimi, szczegółowymi modelami czterech broni. Reszta broni, dźwięki i numery modeli są bez zmian.

| Broń | Przedmiot | custom_model_data | Model w paczce |
|---|---|---|---|
| AK47 | crossbow | 4 | `qualityarmory:gun/ak47` |
| Remington 870 | crossbow | 7 | `qualityarmory:gun/remmington` |
| M4A1-S | crossbow | 25 | `qualityarmory:gun/m4a1s` |
| Makarov PM | crossbow | 53 | `qualityarmory:gun/makarov` |

Zmienione pliki względem oryginału:
- `assets/qualityarmory/models/gun/{ak47,m4a1s,remmington,makarov}.json` – nowe modele (AK 75 elementów, M4 76, Remington 56, Makarov 30).
- `assets/qualityarmory/textures/axon/{ak47,m4a1s,remmington,makarov}.png` – tekstury 128×128 (Makarov ma gęstsze teksele, bo jest mały).
- `assets/minecraft/atlases/blocks.json` – dodane źródło `axon/` (bez tego tekstury byłyby fioletowo-czarne).
- `pack.mcmeta` – opis zaczyna się od „AXON”, żeby w grze było widać, która paczka jest wczytana.

## Skiny premium

Skin używa tego samego modelu co bazowa broń (te same elementy i pozycje, także celowanie), różni się tylko teksturą. Generuje je `gen.py` (słownik `SKINS`; AK ma własne malowania, reszta broni wspólne motywy z `generic_skin`), a `build_pack.py` dopisuje je do `assets/minecraft/items/crossbow.json`. Numery idą blokami po dziesięć na broń (AK 101–, M4A1-S 111–, Remington 121–, Makarov 131–), bo oryginalne numery QA kończą się na 85.

Motywy: Złoto (złoto z grawerem, heban), Neon (czarny mat i karbon, świecące krawędzie cyan/magenta), Polar (biały, pomarańczowe i czarne pasy), Damast (stal damasceńska, czerwone drewno, mosiądz), Lawa (obsydian z żarzącymi się pęknięciami), Galaktyka (mgławica z gwiazdami, chromowane części), Holo (tęczowa folia holograficzna). Każda broń ma wszystkie siedem.

| Skin | custom_model_data | name w QualityArmory (`/qa give <gracz> <name>`) |
|---|---|---|
| AK47 [Złoto] | 101 | `ak47_zloto` |
| AK47 [Neon] | 102 | `ak47_neon` |
| AK47 [Polar] | 103 | `ak47_polar` |
| AK47 [Damast] | 104 | `ak47_damast` |
| AK47 [Lawa] | 105 | `ak47_lawa` |
| AK47 [Galaktyka] | 106 | `ak47_galaktyka` |
| AK47 [Holo] | 107 | `ak47_holo` |
| M4A1-S [Złoto] | 111 | `m4a1s_zloto` |
| M4A1-S [Neon] | 112 | `m4a1s_neon` |
| M4A1-S [Lawa] | 113 | `m4a1s_lawa` |
| M4A1-S [Galaktyka] | 114 | `m4a1s_galaktyka` |
| M4A1-S [Polar] | 115 | `m4a1s_polar` |
| M4A1-S [Damast] | 116 | `m4a1s_damast` |
| M4A1-S [Holo] | 117 | `m4a1s_holo` |
| Remington [Złoto] | 121 | `remmington_zloto` |
| Remington [Neon] | 122 | `remmington_neon` |
| Remington [Lawa] | 123 | `remmington_lawa` |
| Remington [Galaktyka] | 124 | `remmington_galaktyka` |
| Remington [Damast] | 125 | `remmington_damast` |
| Remington [Polar] | 126 | `remmington_polar` |
| Remington [Holo] | 127 | `remmington_holo` |
| Makarov [Złoto] | 131 | `makarov_zloto` |
| Makarov [Neon] | 132 | `makarov_neon` |
| Makarov [Lawa] | 133 | `makarov_lawa` |
| Makarov [Galaktyka] | 134 | `makarov_galaktyka` |
| Makarov [Damast] | 135 | `makarov_damast` |
| Makarov [Polar] | 136 | `makarov_polar` |
| Makarov [Holo] | 137 | `makarov_holo` |

Model w paczce to `qualityarmory:gun/<name>`. Na serwerze skin to „attachment” QualityArmory z `baseGun` ustawionym na bazową broń, więc przejmuje jej statystyki. Pliki z `serwer/attachments/` trzeba skopiować do `plugins/QualityArmory/attachments/` i zrestartować serwer. Skiny nie są do craftingu ani w sklepie QA.

## Mapa AxonMap (shader)

Paczka zawiera też shadery `assets/minecraft/shaders/core/rendertype_text` i `position_tex_color` z pluginu [AxonMap](https://github.com/toMiXgaming/AXONMAP). Rysuje on mapę świata na cały ekran po wpisaniu `/mapa`. Shader rozpoznaje tylko mapy pluginu (po znaczniku w pierwszym wierszu), więc zwykłe napisy, tabliczki i mapy działają jak wcześniej. Przy otwartej mapie chowają też hotbar, serduszka i celownik. Źródła są w `zrodla/shadery/`, a `build_pack.py` dodaje je do zipa.

## Zrzut (AXON-Structure)

Model skrzyni zrzutu: oliwkowa skrzynia z okuciami, pasem ostrzegawczym, złożonym spadochronem na wieku i świecącą czerwoną lampą. Przedmiot `axon:zrzut` (komponent `item_model`, dowolny materiał), model `axon:block/zrzut`, tekstura `axon:item/zrzut` (64×64). Plugin AXON-Structure stawia w strukturze beczkę jako prawdziwy pojemnik i nad nią wyświetlacz przedmiotu z tym modelem; model jest odrobinę większy od bloku, więc beczki nie widać. Generator: `zrodla/gen_zrzut.py`, podgląd: `podglady/zrzut.png`.

## Rekwizyty do struktur (AXON-Structure)

`zrodla/gen_rekwizyty.py` robi dwa modele stawiane przez plugin AXON-Structure jako wyświetlacze przedmiotów:

- `axon:wrak_mi8` – wrak śmigłowca Mi-8 na lądowisku jednostki wojskowej: przeszklony kokpit, otwarte drzwi przesuwne (da się wejść do środka po skrzynię), silniki, połamane łopaty, belka ogonowa z szachownicą, zbiorniki paliwa. Model opisany jest w kratkach `jednostka.axs`; plugin rysuje go ze skalą 8, a kolizję dają bariery w pliku struktury. Podgląd: `podglady/wrak_mi8.png`.
- `axon:lozko` – metalowe łóżko z materacem w paski, wojskowym kocem i poduszką. Plugin stawia je zamiast łóżek z Minecrafta (poza oazą). Podgląd: `podglady/lozko.png`.

Meble z `zrodla/gen_meble.py` (jedna kratka, przód na południe): `axon:regal` (regał z segregatorami), `axon:kartoteka` (szafa kartotekowa), `axon:umywalka`, `axon:warsztat` (stół z imadłem), `axon:kuchenka` (kuchenka gazowa), `axon:piecyk` (koza), `axon:radiostacja`. Plugin stawia je zamiast bloków wymienionych w `meble.bloki` w configu. Podgląd: `podglady/meble.png`.

## Wgranie na serwer

Repo musi być **publiczne**, inaczej gracze nie pobiorą paczki. W `plugins/QualityArmory/config.yml`:

```yaml
DefaultResourcepackOverride: true
DefaultResourcepack:
  '0': https://github.com/ZombieStriker/QualityArmory-Resourcepack/releases/download/latest/QualityArmory.zip
  1-21-4: https://raw.githubusercontent.com/toMiXgaming/QualityArmory-texturepack/main/QualityArmory-21-axon.zip
```

`DefaultResourcepackOverride` musi być `true`, inaczej QualityArmory wyśle swoją paczkę. Paczka jest wysyłana przy wejściu na serwer, więc po zmianie trzeba wejść ponownie (`/qa reload` jej nie wysyła).

## Jak działa celowanie

QualityArmory przy celowaniu przekłada broń do drugiej ręki, więc pozycja przy celowaniu to `display.firstperson_lefthand`. Pozostałe pozycje (biodro, trzecia osoba, GUI, ziemia) są przejęte z modeli QualityArmory, bo nowe modele leżą w tym samym układzie (wylot lufy, wysokość osi, długość).

- AK47 i M4A1-S: oko tuż za tylnym celownikiem, broń przechylona o 2,5°, muszka na krzyżyku. M4 ma cienki, otwarty przeziernik.
- Makarov PM: tak samo, oko kilka jednostek za szczerbinką, przechył 2,5°, muszka w szczerbince na krzyżyku. Oryginalny model QA nie ma pozycji `head`, więc nowy też jej nie ma.
- Remington: bez prawdziwego celowania (właściciel serwera tak zostawił).

## Historia

1. Pierwsza wersja trzech modeli; celowanie „zza kolby” (za mało czytelne).
2. Celowanie AK47 zza szczerbinki z przechyłem 2,5° – zaakceptowane w grze.
3. Zamknięta dziura przed magazynkiem AK47 (komora sięga do łoża jak prawdziwa przednia część komory zamkowej); M4A1-S dostał to samo celowanie co AK z otwartym przeziernikiem (w grze była czarna kolumna i zasłonięty widok).

4. Makarov PM (custom_model_data 53): nowy model z suwadłem, bezpiecznikiem po lewej, kurkiem, osłoną spustu i okładziną z bakelitu; celowanie zza szczerbinki.

5. Skiny premium: po 7 do AK47 (101–107), M4A1-S (111–117), Remingtona (121–127) i Makarova (131–137).

Do sprawdzenia w grze: celowanie M4A1-S po poprawce 3 i celowanie Makarova.

## Katalogi

- `QualityArmory-21-axon.zip` – gotowa paczka.
- `modele/` – wygenerowane modele i tekstury (to samo co w zipie).
- `podglady/` – podglądy i porównania ze starymi modelami (`<broń>-skiny.png` – skiny danej broni).
- `serwer/attachments/` – pliki skinów do configu QualityArmory.
- `zrodla/` – generator (`gen.py`), renderer podglądów (`render.py`, `preview.py`), dopasowanie celowania (`tune_ads.py`), szukanie dziur (`gaps.py`) i budowanie zipa (`build_pack.py`).

Przebudowa: pobierz oryginał `https://github.com/ZombieStriker/QualityArmory-Resourcepack/releases/download/latest/QualityArmory-21.zip`, rozpakuj go do `/tmp/qa/pack` i zapisz zip jako `/tmp/qa/QA21.zip` (albo podaj ścieżkę jako argument `build_pack.py`), potem w `zrodla/`: `python3 gen.py && python3 gen_zrzut.py && python3 gen_rekwizyty.py && python3 gen_meble.py && python3 preview.py && python3 preview.py skiny-ak47 skiny-m4a1s skiny-remmington skiny-makarov && python3 build_pack.py`. `gen.py makarov` generuje tylko wybraną broń. Opis paczki bierze się z `zrodla/pack.mcmeta`. Remington w `modele/` różni się od świeżo wygenerowanego tylko zapisem PNG i liczb, więc przy budowaniu można skopiować go z `modele/` do `zrodla/build/`. Skrypty mogą wymagać poprawienia ścieżek wyjściowych.
