from setuptools import setup, find_packages

setup(
    name="portwatch",
    version="1.0.0",
    description="Network port & service monitor with Telegram/Email alerts and uptime history",
    author="PortWatch Contributors",
    python_requires=">=3.10",
    packages=find_packages(exclude=["tests*"]),
    install_requires=[],
    extras_require={
        "yaml": ["pyyaml>=6.0"],
        "dev": ["pytest>=7.0", "pytest-cov"],
    },
    entry_points={"console_scripts": ["portwatch=portwatch.cli:main"]},
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)
