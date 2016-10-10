# redBorder's Malware Endpoint Installer

This the installer for the redBorder's Malware endpoint client and uses the
NSIS (Nullsoft Scriptable Install System) to build the package.

The installer performs the following operations:

- Install python core
- Run and install GRR client
- Install required libraries
- Install loader agent

The installation will be executed on silent mode, so the system user won't
notice the installation process.

The installer will install the following files that **should be in the
same directory** as the executable:

- `parameters.yaml`
- `hosts`
- `s3.redborder.cluster.crt`
- `GRR_3.0.0.7_i386.exe` or `GRR_3.0.0.7_amd64.exe`
