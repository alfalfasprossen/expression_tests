import random
import time

import expression_object
from expression_object import get_or_create_expression_object

def create_random_expressions( num_base_values, num_expressions,
                               max_values_per_expression,
                               out_expression_list,
                               out_base_value_dict):
    random.seed(0)
    for i in range(num_base_values):
        bv_name = "value_%i" % i
        bv_value = True if random.randint(0,1) == 1 else False
        out_base_value_dict[bv_name] = bv_value

    for exp_idx in range(num_expressions):
        exp_str = ""
        num_vals = random.randint(1,max_values_per_expression)
        num_opening_parens = 0
        for val_idx in range(num_vals):
            real_val_idx = random.randint(0, num_base_values - 1 )
            if random.randint(0,3) == 0:
                exp_str += "!"
            if random.randint(0,1) == 0:
                exp_str += "("
                num_opening_parens += 1
            exp_str += "value_%i " % real_val_idx
            if random.randint(0,2) == 0 and num_opening_parens > 0:
                exp_str += ") "
                num_opening_parens -= 1
            if val_idx == num_vals - 1:
                exp_str += ")" * num_opening_parens
                num_opening_parens = 0
            else:
                if random.randint(0,1) == 1:
                    exp_str += "and "
                else:
                    exp_str += "or "
        out_expression_list.append(exp_str)

expression_list = []
base_value_dict = {}
create_random_expressions(100, 1000, 40, expression_list, base_value_dict)

pycmd_expression_list = []
for exp in expression_list:
    pycmd = exp.replace("!", "not ")
    pycmd_expression_list.append(pycmd)

# print base_value_dict
# for exp in expression_list:
#     print exp
def profile_python_eval(times):
    results = []
    for i in range(times):
        for exp in pycmd_expression_list:
            result = eval(exp)
            results.append(result)
    return results

def profile_object_eval(times):
    results = []
    for i in range(times):
        expression_object.invalidate_all_objects()
        for exp in expression_list:
            exp_obj = get_or_create_expression_object(exp)
            result = exp_obj.is_true()
            results.append(result)
    return results

# evaluate multiple times to get an impression of how many evaluations
# would be the point of where object based is faster than eval based
# 1, 10, 100, 1000, 10k
# note: in the profile_object_eval function, we currently invalidate
# ALL the object's cached values in each iteration.
# this would mean that the configuration of base-values has changed
# completely, which is the worst-case that could happen.
times = 1
for i in range(5):
    expression_object.basic_value_dict = base_value_dict
    expression_object.expression_object_dict = {}
    for key, value in base_value_dict.items():
        exec("%s = %s" % (key, value))
    print "evaluating %i time(s)" % times
    t1 = time.time()
    res_py = profile_python_eval(times)
    t2 = time.time()
    res_obj = profile_object_eval(times)
    t3 = time.time()
    print "python eval took %f" % (t2 - t1)
    print "object eval took %f" % (t3 - t2)
    times *= 10

#print "results do match: " + str(res_py == res_obj)
