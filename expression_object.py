
"""
The idea is to split an expression into a tree / graph of expression objects.
Each expression object can be evaluated, which will evaluate all children
if necessary (or-based expressions may break early after the first 'true' child).
Technically this can be achieved by using the all() and any() functions for
a list of evaluated children.

When an object has been evaluated, we could save its state until it is invalidated
by some special call which might scan a tree upwards from a basic expression
that has been invalidated and invalidating all parents. Caching the state of one
object can speed up successive queries on it enormously, but may be not necessary.
Or this could be limited to occasions where we know that the current state will not
change and we will evaluate a lot of expressions with the same members for a while.
Then maybe invalidate ALL objects to force a new evaluation.

Parsing a string expression into objects is done by breaking the string into
its sub-expressions. A sub-expression is firstly anyhing that is embraced in
parens. Each such sub-expression will form another expression-object which again
may break up its sub-expressions into multiple objects.

After making sure we don't split inbetween parens from the outside, we have to
split logical operations that form inceonsistently across the string. Meaning
a concatenation of ANDs mixed with an OR outside of parens.
  A and B or C
would be such an example.
We split by OR first because we define AND to take precedence.
This will again yield sub-expressions that will need to be handled by multiple
expression objects, resulting in
  [A and B], [C], [(A and B) or C]
in the example.
Finally break up any AND chains into their sub-expressions which will likely be
single value statements.
Let these also be represented by expression objects. These would technically be
the source of any configuration and inherit their value from however
a configuration is put into the system.


Evaluating an expression.
When evaluating an expression, text form, search for the expression object
that represents this text (hashed in a dictionary). If not found, create it.
When evaluating that expression object, it will evaluate all its children up to
that point when it can give an unambiguous statemtent about its current status.

To detect circular dependencies, a caller_stack (a list) is injected into the first
call to evaluate in which each expression object will push itself at the end
and pop again when it is done evaluating. As soon as the same object exists twice
on the stack, that means that an objects evaluation depends on the status of itself
which cannot be resolved.

To handle inverted children inside an ExpressionObject we have two possible ways
one is to create a tuple per child which consists of the child an an indicator
if the value needs to be inverted.
The other option is to keep a second list that has the same amount of elements
therefore the indices match. This list would keep booleans for telling if the
equivalent index would be inverted

The problem with both approaches is that there may be cases where an
inversion is taking place above any child-level. Technically that would
require us to make SOME_EXP and !SOME_EXP different objects.
We don't want to create any more cached values than necessary.
When SOME_EXP has been evaluated once, we know that !SOME_EXP would only
be the inverted cached value, so we don't want them to be different
objects whenever possible.

The case where this is not possible is if the inversion happens on the
top-level of an expression. We can handle all sub-level inversions through
the aforementioned tuple or list for children.
the expression
  [A and !B] would reference the children [A],[B] and have an inversion
list of [0,1]
Since A and B are not top-level expressions, keeping the inversion info
in the [A and !B] expression object is sufficient.
Assuming there is another object that makes use of [!B] directly.
Since this is a single-value expression, it would have no children, so
we could not store the inversion-information this way.

A possible solution is to create new objects for these cases but still
make use of the caching by creatin a top-level object [!B] that references
the child [B] and has an inversion list of [1].
This way the value [B] can be gathered as always, and the inversion is
taking place in a pipe-through kind of expression object.
"""


TYPE_AND = 1
TYPE_OR = 2

expression_object_dict = {}

basic_value_dict = {
    "A" : True,
    "B" : True,
    "C" : False,
    "D" : True,
    "G" : True,
    "F" : True,
    "H" : False}

test_expr = "A and B and (C or D) and (G and (F or H))"

