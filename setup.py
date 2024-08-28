from setuptools import setup, find_packages

setup(
    name="Metagenomics",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "pandas",
        "plotly",
    ],
    entry_points={
        "console_scripts": [
            "run_pipeline=Metagenomics_pipeline.scripts.run_kr_abundance:main",
        ],
    },
    author="Harouna",
    author_email="harounasoum17@gmail.com",
    description="A bioinformatics pipeline for trimming, host depletion, and taxonomic classification",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/Harounas/Metagenomics_pipeline.git",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
)