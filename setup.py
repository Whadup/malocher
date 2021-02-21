from setuptools import setup

setup(name='malocher',
      version='0.0.1',
      description='Simple library to run jobs on multiple machines that share a NFS',
      long_description='Malocher is a lightweight python library for running jobs on a cluster where nodes are accessed via SSH and share a common network storage like traditional NFS or mountable cloud storage.',
      url='https://github.com/Whadup/malocher/',
      author=u'Lukas Pfahler',
      author_email='lukas.pfahler@tu-dortmund.de',
      license='MIT',
      install_requires=[
          "paramiko",
          "dill",
      ],
      packages=['malocher'],
      zip_safe=False
)