class ExpressionObject():
    def __init__(self, exp):
        self._expression = exp
        self._cached_value = None
        self._type = TYPE_AND
        self._children = []
        self._inverted_child_indices = []
        self.parse_expression(self._expression)

    def __str__(self):
        #return (self._expression + " type: " + str(self._type) +
        #        " cached_value: " + str(self._cached_value))
        return self.__repr__()

    def __repr__(self):
        return "ExpressionObject(\"%s\")" % self._expression

    def is_true(self):
        """ Evaluate this expression. This may cause sub-expressions
        to be evaluated.

        Call this function from outside of of expression objects. Do
        not use this function to get the value of children of this
        expression object, use _evaluate_children on these instead.
        """
        return self._evaluate_children(list())

    def invalidate(self):
        """ Invalidate the cached value of this expression object.
        """
        # TODO:
        # This should cause all expression objects that depend on this
        # to also be invalidated, thus causing them to re-evaluate
        # themselves and all uncached children the next time their
        # value is queried.
        self._cached_value = None

    def _evaluate_children(self, caller_stack):
        """ Evaluate this expression internally. If the value of it
        has been cached and not invalidated, return the cached value.

        Otherwise evaluate the children if necessary. If this expression
        has no children, the value for it must exist in the
        basic_value_dict as this is not a composite of single-value-
        expressions, but a single-value-expression itself.

        We call this function directly in children to provide the stack
        of previous callers to identify circular dependencies.
        """
        if self in caller_stack:
            raise AssertionError("circular dependency detected object[%s], "
                                 "caller stack: \n%s"
                                 % (self._expression,
                                    " --> ".join([str(obj) for obj in caller_stack])))
        else:
            caller_stack.append(self)

        if self._cached_value is not None:
            caller_stack.pop()
            return self._cached_value
        if len(self._children) == 0:
            try:
                self._cached_value = basic_value_dict[self._expression]
                caller_stack.pop()
                return self._cached_value
            except KeyError:
                print("Value for single-statement expression %s not found"
                      % self._expression)

        for child, inversion in zip(self._children, self._inverted_child_indices):
            value = child._evaluate_children(caller_stack)
            if inversion:
                value = not value
            if self._type == TYPE_OR and value == True:
                self._cached_value = True
                caller_stack.pop()
                return self._cached_value
            elif self._type == TYPE_AND and value == False:
                self._cached_value = False
                caller_stack.pop()
                return self._cached_value
        if self._type == TYPE_AND:
            self._cached_value = True
        else:
            self._cached_value = False
        caller_stack.pop()
        return self._cached_value

    def parse_expression(self, expr_str):
        """ Identify the type of this expression and add all the
        sub-expression (children) of this expression, create them if
        they don't already exist.
        """
        # TODO: check the inversion thing
        # if this expression starts with an inversion (top-level-inversion)
        # we need to register this and create a sub-expression that
        # is the complete expression just without the inversion.
        # pipe-through
        clean_expr_str, inversion = get_clean_expression_and_inversion(expr_str)
        if inversion:
            ref_expr_obj = get_or_create_expression_object(clean_expr_str)
            self._children.append(ref_expr_obj)
            self._inverted_child_indices.append(inversion)
            return

        sub_exps = intelligent_split_or(expr_str)
        if len(sub_exps) == 1:
            # no top-level or's in the expression,
            # try to split the and's
            sub_exps = intelligent_split_and(expr_str)
        else:
            self._type = TYPE_OR
        if len(sub_exps) == 1:
            # also no top-level and's in the expression,
            # this is a single-value expression without any
            # logical operators

            # if this expression is a single-value and we have an inversion
            # we also need to register this completely as a pipe-through
            return
        for sub_exp in sub_exps:
            cleaned_sub_exp, inversion = get_clean_expression_and_inversion(sub_exp)
            new_exp_object = get_or_create_expression_object(cleaned_sub_exp)
            self._children.append(new_exp_object)
            self._inverted_child_indices.append(inversion)

def get_or_create_expression_object(expr_str):
    clean_expr_str, inversion = get_clean_expression_and_inversion(expr_str)
    if inversion:
        clean_expr_str = strip_expression(expr_str)
    try:
        return expression_object_dict[clean_expr_str]
    except KeyError:
        #print "creating new expression object for '%s'" % clean_expr_str
        pass
    new_exp_object = ExpressionObject(clean_expr_str)
    expression_object_dict[clean_expr_str] = new_exp_object
    return new_exp_object


