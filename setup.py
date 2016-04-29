from setuptools import setup
import os

setup(
    name='aio-service-client',
    url='https://github.com/alfred82santa/aio-service-client',
    author='alfred82santa',
    version='0.1.2',
    author_email='alfred82santa@gmail.com',
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'License :: OSI Approved :: BSD License',
        'Development Status :: 4 - Beta'],
    packages=['service_client'],
    include_package_data=True,
    install_requires=['dirty-loader', 'aiohttp'],
    description="Service Client Framework powered by Python asyncio.",
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
    test_suite="nose.collector",
    tests_require="nose",
    zip_safe=True,
)
