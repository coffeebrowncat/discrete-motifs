"""
motifs.py - the actual maths part. all written by us, no graph libraries

the big idea:
a triad is 3 people plus whatever emails exist between them.
3 people can have 6 possible directed edges, so there are 2^6 = 64 possible patterns.
a lot of those patterns are the same shape with the people swapped around (isomorphic),
so the 64 collapse into 16 shapes. 13 of those are connected (nobody is totally left out).
those 13 shapes are the triad classes 1 to 13
"""

# random is for shuffling the graph
# permutations gives every ordering of a list, combinations gives every pair/group from a list
import random
from itertools import permutations, combinations

# the 6 possible edges between slot 0, slot 1, slot 2 of a triad
# the position in this list is the bit number (the project fixed this order)
#   bit0: 0->1   bit1: 0->2   bit2: 1->0   bit3: 1->2   bit4: 2->0   bit5: 2->1
BIT_EDGES = [(0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1)]

# the canonical codes of the 13 connected shapes, smallest to biggest
# class number = position in this list + 1 (so code 3 is class 1, code 63 is class 13)
CONNECTED_CODES = [3, 6, 7, 10, 11, 15, 21, 23, 25, 27, 30, 31, 63]
# lookup table: code -> class number. the disconnected shapes just aren't in here
CODE_TO_CLASS = {code: i + 1 for i, code in enumerate(CONNECTED_CODES)}


def config_code(order, edge_set):
    """gives the 6-bit number for a triad when we read its people in one specific order

    order    - tuple (a, b, c): which real person sits in slot 0, slot 1, slot 2
    edge_set - set of all emails (u, v) in the graph
    for each of the 6 possible edges, if it really exists we turn that bit on
    """
    # start with all bits off (0)
    code = 0
    # go through the 6 possible edges, k is the bit number, (i, j) is the slot pair
    for k, (i, j) in enumerate(BIT_EDGES):
        # slot i -> slot j means real person order[i] -> real person order[j]. is that email real?
        if (order[i], order[j]) in edge_set:
            # yes, so turn bit k on (1 << k is a 1 moved k places left)
            code |= 1 << k
    # give back the finished number
    return code


def canonical_code(a, b, c, edge_set):
    """the smallest code across all 6 orderings of the people a, b, c

    the same shape gives different codes depending on who you put in which slot,
    so we always take the minimum. same minimum = same shape. that's the whole trick
    """
    # try all 6 orderings of (a, b, c), get a code for each, keep the smallest
    return min(config_code(p, edge_set) for p in permutations((a, b, c)))


def triad_class(a, b, c, edge_set):
    """gives the class (1 to 13) of people a, b, c, or None if they aren't connected

    None happens when the canonical code is 0, 1 or 5: no emails at all, or one lonely
    email with the third person left out
    """
    # work out the canonical code, then look it up in the table (.get gives None if missing)
    return CODE_TO_CLASS.get(canonical_code(a, b, c, edge_set))


def build_adjacency(nodes, edges):
    """makes a neighbour list: nbrs[v] = everyone v sent to OR got an email from

    "connected" for triads ignores direction, so we flatten the arrows here
    """
    # give every person an empty set of neighbours to start
    nbrs = {v: set() for v in nodes}
    # go through every email u -> v
    for u, v in edges:
        # v is a neighbour of u
        nbrs[u].add(v)
        # and u is a neighbour of v (ignoring direction)
        nbrs[v].add(u)
    # give back the neighbour lists
    return nbrs


def triad_census(nodes, edges):
    """counts how many connected triads of each class there are, gives back [N1, ..., N13]

    why not just check every group of 3 people? way too slow, and most aren't even connected
    useful fact: in any connected triple, one person touches the other two
    so for every person v we look at every PAIR (u, w) of v's neighbours,
    and that finds every connected triple. to count each triple exactly once:
      open path (u and w not adjacent): only one centre (v), so only v finds it. count it
      triangle (u and w adjacent): all 3 people find it, so only count it when v is the smallest
    """
    # make sure we have a set of edges (fast lookups), convert if it's a list
    edge_set = edges if isinstance(edges, (set, frozenset)) else set(edges)
    # get everyone's neighbour list
    nbrs = build_adjacency(nodes, edge_set)
    # 13 counters, all at 0. counts[0] is class 1, counts[12] is class 13
    counts = [0] * 13
    # take every person as the possible centre v
    for v in nodes:
        # every pair of v's neighbours. sorted means u is always smaller than w, so no repeats
        for u, w in combinations(sorted(nbrs[v]), 2):
            # are u and w neighbours too? if yes then v, u, w form a triangle
            if w in nbrs[u]:
                # it's a triangle. if v isn't the smallest person (u < w already, so check v vs u)
                if v > u:
                    # skip it, the smallest person will count it
                    continue
            # find which class this triad is
            cls = triad_class(v, u, w, edge_set)
            # add 1 to that class's counter (cls starts at 1, list starts at 0, hence the -1)
            counts[cls - 1] += 1
    # give back all 13 counts
    return counts


