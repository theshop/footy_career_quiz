from setuptools import setup, find_packages
import os

# Read requirements from requirements.txt
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

# Read long description from README.md
with open('README.md', 'r', encoding='utf-8') as f:
    long_description = f.read()

setup(
    name="footy_career_quiz",
    version="0.1.0",
    description="A quiz game that challenges players to identify footballers from their career history",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="The Shop",
    author_email="info@theshop.example.com",
    url="https://github.com/theshop/footy_career_quiz",
    packages=find_packages(exclude=["tests", "tests.*"]),
    include_package_data=True,
    package_data={
        "": ["frontend/templates/*.html", "frontend/static/css/*.css", "frontend/static/js/*.js"]
    },
    install_requires=requirements,
    python_requires=">=3.10",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Environment :: Web Environment",
        "Framework :: Flask",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Topic :: Games/Entertainment :: Puzzle Games",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    entry_points={
        "console_scripts": [
            "footy-quiz=app:main",
        ],
    },
    # Add a main function to app.py to support the entry point
    extras_require={
        "dev": [
            "pytest",
            "pytest-cov",
            "black",
            "flake8",
        ],
    },
    keywords="football, soccer, quiz, game, wikipedia",
)
