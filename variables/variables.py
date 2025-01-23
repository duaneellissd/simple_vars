import re
import sys
import inspect


# So functions in these work..
import os
import stat

def my_extension(  s : str ):
    parts = os.path.splitext(s)
    return parts[1]
def no_extension(  s : str ):
    parts = os.path.splitext(s)
    return parts[0]

def stat_st_mtime( s : str ):
    s = stat(s)
    return s.st_mtime
def stat_st_size( s : str ):
    s = stat(s)
    return s.st_size


func_table = {
    "str.upper"             :  ( str.upper        , "s" ),
    "str.lower"             :  ( str.lower        , "s" ),
    "str.endswith"          :  ( str.endswith     , "s" ),
    "str.startswith"        :  ( str.startswith   , "s" ),
    "str.find"              :  ( str.find         , "s" ),
    "str.isalpha"           :  ( str.isalpha      , "s" ),
    "str.isalnum"           :  ( str.isalnum      , "s" ),
    "str.isascii"           :  ( str.isascii      , "s" ),
    "str.isdecimal"         :  ( str.isdecimal    , "s" ),
    "str.isdigit"           :  ( str.isdigit      , "s" ),
    "str.islower"           :  ( str.islower      , "s" ),
    "str.isupper"           :  ( str.isupper      , "s" ),
    "str.join"              :  ( str.join         , "s,l"),
    "str.lstrip"            :  ( str.lstrip       , "s" ),
    "str.rstrip"            :  ( str.rstrip       , "s" ),
    "str.strip"             :  ( str.strip        , "s" ),
    "str.removeprefix"      :  ( str.removeprefix , "s,s"),
    "str.removesuffix"      :  ( str.removesuffix , "s,s"),
    "str.replace"           :  ( str.replace      , "s,s"),
    "len"                   :  ( len              , "s" ),
    "os.getcwd"             :  ( os.getcwd        , "" ),
    "os.path.abspath"       :  ( os.path.abspath  , "s" ),
    "os.path.join"          :  ( os.path.join     , "*" ),
    "os.path.dirname"       :  ( os.path.dirname  , "s" ),
    "os.path.basename"      :  ( os.path.basename , "s" ),
    "os.path.getsize"       :  ( os.path.getsize  , "s" ),
    "os.path.isdir"         :  ( os.path.isdir    , "s" ),
    "os.path.normcase"      :  ( os.path.normcase , "s" ),
    "os.path.normpath"      :  ( os.path.normpath , "s" ),
    "os.path.realpath"      :  ( os.path.realpath , "s" ),
    "pathtool.extension"    : ( my_extension , "s" ),
    "pathtool.no_extension" : ( no_extension , "s" ),
    "stat.st_mtime"         : ( stat_st_mtime, "s" ),
    "stat.st_size"          : ( stat_st_size, "s" )
}    
    
    

class VarError( Exception ):
    '''
    A common Exception for all VAR errors.
    (so you can catch one, not many errors)
    '''
    SYNTAX = 1
    UNDEF_FUNC = 2
    UNDEF_VAR = 3
    RECURSION = 4
    DUPLICATE = 5
    def __init__( self,  typecode : int, msg : str, history : list ):
        m = [msg]
        for n,h in enumerate(history):
            m.append("%d) %s" % (n,h))
        m = '\n'.join(m)
        Exception.__init__( self, m )
        self.msg = m
        self.history = history
        self.typecode = typecode

        
    

class Var_SyntaxError( VarError ):
    '''
    Raised when we find an obvious syntax error.
    '''
    def __init__( self, history : list, text : str ):
        VarError.__init__( self, VarError.SYNTAX, "Syntax error: %s" % text, history )
        self.text = text

class Var_UndefinedFunc( VarError ):
    '''
    Raised when an undefined variable function is called.
    '''
    def __init( self,   name : str, history : list ):
        VarError.__init__( self, VarError.UNDEF_FUNC, "undefined function: %s" % name, history )
        self.name = name

class Var_UndefinedVar( VarError ):
    '''
    Raised when an undefined variable is referenced
    '''
    def __init__(self, name : str, history : list ):
        VarError.__init__( self, VarError.UNDEF_VAR, "ERROR undefined var: %s" % name, history )
        self.name = name

class Var_RecursionError( VarError ):
    '''
    Raised when a variable is recursive
    example: ${A}->${B}->${A} endlessly.
    '''
    def __init__(self,  history : list ):
        VarError.__init__( self, VarError.RECURSION, "Recursive stop %d tries" % len(history), history )

