#!/usr/bin/python

import os
import subprocess
from os import path
from zipfile import ZIP_DEFLATED, ZIP_STORED, ZipFile

from pynt import main, task

AUTHOR = "lgfrbcsgo"
NAME = "Battle Results Server"
DESCRIPTION = "WoT mod which starts a WebSocket server on `ws://localhost:15455` for serving battle results."

SOURCES = [
    "gui",
    "mod_battle_results_server",
]

RELEASE_DEPENDENCIES = [
    "https://github.com/lgfrbcsgo/wot-async/releases/download/v0.1.3/lgfrbcsgo.async_0.1.3.wotmod",
    "https://github.com/lgfrbcsgo/wot-async-server/releases/download/v0.2.3/lgfrbcsgo.async-server_0.2.3.wotmod",
    "https://github.com/lgfrbcsgo/wot-websocket-server/releases/download/v0.3.2/lgfrbcsgo.websocket-server_0.3.2.wotmod",
    "https://github.com/lgfrbcsgo/wot-hooking/releases/download/v0.1.0/lgfrbcsgo.hooking_0.1.0.wotmod",
]


@task()
def clean():
    subprocess.check_call(["rm", "-rf", "dist"])


@task()
def wotmod():
    # clean dist directory
    subprocess.check_call(["rm", "-rf", "dist/wotmod"])

    source_dst = "dist/wotmod/unpacked/res/scripts/client"

    # make source directory
    subprocess.check_call(["mkdir", "-p", source_dst])

    # copy sources
    for source in SOURCES:
        subprocess.check_call(["cp", "-r", source, source_dst])

    # compile sources
    subprocess.check_call(["python2.7", "-m", "compileall", source_dst])

    unpacked_dst = "dist/wotmod/unpacked"

    # copy license and readme
    subprocess.check_call(["cp", "-r", "LICENSE", unpacked_dst])
    subprocess.check_call(["cp", "-r", "README.md", unpacked_dst])

    # create meta.xml content
    metadata = """
<root>
    <id>{id}</id>
    <version>{version}</version>
    <name>{name}</name>
    <description>{description}</description>
</root>
    """.format(
        id=get_id(), version=get_version(), name=NAME, description=DESCRIPTION
    )

    # write meta.xml
    with open("dist/wotmod/unpacked/meta.xml", "w") as meta_file:
        meta_file.write(metadata.strip())

    # create wotmod file
    wotmod_dst = path.join("dist/wotmod", get_wotmod_name())
    with ZipFile(wotmod_dst, "w", ZIP_STORED) as wotmod_file:
        for file_path in get_files(unpacked_dst):
            zipped_path = path.relpath(file_path, unpacked_dst)
            with open(file_path, "rb") as unzipped_file:
                wotmod_file.writestr(zipped_path, unzipped_file.read())


@task(wotmod)
def release():
    # clean dist directory
    subprocess.check_call(["rm", "-rf", "dist/release"])

    # make release directory
    unpacked_dst = "dist/release/unpacked"
    subprocess.check_call(["mkdir", "-p", unpacked_dst])

    # copy wotmod
    wotmod_dst = path.join("dist/wotmod", get_wotmod_name())
    subprocess.check_call(["cp", wotmod_dst, unpacked_dst])

    # fetch dependencies
    for dependency in RELEASE_DEPENDENCIES:
        subprocess.check_call(["wget", "-nv", "-P", unpacked_dst, dependency])

    # create release archive
    release_dst = path.join("dist/release", get_release_name())
    with ZipFile(release_dst, "w", ZIP_DEFLATED) as release_file:
        for file_path in get_files(unpacked_dst):
            zipped_path = path.relpath(file_path, unpacked_dst)
            with open(file_path, "rb") as unzipped_file:
                release_file.writestr(zipped_path, unzipped_file.read())


@task(release)
def github_actions_release():
    print("::set-output name=version::{}".format(get_version()))

    wotmod_path = path.join("dist/wotmod", get_wotmod_name())
    print("::set-output name=wotmod_path::{}".format(wotmod_path))
    print("::set-output name=wotmod_name::{}".format(get_wotmod_name()))

    release_path = path.join("dist/release", get_release_name())
    print("::set-output name=release_path::{}".format(release_path))
    print("::set-output name=release_name::{}".format(get_release_name()))


@task(wotmod)
def install(dst):
    wotmod_dst = path.join("dist/wotmod", get_wotmod_name())
    subprocess.check_call(["cp", wotmod_dst, dst])


def get_id():
    return "{author}.{name}".format(author=AUTHOR, name=NAME.lower().replace(" ", "-"))


def get_version():
    tag = subprocess.check_output(["git", "describe", "--tags"]).strip()
    return tag.lstrip("v")


def get_wotmod_name():
    return "{id}_{version}.wotmod".format(id=get_id(), version=get_version())


def get_release_name():
    return "{name}-{version}.zip".format(
        name=NAME.lower().replace(" ", "-"), version=get_version()
    )


def get_files(directory):
    for root, _, files in os.walk(directory):
        for file_name in files:
            yield path.join(root, file_name)


if __name__ == "__main__":
    main()
