from setuptools import setup, find_packages
from pathlib import Path

this_dir = Path(__file__).parent
long_desc = (this_dir / "README-PYPI.md").read_text(encoding="utf-8")

setup(
    name='sindi',
    version='0.2.0',
    author='Mojtaba Eshghie',
    author_email='eshghie@kth.se',
    description='SInDi: Semantic Invariant Differencing for Solidity Smart Contracts',
    long_description=long_desc,
    long_description_content_type='text/markdown',
    url='https://github.com/mojtaba-eshghie/Sindi',
    project_urls={
        "Source": "https://github.com/mojtaba-eshghie/Sindi",
        "Author Website": "https://eshghie.com/",
        "Issues": "https://github.com/mojtaba-eshghie/Sindi/issues",
    },
    packages=find_packages(where='src'),
    package_dir={'': 'src'},
    install_requires=[
        'sympy>=1.13',
        'colorama>=0.4.6',
        'pyyaml>=6.0.1',
        'z3-solver>=4.12.4.0'
    ],
    entry_points={
        'console_scripts': [
            'sindi=sindi.cli:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.8',
    include_package_data=True,
    license='MIT',
)