from setuptools import setup, Extension

ext_modules = [
    Extension(
        name="cython_functions_c",
        sources=["cython_functions.pyx"],
        language="c++",
    )
]


setup(
    name="cython",
    ext_modules=ext_modules
)
