from setuptools import setup, Extension

ext_modules = [
    Extension(
        name="charges_service_c",
        sources=["charges_service.pyx"],
        language="c++",
    ),
    Extension(
        name="arbitrage_service_c",
        sources=["arbitrage_service.pyx"],
        language="c++",
    ),
    Extension(
        name="aggregate_service_c",
        sources=["aggregate_service.pyx"],
        language="c++",
    )
]


setup(
    name="equalizer",
    ext_modules=ext_modules
)