# only parse the outermost parens of each sub-expression, pipe the complete
# content into another object.
def parse_expression(self, text):
    # indices of opening parens found in the text
    opening_parens_count = 0
    opening_paren_index = -1
    closing_parens_count = 0
    for i in range(len(text)):
        if text[i] == "(":
            # found an opening paren, put it on the stack
            opening_parens_count += 1
            opening_paren_index = i
        elif text[i]==")":
            closing_parens_count += 1

        if opening_paren_index > -1 and (opening_parens_count ==
                                         closing_parens_count):
            # found as many closing as opening parens. that means our
            # indices describe a portion enclosed in parens,
            # an isolated sub-expression
            start = opening_paren_index
            end = i+1
            partial_text = text[start:end]
            expression_object = get_or_create_expression_object(partial_text)

            # remove the stuff we already parsed from the text we need yet to parse
            text = text[:start-1] + text[end+1:]
            # save the expression object as a potential child
            # then check for congruent and/or operators in the final string
            # this and/or should actually be seperated first, but
            # how to do that without splitting inside parens?


def find_closing_paren(string, open_paren_index):
    """ find the closing paren that matches the opening one
    that would be present at index
    note: this function could be faster with using the native find-
        function, but it would be more complicated to write it
        that way, and this is more likely the way it could be written
        in c++
    """
    opening_parens_count = 1
    opening_paren_index = open_paren_index
    closing_parens_count = 0

    for i in range(open_paren_index+1,len(string)):
        if string[i] == "(":
            opening_parens_count += 1
            opening_paren_index = i
        elif string[i]==")":
            closing_parens_count += 1
            if opening_paren_index > -1 and (opening_parens_count ==
                                         closing_parens_count):
                # found as many closing as opening parens. that means our
                # indices describe a portion enclosed in parens,
                # an isolated sub-expression
                return i
    return -1

def intelligent_split_or(string):
    """
    try to split by OR until we find an opening paren.
    If found a paren, find the closing paren that belongs to it, then
    again split all ORs until we reach the end of the string,
    or only ORs inside of parens are left.
    note: this function could be faster with using the native find-
        function, but it would be more complicated to write it
        that way, and this is more likely the way it could be written
        in c++
    """
    string = strip_expression(string)
    parts = []

    after_last_or = 0
    i = 0
    last_index = i
    while i < len(string)-1:
        #print "%i %s" %(i,string[i])
        if string[i] == "o" and string[i+1] == "r":
            # TODO: make sure we don't split inside a word
            # found an or, split string before and after this
            left_part = string[last_index:i]
            left_part = strip_expression(left_part)
            i = i + 2
            parts.append(left_part)
            last_index = i
            if i >= len(string):
                break
            continue
        elif string[i] == "(":
            #print "found an open paren"
            closing_index = find_closing_paren(string, i)
            #print "closing paren for this %i" % closing_index
            #left_part = string[last_index:i-1]
            #middle_part = string[i+1:closing_index]
            i = closing_index+1
            #parts.append(left_part)
            #parts.append(middle_part)
            #last_index = i
        else:
            i+=1
        #last_index = i
    rest = strip_expression(string[last_index:])
    if rest:
        parts.append(rest)
    return parts

def intelligent_split_and(string):
    string = strip_expression(string)
    parts = []

    after_last_or = 0
    i = 0
    last_index = i
    while i < len(string)-2:
        #pre_word_char = string[i-1]
        #post_word_char = string[i+3]
        if ((string[i] == "a" and string[i+1] == "n" and string[i+2] == "d")):
            #and
            #(pre_word_char == "" or pre_word_char == "(" or pre_word_char == " " or pre_word_char == ")") and
            #(post_word_char == "" or post_word_char)
            # TODO: make sure we don't split inside a word
            left_part = string[last_index:i]
            left_part = strip_expression(left_part)
            i = i + 3
            if left_part:
                parts.append(left_part)
            last_index = i
            if i >= len(string):
                break
            continue
        elif string[i] == "(":
            closing_index = find_closing_paren(string, i)
            i = closing_index+1
        else:
            i+=1
    rest = strip_expression(string[last_index:])
    if rest:
        parts.append(rest)
    return parts


