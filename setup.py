from setuptools import setup, find_packages

# Load __version__ without importing it (avoids race condition with build)
exec(open('arrview/_version.py').read())

setup(name='arrview',
      description='An N-dimensional array viewer',
      author='jthacker',
      author_email='thacker.jon@gmail.com',
      version=__version__,
      url='https://github.com/jthacker/arrview',
      packages=find_packages(),
      install_requires=[
          'h5py',
          'matplotlib',
          'numpy',
          'PySide',
          'scipy', # required by skimage, but skimage doesn't install
          'traits',
          'traitsui',
          'scikit-image'
          ],
      tests_require=[
          'pytest'
          ],
      setup_requires=[
          'pytest-runner'
          ],
      )
