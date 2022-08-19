import setuptools


with open("README.md", "r") as f:
    long_description = f.read()

setuptools.setup(
    name="quickbeserverless",
    version="0.2.1",
    author="Eldad Bishari",
    author_email="eldad@1221tlv.org",
    description="Run your function on serverless platform",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/eldad1221/quickbeserverless",
    packages=setuptools.find_packages(),
    install_requires=[
        'cerberus==1.3.4',
        'quickbelog==1.1.0',
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.8',
)
