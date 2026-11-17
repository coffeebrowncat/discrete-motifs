"""Run: python tests.py  -- self-checks for the core functions."""
import random, itertools
import networkx as nx
import motifs
from motifs import *

# 16 orbits, 13 connected (spec section 2)
def edges_of(code):
    return {(i, j) for k, (i, j) in enumerate(BIT_EDGES) if code >> k & 1}
canon = {min(config_code(p, edges_of(code)) for p in itertools.permutations(range(3)))
         for code in range(64)}
assert len(canon) == 16 and len([c for c in canon if c in CONNECTED_CODES]) == 13
assert set(CONNECTED_CODES) <= canon
print("OK: 64 configs -> 16 orbits, 13 connected classes match the table")

# hand example (T3): 3-cycle 0->1->2->0 has code 25 -> Class 9
assert triad_class(0, 1, 2, {(0, 1), (1, 2), (2, 0)}) == 9
assert triad_class(5, 7, 9, {(5, 7), (7, 9), (9, 5)}) == 9
assert triad_class(0, 1, 2, {(0, 1)}) is None             # disconnected
assert triad_class(0, 1, 2, {(0, 1), (0, 2)}) == 1         # one sender, two receivers
print("OK: hand examples")

NX = {"021D": 1, "021C": 2, "111U": 3, "021U": 4, "030T": 5, "120U": 6, "111D": 7,
      "201": 8, "030C": 9, "120C": 10, "120D": 11, "210": 12, "300": 13}
rng = random.Random(1)
for trial in range(60):
    n = rng.randint(3, 25); m = rng.randint(2, n * (n - 1) // 2)
    E = set()
    while len(E) < m:
        u, v = rng.randrange(n), rng.randrange(n)
        if u != v: E.add((u, v))
    nodes = list(range(n))
    fast = triad_census(nodes, E)
    # brute force over every 3-subset
    brute = [0] * 13
    for a, b, c in itertools.combinations(nodes, 3):
        k = triad_class(a, b, c, E)
        if k: brute[k - 1] += 1
    assert fast == brute, (fast, brute)
    g = nx.DiGraph(); g.add_nodes_from(nodes); g.add_edges_from(E)
    cen = nx.triadic_census(g); mapped = [0] * 13
    for name, k in NX.items(): mapped[k - 1] = cen[name]
    assert mapped == fast
    # randomize keeps degrees
    R = randomize(E, 10 * len(E), seed=trial)
    assert degree_sequences(nodes, R) == degree_sequences(nodes, E)
    assert len(set(R)) == len(R) == len(E) and all(u != v for u, v in R)
print("OK: census == brute force == networkx (60 random graphs); swaps keep in/out-degree")
z, mu, sd = z_scores([7] + [0] * 12, [[4] + [0] * 12, [6] + [0] * 12])
assert z[0] == 2.0 and z[1] == 0.0
print("OK: z-score (population std, sigma=0 -> 0)")
