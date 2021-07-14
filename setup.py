from setuptools import setup, find_packages
import os

# -- Python Dependencies -- #
dependencies = [
    'flopy==3.2.10',
    'sqlalchemy',
    'numpy',
    'tethysext-atcore',
    'fiona',
    'geopandas',
    'pyshp==1.2.12',
    'rasterio'
]

test_dependencies = [
    'mock',
    'coverage'
]


def find_files(directory):
    paths = []
    for (path, directories, filenames) in os.walk(directory):
        for filename in filenames:
            paths.append(os.path.join('..', path, filename))
    return paths


resource_files = find_files('modflow_adapter/resources')

setup(
    name='modflow_adapter',
    version='0.0.0',
    description='An adapter library for the Modflow models.',
    long_description='',
    keywords='Modflow',
    author='Corey Krewson',
    author_email='ckrewson@aquaveo.com',
    url='http://git.aquaveo.com',
    license='',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests.*', 'tests']),
    package_data={'': resource_files},
    include_package_data=True,
    zip_safe=False,
    install_requires=dependencies,
    tests_require=test_dependencies,
    test_suite='tests',
)
