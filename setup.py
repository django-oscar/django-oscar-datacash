#!/usr/bin/env python
from setuptools import setup, find_packages


setup(name='django-oscar-datacash',
      version='0.8.3',
      url='https://github.com/tangentlabs/django-oscar-datacash',
      author="David Winterbottom",
      author_email="david.winterbottom@tangentlabs.co.uk",
      description="Datacash payment module for django-oscar",
      long_description=open('README.rst').read(),
      keywords="Payment, Datacash",
      license='BSD',
      packages=find_packages(exclude=['sandbox*', 'tests*']),
      include_package_data=True,
      install_requires=[
          'django-oscar>=0.6',
          # Python 2 & 3 compatibility helper
          'six>=1.5.2',
      ],
      # See http://pypi.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[
          'Environment :: Web Environment',
          'Framework :: Django',
          'Intended Audience :: Developers',
          'License :: OSI Approved :: BSD License',
          'Operating System :: Unix',
          'Programming Language :: Python',
          'Programming Language :: Python :: 2',
          'Programming Language :: Python :: 2.7',
          'Programming Language :: Python :: 3',
          'Programming Language :: Python :: 3.3',
          'Programming Language :: Python :: 3.4',
      ]
    )
