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

Paczka zawiera też shader `assets/minecraft/shaders/core/rendertype_text.{vsh,fsh}` z pluginu [AxonMap](https://github.com/toMiXgaming/AXONMAP). Rysuje on mapę świata na cały ekran po wpisaniu `/mapa`. Shader rozpoznaje tylko mapy pluginu (po znaczniku w pierwszym wierszu), więc zwykłe napisy, tabliczki i mapy działają jak wcześniej. Do tego czcionka `assets/axonmap/font/panel.json`, z której plugin robi panel zasłaniający hotbar przy otwartej mapie. Źródła są w `zrodla/shadery/` i `zrodla/axonmap/`, a `build_pack.py` dodaje je do zipa.

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
- `zrodla/` – generator (`gen.py`), renderer podglądów (`render.py`, `preview.py`), dopasowanie celowania (`tune_ads.py`), szukanie dziur (`gaps.py`) i budowanie zipa (`build_pack.py`).

Przebudowa: pobierz oryginał `https://github.com/ZombieStriker/QualityArmory-Resourcepack/releases/download/latest/QualityArmory-21.zip`, rozpakuj go do `/tmp/qa/pack` i zapisz zip jako `/tmp/qa/QA21.zip` (albo podaj ścieżkę jako argument `build_pack.py`), potem w `zrodla/`: `python3 gen.py && python3 preview.py && python3 build_pack.py`. `gen.py makarov` generuje tylko wybraną broń. Opis paczki bierze się z `zrodla/pack.mcmeta`. Remington w `modele/` różni się od świeżo wygenerowanego tylko zapisem PNG i liczb, więc przy budowaniu można skopiować go z `modele/` do `zrodla/build/`. Skrypty mogą wymagać poprawienia ścieżek wyjściowych.