def intelligent_split(string):
    # TODO find a way to remove the totally-enclosing parens of
    # split sup-expressions.
    # like "(a and b)", but not "(a and b) and c" or "(a and b) and (c and d)"
    if string[0] == "(":
        end = find_closing_paren(string,0)
        if end == len(string) - 1:
            string = string[1:-1]
    # TODO first find all the opening and closing braces in the string
    # then go through the string by parts and make sure to remove the
    # matching braces of each set before feeding it to the
    # other function. Otherwise we might need to reparse all the braces again?

    # maybe split by or, until only one object is left (the objects we get back)
    # each object is checked for totally-enclosedness and stripped if necessary
    # again each object is split by or until only one object remains.
    # if a single object can not be split by or anymore, split it by and
    # then again start with the or.
    # when an object can not be split by or or by and, what is left should be a
    # single value
    and_parts = []
    or_parts = intelligent_split_or(string)
    for part in or_parts:
        and_parts.extend(intelligent_split_and(part))
    return and_parts

""" using find method, is faster in python because native c-call
and a bit less index-hassle

find the next or in the string
if there is no or left, return the rest of the string
if there is an or:
  find the next opening paren
  if the opening paren comes after the or, split at the or
  otherwise find the closing paren that belongs to this opening
  paren and continue searching for or's after this
"""
def intelligent_split_2(string):
    parts = []
    last_index = 0
    while True:
        next_or = string.find("or",last_index)
        if next_or < 0:
            break
        next_open_paren = string.find("(", last_index)
        if next_open_paren > 0 and next_open_paren < next_or:
            # the or liest behind the paren, find the closing one
            closing_paren = find_closing_paren(string, next_open_paren)
            last_index = closing_paren + 1
            continue
        else:
            # the or lies before the paren, just split it off
            left_part = string[last_index:next_or-1]
            parts.append(left_part)
            last_index = next_or + 2
    parts.append(string[last_index:])
    return parts
# print "----- 0"
# print intelligent_split_2("a or b or c")
# print intelligent_split_2("a or b and c")
# print intelligent_split_2("a or b or c or")
# print "----- 1"
# print intelligent_split_2("a or b or (c and d)")
# print "----- 2"
# print intelligent_split_2("(a or b) and (c or d)")
# print "----- 3"
# print intelligent_split_2("(a and b) and (c or d)")


def strip_expression(string):
    """ return a cleaned expression string.
    this will remove any leading/trailing whitespaces and totally enclosing
    braces from the string
    """
    string = string.strip()
    if not string:
        return ""
    while string[0] == "(":
        if find_closing_paren(string, 0) == len(string) -1:
            string = string[1:-1]
            string = string.strip()
        else:
            break
    return string


def get_clean_expression_and_inversion(string):
    """ return a cleaned expression string.

    This will remove any leading/trailing whitespaces and totally enclosing
    braces from the string.
    It will also remove any leading (or only enclosed in leading braces)
    inversion marks.

    return the cleaned expression and the inversion state that any
    inversion marks define.

    example:
      "(A and B)" = ("A and B", False)
      "!(A and B)" = ("A and B", True)
      "(!(A and B))" = ("A and B", True)
      "(!(!(A and B)))" = ("A and B", False)
    """
    # TODO: i may only do the inversion decision if this is a single-value
    # or if there is parens after the inversio mark. ??
    # the expression otherwise needs to split first. Otherwise we might
    # remove the ! from an expression like "!A and B", but we only
    # may do that with "!(A and B)"
    inversion = False
    string = string.strip()
    if not string:
        return ("", False)
    while True:
        if string[0] == "(":
            if find_closing_paren(string, 0) == len(string) -1:
                string = string[1:-1]
                string = string.strip()
            else:
                break
        elif string[0] == "!":
            # check that this is a single-value or totally-enclosed
            # expression, otherwise stop stripping
            temp_str = string[1:].strip()
            if not " " in temp_str:
                # probably single-value expression
                string = temp_str
                inversion = not inversion
            elif temp_str[0] == "(":
                if find_closing_paren(temp_str, 0) == len(temp_str) -1:
                    # totally-enclosing expression
                    string = temp_str
                    string = string[1:-1].strip()
                    inversion = not inversion
                else:
                    break
            else:
                break
        else:
            break
    return (string, inversion)

def invalidate_all_objects():
    for exp_obj in expression_object_dict.values():
        exp_obj.invalidate()
