from setuptools import find_packages, setup


def readme():
    with open("README.md") as f:
        return f.read()


setup(
    name="flachtex",
    version="0.3.15",
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
    packages=find_packages("src"),
    package_dir={"": "src"},
    install_requires=[],
    entry_points={
        "console_scripts": ["flachtex=flachtex.__main__:main"],
    },
    python_requires=">=3.8",
    include_package_data=True,
    zip_safe=False,
)
