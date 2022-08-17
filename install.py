#!/usr/bin/env python

from genericpath import exists
import os
import re
import subprocess
import logging
import tempfile
import shutil
import sys
import fnmatch
import subprocess

rootLogger = logging.getLogger()
rootLogger.setLevel(logging.INFO)
consoleHandler = logging.StreamHandler(sys.stdout)
consoleHandler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
rootLogger.addHandler(consoleHandler)
SCRIPT_DIR = os.popen("find ~ -type d -name \"tmp_track_packages\"").read()
ARG = ""
try:
    ARG = sys.argv[1]
except IndexError:
    pass

class TopologicalSort(object):
    def __init__(self, dependency_map):
        self._dependency_map = dependency_map
        self._already_processed = set()

    def _get_dependencies(self, item, root=None):

        if not root:
            root = item

        elif root == item:
            logging.warn("circular dependency detected in '{}'".format(item))
            raise StopIteration()

        dependencies = self._dependency_map.get(item, [])
        for dependency in dependencies:

            if dependency in self._already_processed:
                continue

            self._already_processed.add(dependency)

            for sub_dependency in self._get_dependencies(dependency, root=root):
                yield sub_dependency

            yield dependency

    def sort(self):
        # Reduction, connect all nodes to a dummy node and re-calculate
        special_package_id = 'topological-sort-special-node'
        self._dependency_map[special_package_id] = self._dependency_map.keys()
        sorted_dependencies = self._get_dependencies(special_package_id)
        sorted_dependencies = list(sorted_dependencies)
        del self._dependency_map[special_package_id]

        # Remove "noise" dependencies (only referenced, not declared)
        sorted_dependencies = filter(lambda x: x in self._dependency_map, sorted_dependencies)
        return sorted_dependencies


class DebianPackage(object):
    def __init__(self, file_path):
        metadata = subprocess.check_output('dpkg -I {}'.format(file_path), shell=True)
        metadata = metadata.replace('\n ', '\n')
        self._metadata = metadata
        self.id = self._get('Package')
        self.dependencies = list(self._get_dependencies())
        self.file_path = file_path

    def _get_dependencies(self):
        dependencies = self._get('Depends') + ',' + self._get('Pre-Depends')
        dependencies = re.split(r',|\|', dependencies)
        dependencies = map(lambda x: re.sub(r'\(.*\)|:any', '', x).strip(), dependencies)
        dependencies = filter(lambda x: x, dependencies)
        dependencies = set(dependencies)
        for dependency in dependencies:
            yield dependency

    def _get(self, key):
        search = re.search(r'\n{key}:(.*)\n[A-Z]'.format(key=key), self._metadata)
        return search.group(1).strip() if search else ''

def sort_debian_packages(directory_path):
    file_names = os.listdir(directory_path)
    debian_packages = {}
    dependency_map = {}
    for file_name in file_names:

        file_path = os.path.join(directory_path, file_name)

        if not os.path.isfile(file_path):
            continue

        debian_package = DebianPackage(file_path)
        debian_packages[debian_package.id] = debian_package
        dependency_map[debian_package.id] = debian_package.dependencies

    sorted_dependencies = TopologicalSort(dependency_map).sort()
    sorted_dependencies = map(lambda package_id: debian_packages[package_id].file_path, sorted_dependencies)
    return sorted_dependencies

def find_packages(script_dir):
    pathname = [os.path.join(dirpath, f)
    for dirpath, dirnames, files in os.walk(script_dir)
    for f in fnmatch.filter(files, '*.deb')]

    return pathname[0]

def main():
    # ------------------
    # Sort the packages using topological sort
    tmp_folder = SCRIPT_DIR
    logging.info('Attempting to install: "{}" ...'.format(SCRIPT_DIR))
    dir_path = os.path.dirname(os.path.abspath(os.path.abspath(find_packages(tmp_folder))))
    logging.info('Sorting packages in "{}" using topological sort ...'.format(dir_path))
    sorted_packages = sort_debian_packages(dir_path)

    # ------------------
    # Install the packages in the sorted order

    for index, package_file_path in enumerate(sorted_packages):
        command = 'dpkg -i {}'.format(package_file_path)
        logging.info('executing "{}" ...'.format(command))
        subprocess.check_call(command, shell=True)

    shutil.rmtree(tmp_folder)
    if exists(tmp_folder) :
        logging.error("Unable to remove temp folder: {}".format(tmp_folder))
    else:
        logging.info('Successfully removed "{}" ...'.format(tmp_folder))
    logging.info('ACU successfully installed.')

if __name__ == '__main__':

    if os.geteuid() != 0:
        logging.error('must be run as root')
        sys.exit(1)
    try:
        main()
    except:
        logging.error('failed to install packages', exc_info=True)
        sys.exit(1)
