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

## Mapa AxonMap (shader)

Paczka zawiera też shadery `assets/minecraft/shaders/core/rendertype_text` i `position_tex_color` z pluginu [AxonMap](https://github.com/toMiXgaming/AXONMAP). Rysuje on mapę świata na cały ekran po wpisaniu `/mapa`. Shader rozpoznaje tylko mapy pluginu (po znaczniku w pierwszym wierszu), więc zwykłe napisy, tabliczki i mapy działają jak wcześniej. Przy otwartej mapie chowają też hotbar, serduszka i celownik. Źródła są w `zrodla/shadery/`, a `build_pack.py` dodaje je do zipa.

## Reaktor działki (AxonPlot)

Rdzeń działki z [AxonPlot](https://github.com/toMiXgaming/AXONPLOT) wygląda jak reaktor. Plugin stawia na bloku rdzenia ItemDisplay z przedmiotem `crying_obsidian` i `custom_model_data`, a `assets/minecraft/items/crying_obsidian.json` wybiera po tej liczbie model z `assets/axon/`. Zwykły crying obsidian (bez liczby) wygląda jak w vanilli.

Numer modelu to `7100 + 20 × skin + stan`, gdzie stan to 1 zasilony, 2 mało paliwa (przygaszony żółty, migocze), 3 wygaszony, 4 atak (czerwony, szybki puls). Kryształ nad reaktorem ma numer o 10 większy (wygaszony reaktor go nie ma).

| Skin | Obudowa | Kryształ | Zasilony świeci |
|---|---|---|---|
| 0 Standard | 7101–7104 | 7111–7114 | zielono |
| 1 Kwantowy | 7121–7124 | 7131–7134 | błękitnie |
| 2 Pustka | 7141–7144 | 7151–7154 | fioletowo |
| 3 Piekielny | 7161–7164 | 7171–7174 | turkusowo (ogień dusz) |
| 4 Królewski | 7181–7184 | 7191–7194 | różowo |

![Skiny reaktora](podglady/reaktor-skiny.png)

Obudowa ma wgłębienia, więc plugin pokazuje ją w skali 1,2 (inaczej prawdziwy blok przebijałby przez okna). Energia w oknach, emiter na górze i kryształ są animowanymi teksturami (`.png.mcmeta`). Generator: `zrodla/gen_reactor.py`, podglądy i miniatury do menu w pluginie (`out/miniatury/`, kopiowane do `AXONPLOT/src/main/resources/reactor/`): `zrodla/preview_reactor.py`, dopisanie do gotowego zipa bez pełnej przebudowy: `zrodla/dodaj_reaktor.py` (pełna przebudowa `build_pack.py` też dodaje reaktor). Gotowe pliki są w `modele/reactor/`, podglądy w `podglady/reaktor-*`.

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

Do sprawdzenia w grze: celowanie M4A1-S po poprawce 3 i celowanie Makarova.

## Katalogi

- `QualityArmory-21-axon.zip` – gotowa paczka.
- `modele/` – wygenerowane modele i tekstury (to samo co w zipie).
- `podglady/` – podglądy i porównania ze starymi modelami.
- `zrodla/` – generator broni (`gen.py`) i reaktora (`gen_reactor.py`), renderer podglądów (`render.py`, `preview.py`), dopasowanie celowania (`tune_ads.py`), szukanie dziur (`gaps.py`) i budowanie zipa (`build_pack.py`).

Przebudowa: pobierz oryginał `https://github.com/ZombieStriker/QualityArmory-Resourcepack/releases/download/latest/QualityArmory-21.zip`, rozpakuj go do `/tmp/qa/pack` i zapisz zip jako `/tmp/qa/QA21.zip` (albo podaj ścieżkę jako argument `build_pack.py`), potem w `zrodla/`: `python3 gen.py && python3 preview.py && python3 build_pack.py`. `gen.py makarov` generuje tylko wybraną broń. Opis paczki bierze się z `zrodla/pack.mcmeta`. Remington w `modele/` różni się od świeżo wygenerowanego tylko zapisem PNG i liczb, więc przy budowaniu można skopiować go z `modele/` do `zrodla/build/`. Skrypty mogą wymagać poprawienia ścieżek wyjściowych.
