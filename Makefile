VERSION = $(shell git describe --tags | sed "s/^v//")
WOTMOD_NAME = lgfrbcsgo.battle-results-server_$(VERSION).wotmod
RELEASE_NAME = battle-results-server-$(VERSION).zip

clean-build:
	rm -rf build
	mkdir -p build

clean-dist:
	rm -rf dist
	mkdir -p dist/unpacked

copy-python-source: clean-build
	cp -r gui build
	cp -r mod_battle_results_server build

compile: copy-python-source
	python2.7 -m compileall build

copy-wotmod-content: compile clean-dist
	cp LICENSE dist/unpacked
	cp README.md dist/unpacked

	mkdir -p dist/unpacked/res/scripts/client
	cp -r build/* dist/unpacked/res/scripts/client

wotmod: copy-wotmod-content
	python ./scripts/template_meta_xml.py $(VERSION) > dist/unpacked/meta.xml
	cd dist/unpacked; 7z a -mx=0 -tzip ../$(WOTMOD_NAME) .

release: wotmod
	mkdir -p dist/release
	cp dist/$(WOTMOD_NAME) dist/release
	cd dist/release; cat ../../dependencies | while read -r line; do wget $$line; done
	cd dist/release; 7z a -mx=0 -tzip ../$(RELEASE_NAME) .

gh-actions-release: release
	echo "::set-output name=version::$(VERSION)"
	echo "::set-output name=wotmod_name::$(WOTMOD_NAME)"
	echo "::set-output name=release_name::$(RELEASE_NAME)"
