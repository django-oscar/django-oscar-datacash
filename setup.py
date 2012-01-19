#!/usr/bin/env python
from setuptools import setup, find_packages

setup(name='django-oscar-datacash',
      version='0.1.1',
      url='https://github.com/tangentlabs/django-oscar-datacash',
      author="David Winterbottom",
      author_email="david.winterbottom@tangentlabs.co.uk",
      description="Datacash payment module for django-oscar",
      long_description=open('README.rst').read(),
      keywords="Payment, Datacash",
      license='BSD',
      platforms=['linux'],
      packages=find_packages(),
      install_requires=[ 'django-oscar',],
      # See http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=['Environment :: Web Environment',
                   'Framework :: Django',
                   'Intended Audience :: Developers',
                   'License :: OSI Approved :: BSD License',
                   'Operating System :: Unix',
                   'Programming Language :: Python']
      )
