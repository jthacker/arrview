from distutils.core import setup

setup(
        name='arrview',
        version='0.1dev',
        packages=['arrview'],
        install_requires=[
            'numpy','traits','traitsui',
            'scikit-image','h5py',
            'matplotlib', 'PySide']
)
