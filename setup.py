from setuptools import setup


def readme():
    with open("README.md") as f:
        return f.read()


setup(
    name="flachtex",
    version="0.3.4",
    description="A traceable LaTeX flattener.",
    long_description=readme(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 4 - Beta",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
    ],
    keywords="LaTeX flatten",
    url="https://github.com/d-krupke/flachtex",
    author="Dominik Krupke",
    author_email="krupke@ibr.cs.tu-bs.de",
    license="MIT",
    packages=["flachtex", "flachtex.rules"],
    install_requires=[],
    entry_points={
        "console_scripts": ["flachtex=flachtex.__main__:main"],
    },
    python_requires=">=3.7",
    include_package_data=True,
    zip_safe=False,
)
