from setuptools import setup
from setuptools import find_packages

setup(name='boobank_indicator',
      version='2.0',
      description='show your bank accounts in your System Tray',
      long_description='boobank_indicator will show you bank accounts and associated transactions in your system tray. Your bank accounts should be configured in boobank',
      keywords='weboob boobank tray icon',
      url='http://weboob.org/',
      license='GNU LGPL 3',
      author='Bezleputh',
      author_email='bezleputh@gmail.com',
      packages=find_packages(),
      package_data={
          'boobank_indicator.data': ['indicator-boobank.png', 'green_light.png', 'red_light.png', 'personal-loan.png']
      },
      entry_points={
          'console_scripts': ['boobank_indicator = boobank_indicator.boobank_indicator:main'],
      },
      zip_safe=False)
