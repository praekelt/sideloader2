from setuptools import setup, find_packages


setup(
    name="hive",
    version='0.0.1',
    url='http://github.com/praekelt/sideloader2',
    license='MIT',
    description="An asynchronous job queue for Sideloader",
    author='Colin Alston',
    author_email='colin.alston@gmail.com',
    packages=find_packages() + [
        "twisted.plugins",
    ],
    package_data={
        'twisted.plugins': ['twisted/plugins/hive_plugin.py']
    },
    include_package_data=True,
    install_requires=[
        'Twisted',
        'txredis',
        'PyYaml'
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: MIT License',
        'Operating System :: POSIX',
        'Programming Language :: Python',
        'Topic :: System :: Deployment',
    ],
)
