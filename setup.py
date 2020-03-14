'''Package description for Mariusz. Allows us to `pip install` the bot.'''

from setuptools import setup, find_packages

setup(name='mariusz',
      version='0.1',
      description='Hakierspejs Lodz multi-purpose telegram bot.',
      url='https://github.com/hakierspejs/mariusz',
      author='hakierspejs',
      author_email='lodz@lists.hackerspace.pl',
      packages=find_packages(),
      entry_points={
        'console_scripts': ['mariusz-bot=mariusz.main:main'],
      },
      zip_safe=False)
