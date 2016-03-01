all: libs installer_32 installer_64

installer_32:
	pynsist installer-x86.cfg

installer_64:
	pynsist installer-x86_64.cfg

libs:
	./get_deps.sh
