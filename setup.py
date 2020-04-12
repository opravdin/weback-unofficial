import setuptools
import os

WEBACK_PASSWORD = os.environ.get("WEBACK_PASSWORD")
WEBACK_USERNAME = os.environ.get("WEBACK_USERNAME")

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="weback-unofficial", # Replace with your own username
    version="0.3.3",
    author="Pravdin Oleg",
    author_email="opravdin@gmail.com",
    description="Unofficial client for WeBack API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/opravdin/weback-unofficial",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)