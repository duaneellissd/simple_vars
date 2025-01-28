# simple_vars
Simple `${VARIABLE}` routines that only do text replacements

* Basic Text base variables
	```python
	s = "A ${BOY} and his ${DOG}"
	my_vars = Variables()
	my_vars.add("BOY","Zack")
	my_vars.add("DOG","scout")

	result = my_vars.resolve( s )
	print("result: %s" % result )
	```

    Should produce:
	```bash
	"A Zack and his scout"
	```

* Going further there are other features:
	```python
	d = some_dict_of_vars()
	my_vars = Variables()
	my_vars.add_var_dict(d)
	```

* And..
	```python
	my_vars = Variables()
	# There are a number of functions you can use
	my_vars.add("ROOT_DIR","${os.path.abspath("~/project/foo")}" )
	s = my_vars.resolve("${ROOT_DIR}/config.file")
	print("CFG file is: %s" % s )
	```

* And
	```python
	import os
	my_vars = Variables()
	my_vars.add_dict(os.environ)
	s = my_vars.resolve("${HOME}")
	print("your home direcory is: %s"  % s )
	```

* Built in Unit test
	```bash
	cd variables
	python3 variables.py
	```
