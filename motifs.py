"""
motifs.py - the actual maths part. no graph libraries, all ours.

vibe check on the big idea:
a triad = 3 people + whatever emails exist between them. 3 people = 6 possible
directed edges, so 2^6 = 64 possible patterns. a lot of those are just the same
shape with the people swapped around (isomorphic), so they collapse into 16 shapes.
13 of those are connected (nobody is totally left out). those 13 = triad classes 1-13.
"""
import random
from itertools import permutations, combinations

# the 6 possible edges between slot 0,1,2. position in list = bit number (spec says so)
#   bit0: 0->1   bit1: 0->2   bit2: 1->0   bit3: 1->2   bit4: 2->0   bit5: 2->1
BIT_EDGES = [(0, 1), (0, 2), (1, 0), (1, 2), (2, 0), (2, 1)]

# canonical codes of the 13 connected shapes, sorted. class number = index + 1
CONNECTED_CODES = [3, 6, 7, 10, 11, 15, 21, 23, 25, 27, 30, 31, 63]
# code -> class lookup. disconnected shapes just arent in here
CODE_TO_CLASS = {code: i + 1 for i, code in enumerate(CONNECTED_CODES)}


def config_code(order, edge_set):
    """6-bit number for the triad when we read its people in this specific order.

    order    - tuple (a, b, c): which real node sits in slot 0, 1, 2
    edge_set - set of directed edges (u, v) in the graph
    for each of the 6 possible edges, if it actually exists we flip that bit on.
    """
    code = 0
    for k, (i, j) in enumerate(BIT_EDGES):
        # slot i -> slot j means real nodes order[i] -> order[j]
        if (order[i], order[j]) in edge_set:
            code |= 1 << k          # turn bit k on
    return code


def canonical_code(a, b, c, edge_set):
    """smallest code across all 6 orderings of a,b,c.

    same shape gives different codes depending on who u put in which slot, so we
    always take the minimum. same minimum = same shape. thats the whole trick.
    """
    return min(config_code(p, edge_set) for p in permutations((a, b, c)))


def triad_class(a, b, c, edge_set):
    """class 1-13 for nodes a,b,c, or None if theyre not connected.

    (None = canonical code is 0, 1 or 5 aka no edges / one lonely edge with a
    third node just vibing alone)
    """
    return CODE_TO_CLASS.get(canonical_code(a, b, c, edge_set))


def build_adjacency(nodes, edges):
    """undirected neighbour sets: nbrs[v] = everyone v sent to OR got email from.

    "connected" for triads ignores direction, so we flatten it here.
    """
    nbrs = {v: set() for v in nodes}
    for u, v in edges:
        nbrs[u].add(v)
        nbrs[v].add(u)
    return nbrs


def triad_census(nodes, edges):
    """T4: returns [N1..N13], how many connected triples fall in each class.

    why not just check every C(n,3) triple? way too slow + most arent even connected.
    useful fact: in any connected triple, one node touches the other two.
    so for every node v we look at every PAIR (u, w) of its neighbours - that finds
    every connected triple. to count each one exactly once:
      - open path (u,w not adjacent): only one centre (v), so only v finds it. count it.
      - triangle (u,w adjacent): all 3 nodes find it, so only count when v is the
        smallest of the three.
    """
    edge_set = edges if isinstance(edges, (set, frozenset)) else set(edges)
    nbrs = build_adjacency(nodes, edge_set)
    counts = [0] * 13                         # counts[k-1] = number of class k triads
    for v in nodes:
        # sorted so u < w always, no repeated pairs
        for u, w in combinations(sorted(nbrs[v]), 2):
            if w in nbrs[u]:                  # u,w adjacent -> its a triangle
                if v > u:                     # v isnt the smallest (u < w already)
                    continue                  # skip, smallest node will count it
            cls = triad_class(v, u, w, edge_set)
            counts[cls - 1] += 1              # cls cant be None, the triple is connected
    return counts


def randomize(edges, attempts, seed):
    """T5: double-edge-swap shuffle. returns a NEW edge list, input stays untouched.

    one attempt: grab two random edges (a,b) and (c,d), turn them into (a,d) and (c,b).
    rejected (graph unchanged but attempt still counts) if:
      a == d or c == b          -> would make a self-loop
      (a,d) or (c,b) exists     -> would make a duplicate edge
    why degrees dont change: a and c still send exactly one edge each (out-degree same),
    b and d still receive exactly one each (in-degree same). just rewired who gets what.
    """
    rng = random.Random(seed)                 # own rng so its reproducible from the seed
    edge_list = list(edges)                   # list so we can pick by index
    edge_set = set(edge_list)                 # set so "does edge exist" is fast
    m = len(edge_list)
    if m < 2:
        return edge_list
    for _ in range(attempts):
        i = rng.randrange(m)                  # random edge, uniform
        j = rng.randrange(m)
        a, b = edge_list[i]
        c, d = edge_list[j]
        if a == d or c == b or (a, d) in edge_set or (c, b) in edge_set:
            continue                          # rejected, do nothing
        edge_set.discard((a, b)); edge_set.discard((c, d))   # drop old edges
        edge_set.add((a, d)); edge_set.add((c, b))           # add swapped ones
        edge_list[i] = (a, d)
        edge_list[j] = (c, b)
    return edge_list


def degree_sequences(nodes, edges):
    """(indeg, outdeg) dicts - used to PROVE the swaps kept every nodes degrees."""
    indeg = {v: 0 for v in nodes}
    outdeg = {v: 0 for v in nodes}
    for u, v in edges:
        outdeg[u] += 1
        indeg[v] += 1
    return indeg, outdeg


def z_scores(real_counts, random_counts):
    """T6: Z_k = (N_k(G) - mu_k) / sigma_k for each class k.

    real_counts   - [N1..N13] for the real graph
    random_counts - list of [N1..N13], one per random graph
    mu = mean over the random graphs, sigma = POPULATION std (divide by n, not n-1).
    if sigma is 0 (class never changes in random graphs) we say Z = 0.
    Z > 2 = motif (shows up more than chance), Z < -2 = anti-motif (less than chance).
    returns (z, mu, sigma), each a list of 13.
    """
    n = len(random_counts)
    z, mus, sigmas = [], [], []
    for k in range(13):
        vals = [rc[k] for rc in random_counts]
        mu = sum(vals) / n
        var = sum((x - mu) ** 2 for x in vals) / n      # population variance
        sigma = var ** 0.5
        mus.append(mu); sigmas.append(sigma)
        z.append(0.0 if sigma == 0 else (real_counts[k] - mu) / sigma)
    return z, mus, sigmas
