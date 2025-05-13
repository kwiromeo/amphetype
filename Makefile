clean:
	rm -rf dist build

build-mac: clean
	pyinstaller --clean amphetype-mac.spec
