installer: libs
	pynsist installer-x86.cfg
	pynsist installer-x86_64.cfg

libs:
	./get_deps.sh
