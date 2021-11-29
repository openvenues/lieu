from setuptools import setup, find_packages


def main():
    setup(
        name='lieu',
        version='1.1.1',
        install_requires=[
            'six',
            'postal>=1.1.6',
            'rocksdb',
            'python-geohash',
            'phonenumbers',
            'mrjob',
        ],
        package_dir={'': 'lib'},
        packages=find_packages('lib'),
        scripts=['scripts/dedupe_geojson'],
        zip_safe=False,
        url='https://github.com/openvenues/lieu',
        description='Dedupe addresses and venues around the world with libpostal',
        license='MIT License',
        maintainer='mapzen.com',
        maintainer_email='pelias@mapzen.com',
        classifiers=[
            'Intended Audience :: Developers',
            'Intended Audience :: Information Technology',
            'License :: OSI Approved :: MIT License',
            'Programming Language :: Python :: 2',
            'Programming Language :: Python :: 2.7',
            'Programming Language :: Python :: 3',
            'Programming Language :: Python :: 3.4',
            'Programming Language :: Python :: 3.5',
            'Operating System :: MacOS :: MacOS X',
            'Operating System :: POSIX :: Linux',
            'Topic :: Text Processing :: Linguistic',
            'Topic :: Scientific/Engineering :: GIS',
            'Topic :: Software Development :: Libraries :: Python Modules'
        ],
    )


if __name__ == '__main__':
    main()
