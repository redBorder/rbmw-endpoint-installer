#!/bin/bash

# Create base dirs
mkdir -p endpoint-loader-agent/endpoint_agent/lib
mkdir -p deps/x86
mkdir -p deps/x86_64

# Install boto
wget https://pypi.python.org/packages/source/b/boto/boto-2.39.0.tar.gz#md5=503e6ffd7d56dcdffa38cb316bb119e9
tar xvzf boto-2.39.0.tar.gz
rm -f boto-2.39.0.tar.gz
rm -rf endpoint-loader-agent/endpoint_agent/lib/boto
mv boto-2.39.0/boto endpoint-loader-agent/endpoint_agent/lib/
rm -rf boto-2.39.0

# # Install request
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
wget https://pypi.python.org/packages/3.4/p/psutil/psutil-4.0.0.win-amd64-py3.4.exe#md5=baa1f3e1bd4fc5b0dd4823fe7c7cbf1c -O deps/x86_64/psutil-4.0.0.win-amd64-py3.4.exe
wget https://pypi.python.org/packages/3.4/p/psutil/psutil-4.0.0.win32-py3.4.exe#md5=baa1f3e1bd4fc5b0dd4823fe7c7cbf1c -O deps/x86/psutil-4.0.0.win32-py3.4.exe

# Get pysha3
wget https://pypi.python.org/packages/3.4/p/pysha3/pysha3-0.3.win-amd64-py3.4.exe#md5=f76ec330bd918d9fc693cf5acb3fc4ca -O deps/x86_64/pysha3-0.3.win-amd64-py3.4.exe
wget https://pypi.python.org/packages/3.4/p/pysha3/pysha3-0.3.win32-py3.4.exe#md5=f76ec330bd918d9fc693cf5acb3fc4ca -O deps/x86/pysha3-0.3.win32-py3.4.exe

# Get pywin32
wget --user-agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:21.0) Gecko/20100101 Firefox/21.0' http://www.lfd.uci.edu/~gohlke/pythonlibs/tugyrhqo/pywin32-220-cp34-none-win32.whl -O deps/x86/pywin32.whl
wget --user-agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:21.0) Gecko/20100101 Firefox/21.0' http://www.lfd.uci.edu/~gohlke/pythonlibs/tugyrhqo/pywin32-220-cp34-none-win_amd64.whl -O deps/x86_64/pywin32.whl
