# simple_vars
Simple ${VARIABLE} routines that only do text replacements

* Basic Text base variables

	s = "A ${BOY} and his ${DOG}"
	vars = Variables()
	vars.define( "BOY", "Zack" )
	vars.defined("DOG", "scout")

	result = vars.resolve( s )
	print("result: %s" % result )

    Should produce:
	"A Zack and his scout"

* Going further there are other features:

	d = some_dict_of_vars()
	vars = Variables()
	vars.add_var_dict( d )

* And..
	vars = Variables()
	# There are a number of functions you can use
	vars.add("ROOT_DIR", "${os.path.abspath("~/project/foo")}" )
	s = vars.resolve("${ROOT_DIR}/config.file")
	print("CFG file is: %s" % s )

* And
	import os
	vars = Variables()
	vars.add_dict( os.environ )
	s = vars.resolve("${HOME}")
	print("your home direcory is: %s"  % s )
	