def randomize(edges, attempts, seed):
    """shuffles the graph with double edge swaps. gives back a NEW edge list, the input isn't touched

    one attempt: grab two random emails (a,b) and (c,d) and turn them into (a,d) and (c,b)
    the attempt is rejected (graph stays the same, but the attempt still counts) if:
      a == d or c == b          -> it would make someone email themselves
      (a,d) or (c,b) exists     -> it would make a duplicate email
    why nobody's degree changes: a and c still send exactly one email each (out-degree same),
    b and d still receive exactly one each (in-degree same). only who-gets-what got rewired
    """
    # our own random generator started from the seed, so the shuffle is repeatable
    rng = random.Random(seed)
    # list copy so we can pick edges by position
    edge_list = list(edges)
    # set copy so "does this email exist?" is instant
    edge_set = set(edge_list)
    # how many edges there are
    m = len(edge_list)
    # need at least 2 edges to swap anything
    if m < 2:
        return edge_list
    # do the swap attempts, one loop = one attempt
    for _ in range(attempts):
        # pick a random edge position (every edge equally likely)
        i = rng.randrange(m)
        # pick another random edge position (could be the same one, then it gets rejected)
        j = rng.randrange(m)
        # first email: a sent to b
        a, b = edge_list[i]
        # second email: c sent to d
        c, d = edge_list[j]
        # reject if it would make a self loop (a == d or c == b) or a duplicate edge
        if a == d or c == b or (a, d) in edge_set or (c, b) in edge_set:
            # do nothing, go to the next attempt
            continue
        # remove the two old emails from the set
        edge_set.discard((a, b)); edge_set.discard((c, d))
        # add the two new swapped emails to the set
        edge_set.add((a, d)); edge_set.add((c, b))
        # replace the old edges in the list too
        edge_list[i] = (a, d)
        edge_list[j] = (c, b)
    # give back the shuffled edge list
    return edge_list


def degree_sequences(nodes, edges):
    """gives (indeg, outdeg): how many emails each person received and sent

    we use this to PROVE the swaps didn't change anyone's degrees
    """
    # everyone starts at 0 received and 0 sent
    indeg = {v: 0 for v in nodes}
    outdeg = {v: 0 for v in nodes}
    # go through every email u -> v
    for u, v in edges:
        # u sent one email
        outdeg[u] += 1
        # v received one email
        indeg[v] += 1
    # give back both
    return indeg, outdeg


def z_scores(real_counts, random_counts):
    """works out the z-score for each class: Z = (real count - random average) / random spread

    real_counts   - [N1..N13] for the real graph
    random_counts - a list of [N1..N13], one for each random graph
    mu = average over the random graphs
    sigma = POPULATION standard deviation (divide by n, not n-1)
    if sigma is 0 (that class never changes in the random graphs) we say Z = 0
    Z above 2 = motif (shows up more than chance), Z below -2 = anti-motif (less than chance)
    gives back (z, mu, sigma), each a list of 13 numbers
    """
    # how many random graphs we have
    n = len(random_counts)
    # empty lists to fill up, one entry per class
    z, mus, sigmas = [], [], []
    # do the same thing for each of the 13 classes
    for k in range(13):
        # this class's count in every random graph
        vals = [rc[k] for rc in random_counts]
        # average of those counts
        mu = sum(vals) / n
        # variance: average of (value - average) squared
        var = sum((x - mu) ** 2 for x in vals) / n
        # standard deviation = square root of the variance
        sigma = var ** 0.5
        # save mu and sigma
        mus.append(mu); sigmas.append(sigma)
        # z-score, but if sigma is 0 just use 0 so we don't divide by zero
        z.append(0.0 if sigma == 0 else (real_counts[k] - mu) / sigma)
    # give back everything
    return z, mus, sigmas
