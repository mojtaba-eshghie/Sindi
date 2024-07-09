from setuptools import setup, find_packages

setup(
    name='spi_solidity_predicate_inspector',  # Changed to match PyPI naming conventions
    version='0.1.1',  # Incremented version for re-upload
    author='Mojtaba Eshghie',
    author_email='eshghie@kth.se',
    description='SPi (Solidity Predicate Inspector): Solidity Semantic Predicate Comparison Tool',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/mojtaba-eshghie/spi',
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'sympy>=1.13.0rc2',
        'colorama>=0.4.6',
        'pyyaml>=6.0.1'
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
)