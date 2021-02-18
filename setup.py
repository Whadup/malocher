from setuptools import setup

setup(name='malocher',
      version='0.0.1',
      description='Simple library to run jobs on multiple machines that share a NFS',
      url='https://github.com/Whadup/malocher/',
      author=u'Lukas Pfahler',
      author_email='lukas.pfahler@tu-dortmund.de',
      license='MIT',
      install_requires=[
          "paramiko",
          "cloudpickle",
          "tornado"
      ],
      packages=['malocher'],
      zip_safe=False
)
