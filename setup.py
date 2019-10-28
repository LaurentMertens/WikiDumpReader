from setuptools import setup

setup(
    python_requires='>=3.6',
    name='wikipedia_reader',
    version='1.0',
    packages=['wikipedia_reader'],
    url='',
    license='MIT',
    author='Laurent Mertens',
    author_email='laurent.mertens@outlook.com',
    description='A generator for reading a Wikipedia dump stream',
    # sklearn depends on scipy, so no need to mention scipy explicitely
    install_requires=[]
)
