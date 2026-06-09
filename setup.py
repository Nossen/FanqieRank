from setuptools import find_packages, setup

setup(
    name="fanqierank",
    version="0.1.0",
    description="Fanqie male new-book rank tracker with fallback reports and Codex analysis finalization.",
    packages=find_packages(include=["fanqierank", "fanqierank.*"]),
    python_requires=">=3.9",
    install_requires=["playwright>=1.45"],
    extras_require={"dev": ["pytest>=8.0"]},
)
