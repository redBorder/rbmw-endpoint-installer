# redBorder's Malware Endpoint Installer

This the installer for the redBorder's Malware endpoint client and uses the
NSIS (Nullsoft Scriptable Install System) to build the package.

The installer performs the following operations:

- Install python core
- Install required libraries
- Run and install GRR client
- Install loader agent and run it as a Windows scheduled task

The installation will be executed on silent mode, so the system user won't
notice the installation process.
