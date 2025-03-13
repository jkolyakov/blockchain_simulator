from setuptools import setup, find_packages

setup(
    name="blockchain-simulator",
    version="0.1.0",
    author="Your Name",
    author_email="your.email@example.com",
    description="A blockchain network simulator with GHOST consensus and analytics.",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/blockchain-simulator",
    packages=find_packages(),
    install_requires=[
        "simpy",
        "pandas",
        "matplotlib",
        "rich"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
)