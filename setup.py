from setuptools import setup

setup(
    name = 'django-candidates',
    version = '0.1',
    packages = ['candidates'],
    author = 'Antti Kaihola',
    author_email = 'akaihol+django@ambitone.com',
    description = ('Application form handling re-usable app for Django'),
    url = 'http://github.com/akaihola/django-candidates/tree/master',
    download_url = ('http://www.github.com/akaihola/django-candidates/'
                    'tarball/0.1'),
    classifiers=(
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development'),
    )
