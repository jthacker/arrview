from setuptools import setup

# Load __version__ without importing it (avoids race condition with build)
exec(open('arrview/version.py').read())

setup(name='arrview',
      description='An N-dimensional array viewer',
      author='jthacker',
      author_email='thacker.jon@gmail.com',
      version=__version__,
      url='https://github.com/jthacker/arrview',
      packages=['arrview', 'arrview.ui'],
      install_requires=[
          'numpy',
          'traits',
          'traitsui',
          'scipy',
          'scikit-image',
          'h5py',
          'matplotlib',
          'jtmri',
          'PySide'],
     tests_require=[
          'pytest'
          ],
      setup_requires=[
          'pytest-runner'
          ],
      )
