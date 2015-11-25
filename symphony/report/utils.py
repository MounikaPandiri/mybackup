def get_least_pt(graph_data):
    min_l = 100000000
    for list_set in graph_data:
        if min(list_set) < min_l:
           min_l = min(list_set)
    return min_l-5 if min_l-5 > 0 else 0

def get_max_pt(graph_data):
    max_l = 0
    for list_set in graph_data:
        if max(list_set) > max_l:
           max_l = max(list_set)
    return max_l+5
