from setuptools import setup, find_packages

import utils.version
import re
import os

m = re.search(r'(\d+\.\d+\.\d+(-.+)?)', utils.version.VERSION)
version = m.group(1) if m is not None else '0.0.0'

def read(filename):
    return open(os.path.join(os.path.dirname(__file__), filename)).read()

setup(name='mulpy',
      version=version,
      description='A Multi-Paradigm High-Level Hardware Design Framework',
      long_description=read('README.rst'),
      keywords = 'FPGA, Verilog HDL',
      author='Shinya Takamaeda-Yamazaki',
      author_email='shinya.takamaeda_at_gmail_com',
      license="Apache License 2.0",
      url='https://github.com/PyHDI/mulpy',
      packages=find_packages(),
      #package_data={ 'path' : ['*.*'], },
      install_requires=[ 'pyverilog>=1.0.6', 'Jinja2>=2.8' ],
      extras_require={
          'graph' : [ 'pygraphviz>=1.3.1' ],
          'test' : [ 'pytest>=2.8.2', 'pytest-pythonpath>=0.7' ],
      },
)
