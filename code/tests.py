"""
tests.py - checks that our functions are actually right. run it with: python code/tests.py
if everything is fine it prints 4 lines that start with OK. if something is wrong it crashes
"""
# random for making random test graphs, itertools for orderings and groups of 3
import random, itertools
# networkx is ONLY used here to double check our counts, never for the real counting
import networkx as nx
# our own file with the triad functions
import motifs
# this lets us write config_code instead of motifs.config_code (same for the other functions)
from motifs import *

# test 1: check there are 16 shapes and 13 of them are connected (what the project says)
# helper: turns a 6-bit code back into the list of edges it stands for
def edges_of(code):
    # for each bit position k, if that bit is on, include the edge (i, j)
    return {(i, j) for k, (i, j) in enumerate(BIT_EDGES) if code >> k & 1}
# for all 64 possible codes: take the smallest code over all 6 orderings (canonical code)
# putting them in a set removes repeats, so what's left is one code per shape
canon = {min(config_code(p, edges_of(code)) for p in itertools.permutations(range(3)))
         for code in range(64)}
# there must be exactly 16 shapes, and exactly 13 of them are in our connected list
assert len(canon) == 16 and len([c for c in canon if c in CONNECTED_CODES]) == 13
# and every code in our connected list must really be one of the shapes
assert set(CONNECTED_CODES) <= canon
print("OK: 64 configs -> 16 orbits, 13 connected classes match the table")

# test 2: hand examples where we already know the answer
# a cycle 0->1->2->0 should be class 9
assert triad_class(0, 1, 2, {(0, 1), (1, 2), (2, 0)}) == 9
# same cycle but with different people (5, 7, 9) should still be class 9
assert triad_class(5, 7, 9, {(5, 7), (7, 9), (9, 5)}) == 9
# only one email means one person is left out, so not connected = None
assert triad_class(0, 1, 2, {(0, 1)}) is None
# one person sends to two others (0->1 and 0->2) is class 1
assert triad_class(0, 1, 2, {(0, 1), (0, 2)}) == 1
print("OK: hand examples")

# test 3: our fast counting vs brute force vs networkx on lots of random graphs
# networkx's names for the shapes -> our class numbers
NX = {"021D": 1, "021C": 2, "111U": 3, "021U": 4, "030T": 5, "120U": 6, "111D": 7,
      "201": 8, "030C": 9, "120C": 10, "120D": 11, "210": 12, "300": 13}
# random generator with a fixed seed so the tests are the same every time
rng = random.Random(1)
# try 60 different random graphs
for trial in range(60):
    # random number of people n and random number of emails m
    n = rng.randint(3, 25); m = rng.randint(2, n * (n - 1) // 2)
    # build a random set of m emails
    E = set()
    # keep adding until we have m emails
    while len(E) < m:
        # pick a random sender and receiver
        u, v = rng.randrange(n), rng.randrange(n)
        # only add if they aren't the same person (no self loops)
        if u != v: E.add((u, v))
    # the people are 0, 1, ..., n-1
    nodes = list(range(n))
    # our fast count
    fast = triad_census(nodes, E)
    # brute force: check EVERY group of 3 people and count by hand
    brute = [0] * 13
    # every possible group of 3 people
    for a, b, c in itertools.combinations(nodes, 3):
        # which class is it (None if not connected)
        k = triad_class(a, b, c, E)
        # if it's connected, add 1 to that class
        if k: brute[k - 1] += 1
    # the fast count must equal the brute force count
    assert fast == brute, (fast, brute)
    # now ask networkx to count the same graph
    g = nx.DiGraph(); g.add_nodes_from(nodes); g.add_edges_from(E)
    # networkx's counts, and an empty list to fill in our class order
    cen = nx.triadic_census(g); mapped = [0] * 13
    # translate networkx's names into our class order
    for name, k in NX.items(): mapped[k - 1] = cen[name]
    # networkx must agree with us
    assert mapped == fast
    # also test the shuffling: shuffle this graph 10 x edges times
    R = randomize(E, 10 * len(E), seed=trial)
    # everyone's in and out degrees must be exactly the same as before
    assert degree_sequences(nodes, R) == degree_sequences(nodes, E)
    # no lost edges, no duplicates, no self loops
    assert len(set(R)) == len(R) == len(E) and all(u != v for u, v in R)
print("OK: census == brute force == networkx (60 random graphs); swaps keep in/out-degree")

# test 4: z-score maths. real count 7, random counts 4 and 6 -> average 5, spread 1, so z = 2
z, mu, sd = z_scores([7] + [0] * 12, [[4] + [0] * 12, [6] + [0] * 12])
# class 1 should have z = 2, and class 2 never changes (spread 0) so z must be 0
assert z[0] == 2.0 and z[1] == 0.0
print("OK: z-score (population std, sigma=0 -> 0)")