class Var_Duplicate( VarError ):
    '''
    Raised when defining a variable and it is a duplicate
    '''
    def __init__(self,new_name, old_name  ):
        # One day, the new/old will have "where defined" attribute.
        VarError.__init__( self, new_name.where, VarError.DUPLICATE,
                           "Duplicate variable: %s" % new_name)
        self.new_name = new_name
        self.old_name = old_name
                           
                           

# SIMPLE-MATCH:
#   Match <LHS> ${ CONTENT } <RHS>
#   Note: LHS or RHS might be empty.
_re_simple_var = re.compile(r'(?P<LHS>^.*)[$][{](?P<CONTENTS>.*)[}](?P<RHS>.*$)')
# Match a function call like: ${os.path.abspath(${OBJ_DIR})}
#   note that: ${OBJ_DIR} would be resolved first...
#   Then the function os.path.abspath() would be called.
_re_function_call=re.compile(r'^(?P<fname>[a-zA-Z_][A-Z0-9a-z_.]*)[(](?P<params>.*)[)]$')
# This matches a basic variable name, ie: ${OBJ_DIR}
# used to determine if we have a VARNAME or FUNCTION_CALL
_re_basic_name = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*$')

class _resolver():
    '''
    This is the variable resolver.
    You don't use this directly, the Variable class uses this to resolve vars.
    Generally, the idea is to call: "_resolver.do_pass()" in a loop.
    '''
    def __init__( self, parent, starting_text, vars : dict ):
        self._parent = parent
        self._vars = vars
        self.history = [ starting_text ]
    def _do_replacement( self, lhs, value, rhs ):
       
        result = lhs + value + rhs
        self.history.append(result)
        return (True,result)
    def _basic_var( self, lhs,  varname, rhs):
        '''
        Once a basic variable is found, this does the replacement.
        '''
        if str(varname) not in self._vars:
            e = Var_UndefinedVar( varname, self.history )
            self._parent.fatal(e)
            # raise e
        value = self._vars.get( varname, None )
        result = self._do_replacement( lhs, value, rhs )
        return result

    def _get_params( self, fname : str , fentry : dict , param_text : str ):
        '''
        Given the function table entry (a tuple)
        Where: fentry[0] = the function pointer
        And:   fentry[1] = the parameter list.
        RETURN an LIST of parameters.
        
        TODAY: I am a lazy bastard, so we split on commas
        FUTURE: we might add quoted strings and fancy stuff
        '''
        # Just split our params up simple style.
        if len(param_text) == 0:
            our_params = []
        else:
            our_params = param_text.split(',')

        # TODO:
        #    Determine what the actual implimentation requires.
        #    For some detail, see:
        #        https://docs.python.org/3/library/inspect.html
        # The idea is some type of syntax checking.. 
        
        return our_params
    
    def _do_function_call( self, lhs, func_match, rhs ):
        '''
        This handles a function call, for example: ${str.upper(${A})}
        '''
        fname = func_match['fname']
        if fname not in func_table:
            raise Var_UndefinedFunc( fname, self.history )
        entry = func_table.get( fname )
        param_list = self._get_params( fname, entry, func_match['params'] )
        func_ptr = entry[0]
        result = func_ptr( *param_list )
        if not isinstance(result,str):
            result = str( result )
        text = self._do_replacement(lhs, result, rhs )
        return text
    
    def do_pass( self, text  ):
        '''
        this performs the simple and function type replacement.
        This does ONE and only ONE replacement.
        This function returns a tuple, (BOOL, Result)
        This function also tracks "history"
        where:
           Result is the current text string.
           BOOL is TRUE if a replacement was made (forward progress)
           BOOL is FALSE if no replacement was found (ie: done)    
        '''
        # stop the recursive case where:  ${A}->${B}->${A} endlessly.
        if len(self.history) > 20:
            raise Var_RecursionError(self.history)
        lh_loc = 0
        rh_loc = len(text)
        done = False
        while not done:
            start= text.find("${",lh_loc)
            if start < 0:
                # No further progress can be made.
                return (False,text)
            # See if there is another further ahead, ie: ${${inside}}
            tmp = text.find("${",start+2)
            if tmp >= 0:
                # There is another var so keep searching
                lh_loc = tmp # +2 skips the opening ${
                continue
            done = True
            lh_loc = start
        # find the closing curly brace
        rh_loc = text.find('}', lh_loc )
        if rh_loc < 0:
            # Missing closing curly brace?
            raise Var_SyntaxError( self.history, text )
        lhs = text[0:lh_loc] #
        # The +2 skips the opening ${
        varname = text[lh_loc+2:rh_loc].strip()
        rhs = text[rh_loc+1:] # +1 skips the } close.
        if _re_basic_name.match( varname ):
            return self._basic_var( lhs, varname, rhs )

        # If not a var, is this a function call?
        content = varname.strip()
        # FUTURE: support NESTED function calls??
        # ie:  ${os.path.abspath(os.path.join('dog','cat','frog'))}
        func_match = _re_function_call.match( content )
        if func_match is not None:
            # YES - then do the function call.
            return self._do_function_call( lhs, func_match, rhs )
        # otherwise it is a syntax error.
        raise Var_SyntaxError( self.history, text )
        

