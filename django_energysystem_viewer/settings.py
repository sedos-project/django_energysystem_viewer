import os
import pathlib

from django.conf import settings

VERSION = "0.1.0"

STRUCTURE_FILE = os.environ.get("STRUCTURE_FILE", pathlib.Path(settings.MEDIA_ROOT) / "SEDOS_Modellstruktur.xlsx")
