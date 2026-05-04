from setuptools import find_packages, setup

package_name = 'adxl355_viz'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
         ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch',
         ['launch/adxl355_viz_launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='User',
    maintainer_email='user@example.com',
    description='ADXL355 real-time acceleration visualization',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'viz_node = adxl355_viz.viz_node:main',
        ],
    },
)