class Variables():
    '''
    This gives a crude "shell-like" text variables with some functions.
    Example:
        dog_name=Walter
        the text: "My Dog's name is ${dog_name}"
        when resolved, would be: "My Dog's name is Walter"
    '''
    def __init__(self):
        self._vars = dict()
        self.just_exit = True

    def fatal( self, the_exception ):
        if self.just_exit:
            print( str(the_exception ) )
            sys.exit(1)
        else:
            raise the_exception
    def replace( self, name, value  ):
        '''
        Replace the definition of this var.
        '''
        self._vars[name] = value

    def add( self, new_name  , value  ):
        if new_name in self._vars:
            old = self._vars[new_name]
            raise Var_Duplicate( new_name, old )
        self.replace( new_name, value )

    def add_dict( self, somedict ):
        for k,v in somedict.items():
            self.add( k,v )
    def resolve( self, text ):
        '''
        Given text in the form: "hello ${planet}" perform var replacement.
        Also handles: "hello ${str.upper(${planet})}"
        '''
        tmp = _resolver( self, text, self._vars )
        progress = True
        while progress:
            (progress,text) = tmp.do_pass( text )
        return text

def _create_test_v():
    v = Variables()
    # Simple replacement.
    v.add( 'dog3', 'walter')
    v.add( 'dog1', 'shatzi')
    v.add( 'dog2', 'dolly' )
    v.add( "DOG", "${str.upper(${dog1})}")
    # create a loop
    v.add( "A", "${B}" )
    v.add( "B", "${C}" )
    v.add( "C", "${A}" )
    return v

def _standard_case( input_text, expected_text ):
    DUT = _create_test_v()
    answer = DUT.resolve( input_text )
    assert( answer == expected_text )
    frame = inspect.currentframe().f_back
    print("Success: %s" % frame.f_code.co_name )

def _expect_error( text, errcode ):
    DUT = _create_test_v()
    DUT.just_exit = False
    try:
        DUT.resolve( text )
        # should have asserted
        assert(False)
    except VarError as E:
        assert( E.typecode == errcode )
    # All is well
    frame = inspect.currentframe().f_back
    print("Success: %s" % frame.f_code.co_name )

def _test_case1():
    '''Simple...'''
    _standard_case( "${dog3}", "walter" )

def _test_case2():
    ''' Nested.. '''
    DUT = _create_test_v()
    DUT.replace( "C", "${dog3}")
    answer = DUT.resolve("${A}")
    assert( answer == 'walter' )
    print("success: _test_case2")

    
def _test_case3():
    _expect_error( "${cat}", VarError.UNDEF_VAR )

def _test_case4():
    _expect_error( "${A}", VarError.RECURSION )
    
def _test_case5():
    _standard_case( "my dogs name is: ${dog3}", 'my dogs name is: walter' )

def _test_case6():
    _standard_case("${dog3} is my dogs name", 'walter is my dogs name' )

def _test_case7():
    _standard_case( "first ${dog1} second: ${dog2} third: ${dog3} today", "first shatzi second: dolly third: walter today")

def _test_case8():
    _expect_error( "var ${dog without close", VarError.SYNTAX )

def _test_case9():
    _standard_case("${dog1} ${dog2} ${dog3}", "shatzi dolly walter")

def _test_case10():
    _standard_case("${DOG}", "SHATZI")

def _test_case11():
    tmp = os.getcwd()
    _standard_case("${os.getcwd()}", tmp )
    expect = "before %s after" % tmp
    _standard_case("before ${os.getcwd()} after", expect)

def _test_case12():
    tmp ="dog %s cat" % os.getcwd()
    _standard_case("dog ${os.path.abspath(.)} cat", tmp )

def _test_case13():
    v = Variables()
    v.add_dict( os.environ )
    s = v.resolve("Your HOME dir is ${HOME}")
    print("Result: %s" % s)

def unit_test():
    '''
    Unit test for this module is here.
    '''
    _test_case1()
    _test_case2()
    _test_case3()
    _test_case4()
    _test_case5()
    _test_case6()
    _test_case7()
    _test_case8()
    _test_case9()
    _test_case10()
    _test_case11()
    _test_case12()
    _test_case13()
    print("var selftest complete")

if __name__ == '__main__':
   unit_test()
   sys.exit(0)

    
