
-include .env
export

PYTHONPATH := $(CURDIR)
export PYTHONPATH

download_collection:
	python -c "from data_adapter import main; main.download_collection('$(collection)')"

download_example_collection:
	python -c "from data_adapter import main; main.download_collection('https://databus.openenergyplatform.org/felixmaur/collections/hack-a-thon/')"
