#!/bin/bash

# Create base dirs
mkdir -p endpoint-loader-agent/endpoint_agent/lib
mkdir -p deps/x86
mkdir -p deps/x86_64

# Install botocore
wget https://pypi.python.org/packages/source/b/botocore/botocore-1.4.5.tar.gz#md5=8ada0254ab3f080a0a7f5035c958403c
tar xvzf botocore-1.4.5.tar.gz
rm -f botocore-1.4.5.tar.gz
rm -rf endpoint-loader-agent/endpoint_agent/lib/botocore
mv botocore-1.4.5/botocore endpoint-loader-agent/endpoint_agent/lib/
rm -rf botocore-1.4.5

# Install boto3
wget https://pypi.python.org/packages/source/b/boto3/boto3-1.3.0.tar.gz#md5=b5a6cc7dc0e0c0969944f65db7f7b07f
tar xvzf boto3-1.3.0.tar.gz
rm -f boto3-1.3.0.tar.gz
rm -rf endpoint-loader-agent/endpoint_agent/lib/boto3
mv boto3-1.3.0/boto3 endpoint-loader-agent/endpoint_agent/lib/
rm -rf boto3-1.3.0

# Install dateutil
wget https://pypi.python.org/packages/source/p/python-dateutil/python-dateutil-2.5.1.tar.gz#md5=2769f13c596427558136b34977a95269
tar xvzf python-dateutil-2.5.1.tar.gz
rm -f python-dateutil-2.5.1.tar.gz
rm -rf endpoint-loader-agent/endpoint_agent/lib/dateutil
mv python-dateutil-2.5.1/dateutil endpoint-loader-agent/endpoint_agent/lib
rm -rf python-dateutil-2.5.1

# Install jmespath
wget https://pypi.python.org/packages/source/j/jmespath/jmespath-0.9.0.tar.gz#md5=471b7d19bd153ac11a21d4fb7466800c
tar xvzf jmespath-0.9.0.tar.gz
rm -f jmespath-0.9.0.tar.gz
rm -rf endpoint-loader-agent/endpoint_agent/lib/jmespath
mv jmespath-0.9.0/jmespath endpoint-loader-agent/endpoint_agent/lib
rm -rf jmespath-0.9.0

# Install request
wget https://pypi.python.org/packages/source/r/requests/requests-2.9.1.tar.gz#md5=0b7f480d19012ec52bab78292efd976d
tar xvzf requests-2.9.1.tar.gz
rm -f requests-2.9.1.tar.gz
rm -rf endpoint-loader-agent/endpoint_agent/lib/requests
mv requests-2.9.1/requests endpoint-loader-agent/endpoint_agent/lib/
rm -rf requests-2.9.1

# Install kafka
wget https://github.com/dpkp/kafka-python/archive/v0.9.4.tar.gz
tar xvzf v0.9.4.tar.gz
rm -f v0.9.4.tar.gz
rm -rf endpoint-loader-agent/endpoint_agent/lib/kafka
mv kafka-python-0.9.4/kafka endpoint-loader-agent/endpoint_agent/lib/
rm -rf kafka-python-0.9.4

# Install yaml
wget https://pypi.python.org/packages/source/P/PyYAML/PyYAML-3.11.tar.gz#md5=f50e08ef0fe55178479d3a618efe21db
tar xvzf PyYAML-3.11.tar.gz
rm -f PyYAML-3.11.tar.gz
rm -rf endpoint-loader-agent/endpoint_agent/lib/yaml
mv PyYAML-3.11/lib3/yaml endpoint-loader-agent/endpoint_agent/lib/
rm -rf PyYAML-3.11

# Install wmi
wget https://pypi.python.org/packages/source/W/WMI/WMI-1.4.9.zip#md5=e883e155ed5a63b742686816ec762053
unzip WMI-1.4.9.zip
rm -f WMI-1.4.9.zip
rm -rf endpoint-loader-agent/endpoint_agent/lib/wmi.py
mv WMI-1.4.9/wmi.py endpoint-loader-agent/endpoint_agent/lib/
rm -rf WMI-1.4.9

# Install six
wget https://pypi.python.org/packages/source/s/six/six-1.10.0.tar.gz#md5=34eed507548117b2ab523ab14b2f8b55
tar xvzf six-1.10.0.tar.gz
rm -f six-1.10.0.tar.gz
rm -rf endpoint-loader-agent/endpoint_agent/lib/six.py
mv six-1.10.0/six.py endpoint-loader-agent/endpoint_agent/lib/
rm -rf six-1.10.0

# Get psutil
wget https://pypi.python.org/packages/3.4/p/psutil/psutil-4.0.0-cp34-cp34m-win32.whl -O deps/x86/psutil-4.0.0-cp34-cp34m-win32.whl
wget https://pypi.python.org/packages/3.4/p/psutil/psutil-4.0.0-cp34-cp34m-win_amd64.whl -O deps/x86_64/psutil-4.0.0-cp34-cp34m-win_amd64.whl

# Get pysha3
wget https://pypi.python.org/packages/3.4/p/pysha3/pysha3-0.3-cp34-none-win32.whl -O deps/x86/pysha3-0.3-cp34-none-win32.whl
wget https://pypi.python.org/packages/3.4/p/pysha3/pysha3-0.3-cp34-none-win_amd64.whl -O deps/x86_64/pysha3-0.3-cp34-none-win_amd64.whl

# Get pip
wget https://pypi.python.org/packages/py2.py3/p/pip/pip-8.1.0-py2.py3-none-any.whl -O deps/pip-8.1.0-py2.py3-none-any.whl

# Get pywin32
# wget --user-agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:21.0) Gecko/20100101 Firefox/21.0' http://www.lfd.uci.edu/~gohlke/pythonlibs/djcobkfp/pywin32-220-cp34-none-win32.whl -O deps/x86/pywin32-220-cp34-none-win32.whl
# wget --user-agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:21.0) Gecko/20100101 Firefox/21.0' http://www.lfd.uci.edu/~gohlke/pythonlibs/djcobkfp/pywin32-220-cp34-none-win_amd64.whl -O deps/x86_64/pywin32-220-cp34-none-win_amd64.whl
