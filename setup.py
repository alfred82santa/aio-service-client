import ast

from setuptools import setup
import os

path = os.path.join(os.path.dirname(__file__), 'service_client', '__init__.py')

with open(path, 'r') as file:
    t = compile(file.read(), path, 'exec', ast.PyCF_ONLY_AST)
    for node in (n for n in t.body if isinstance(n, ast.Assign)):
        if len(node.targets) != 1:
            continue

        name = node.targets[0]
        if not isinstance(name, ast.Name) or \
                name.id not in ('__version__', '__version_info__', 'VERSION'):
            continue

        v = node.value
        if isinstance(v, ast.Str):
            version = v.s
            break
        if isinstance(v, ast.Tuple):
            r = []
            for e in v.elts:
                if isinstance(e, ast.Str):
                    r.append(e.s)
                elif isinstance(e, ast.Num):
                    r.append(str(e.n))
            version = '.'.join(r)
            break

setup(
    name='aio-service-client',
    url='https://github.com/alfred82santa/aio-service-client',
    author='alfred82santa',
    version=version,
    license='LGPLv3',
    author_email='alfred82santa@gmail.com',
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Development Status :: 4 - Beta'],
    packages=['service_client'],
    include_package_data=False,
    install_requires=['dirty-loader>=0.2.2', 'aiohttp>=2.0.0'],
    description="Service Client Framework powered by Python asyncio.",
    long_description=open(os.path.join(os.path.dirname(__file__), 'README.rst')).read(),
    test_suite="nose.collector",
    tests_require="nose",
    zip_safe=True,
)
