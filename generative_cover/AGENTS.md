# Programmierstyle

Nutze bitte starke Type annotation. 

Ich verwende `uv` als virtuelle Python Umgebung. Abhängigkeiten bitte in `pyproject.toml`eintragen. 

Benutze bitte als Shebang "#!/usr/bin/env uv run" in den Files.

Verwende keine "from __future__ import annotations" mehr

Dateikopf: Direkt nach dem Shebang eine kurze Modul-Docstring-Zeile im Stil von `py_helper/pic_scripts_config.py` ("""..."""), keine Kommentarzeile als Beschreibung.

# Projekt
In dem Projekt sollen python Skripte erstellt werden mit denen generative Bilder erstellt werden. Dabei soll mittels Zufallszahlen jeweils ein zufälliges Bild erstellt werden. 

# Projektstruktur

`py_scripts` In diesem Ordner liegen alle Skripte zur generierung der Bilder. 

`py_helper` Hier werden alle Hilfsskripte abgelegt die in den Skripten aufgerufen werden können. Oder allgemeine Skripte die nicht direkt mit der Erstellung der Bilder zusammenhängen.

`output` Die fertigen Bilder sollen hier abgelegt werden

`config.toml`In diesem Konfigurationsfile liegt die Konfiguration ab. Also welches skript ausgeführt werden soll. Welche Farben verwendet werden sollen und der seed für die Zufallszahlengenerierung. 

`main.py` Der Hauptfile mit Aufruf von diesem werden die Bilder generiert

`variables.py`Variablen die ich in mehreren Skripten benötige liegen in diesem Skript ab und können importiert werden. 

# pic_scripts
Die Skripte zum erstellen der Bilder sollen so aufgebaut sein, dass sie die Konfiguration aus der config.toml laden und immer ein svg File erzeugen. Die Skripte sollen auch eigenständig lauffähig sein.
