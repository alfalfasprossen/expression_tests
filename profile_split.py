import time

def mysplit(string):
    """ splitting in pure python is about 8 times slower than
    the python internal split function, which calls underlying c-code
    and uses the c-equivalent of the find-function to find the next
    position in the text of where to split.
    so technically using the python string find method should still be much
    faster than walking through the string char by char.
    """
    result = []
    last_split = 0
    for i in range(len(string)-3):
        if( string[i] == "a" and
            string[i+1] == "n" and
            string[i+2] == "d"):
            partial = string[last_split:i]
            last_split = i+3
            result.append(partial)
    rest = string[last_split:]
    result.append(rest)
    return result

a = "a and b and c and d"

t1 = time.time()
for i in range(1000000):
    res = a.split("and")
t2 = time.time()
#print res
#t2 = time.time()
for i in range(1000000):
    res = mysplit(a)
t3 = time.time()
#print res
print "split took %f" % (t2-t1)
print "msplit took %f" % (t3-t2)
print "msplit took %f times as long as split" % ((t3 - t2)/(t2 - t1))
