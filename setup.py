from setuptools import setup
import stacksync_quota

setup(name='stacksync_quota_swift',
      version=stacksync_quota.__version__,
      description='StackSync Quota module for OpenStack Swift',
      author='The StackSync Team',
      url='http://stacksync.org',
      packages=['stacksync_quota'],
      requires=['swift(>=1.4)'],
      install_requires=['stacksync_quota>=2.0'],
      entry_points={'paste.filter_factory':
                        ['stacksync_quota=stacksync_quota.stacksync_quota:filter_factory']})