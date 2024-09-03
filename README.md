# Quellcode des Servers
Der Quellcode des Servers ist in der Datei "consumers.py" im Ordner "pruefstand" abgelegt.
In dieser Datei befinden sich die Klassen zur Steuerung des 32-Kanal-Relaisblocks (ModBusRelay) und zur Kommunikation und Verarbeitung der Client-Schnittstelle (TestConsumer).


## Algmemeines
Der RaspberryPi ist über eine SSH-Verbindung mit folgendem Schlüssel erreichbar:
### Schlüssel

Die Autostartkonfiguration ist in folgender Datei abgespeichert:
  ~/.config/wayfire.ini
In dieser ist ein Skript hinterlegt, welches den Chromium-Browser im Kioskmodus (Vollbildansicht) öffnet und "haha.service" aufruft. Darin enthalten ist der Start des Django-Servers.
