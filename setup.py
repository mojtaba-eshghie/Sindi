from setuptools import setup, find_packages

setup(
    name='PreDi',  
    version='0.1.5',  
    author='Mojtaba Eshghie',
    author_email='eshghie@kth.se',
    description='PreDi: Semantic Solidity Predicate Difference Tool ',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/mojtaba-eshghie/PreDi',
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