import os
from setuptools import setup

here = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(here, 'README.rst')) as f:
    README = f.read()

setup(
    name='score.svg',
    version='0.1.1',
    description='Helpers for managing svg icons with The SCORE Framework',
    long_description=README,
    author='strg.at',
    author_email='score@strg.at',
    url='http://score-framework.org',
    keywords='score framework web svg icons',
    packages=['score.svg'],
    include_package_data=True,
    zip_safe=False,
    install_requires=[
        'score.webassets >= 0.1',
        'Pillow',
        'CairoSVG',
    ],
)
