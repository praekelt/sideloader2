from setuptools import setup, find_packages

setup(name='sideloader',
      version='2.0a0',
      description='Sideloader',
      classifiers=[
          "Programming Language :: Python",
      ],
      author='Praekelt Foundation',
      author_email='dev@praekeltfoundation.org',
      url='http://github.com/praekelt/sideloader2',
      license='BSD',
      keywords='deb,rpm,virtualenv',
      packages=find_packages(exclude=['docs']),
      include_package_data=True,
      zip_safe=False,
      install_requires=[
          'click',
          'PyYAML',
      ],
      entry_points={
          'console_scripts': ['sideloader = sideloader.cli:main'],
      })
