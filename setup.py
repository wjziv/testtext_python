import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="touchstone",
    version="0.1",
    author="Walter Zielenski",
    author_email="walterzielenski@gmail.com",
    description="An Unofficial Touchstone Email Testing Library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3.6",
        "Operating System :: Linux",
    ],
    include_package_data=True,
    python_requires='>=3.6.9',
    install_requires=[
        'requests>=2.21.0',
        'beautifulsoup4>=4.6.3'
    ],
)
