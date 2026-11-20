"""
main.py - runs the whole project: load data -> pick departments -> count triads ->
shuffle graphs -> z-scores -> chart.

group: 24i-0896, 24i-0611
R = 896 + 611 = 1507  (sum of last 4 digits of each roll number)
derived params (all come from R):
  pair number        = R mod 190        = 177  -> pair (14, 17) -> top-20[14], top-20[17]
  random networks    = 20 + (R mod 31)  = 39
  swap attempts      = (5 + R mod 6)*|E| = 6 x number of edges
  seed               = R                = 1507
the code prints all of these when it runs too.
"""
import argparse, csv, os, random, sys
from collections import Counter

import motifs

ROLL_NUMBERS = ["24i-0896", "24i-0611"]       # R gets computed from these
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_graph(edge_file, label_file):
    """T1 part 1: read the files and make the graph simple (no self loops, no dupes)."""
    edges = set()                             # a set kills duplicate edges for free
    with open(edge_file) as f:
        for line in f:
            parts = line.split()
            if len(parts) < 2 or line.startswith("#"):
                continue
            u, v = int(parts[0]), int(parts[1])
            if u != v:                        # drop self loops
                edges.add((u, v))
    dept = {}                                 # node -> department id
    with open(label_file) as f:
        for line in f:
            parts = line.split()
            if len(parts) >= 2:
                dept[int(parts[0])] = int(parts[1])
    return edges, dept


def top20_departments(edges, dept):
    """rank departments by how many edges are fully inside them (biggest first).

    ties go to the smaller department id. returns (top 20 list, internal edge counts).
    """
    internal = Counter()
    for u, v in edges:
        if dept[u] == dept[v]:                # both ends in the same department
            internal[dept[u]] += 1
    ranked = sorted(set(dept.values()), key=lambda d: (-internal[d], d))
    return ranked[:20], internal


def pair_from_number(n):
    """n-th pair (i,j) with 0<=i<j<=19 in lexicographic order, counting from 0.

    (0,1)=0, (0,2)=1, ... (0,19)=18, (1,2)=19, ... (18,19)=189
    """
    k = 0
    for i in range(20):
        for j in range(i + 1, 20):
            if k == n:
                return i, j
            k += 1


def department_subgraph(edges, dept, d):
    """T2: induced subgraph - all members of department d + only edges between them."""
    nodes = sorted(v for v, dd in dept.items() if dd == d)
    node_set = set(nodes)
    sub_edges = {(u, v) for (u, v) in edges if u in node_set and v in node_set}
    return nodes, sub_edges


def run(R, edges, dept, out_dir, verify_nx=False):
    # ---- T1: work out all the parameters from R ----
    top20, internal = top20_departments(edges, dept)
    pair_no = R % 190
    i, j = pair_from_number(pair_no)
    dA, dB = top20[i], top20[j]
    n_random = 20 + (R % 31)
    factor = 5 + (R % 6)
    seed = R
    params = {"R": R, "pair_number": pair_no, "pair": (i, j),
              "department_A": dA, "department_B": dB, "random_networks": n_random,
              "swap_attempts_factor": factor, "seed": seed}
    print("=== T1: parameters ===")
    for k, v in params.items():
        print(f"{k:22s} {v}")
    print("top-20 departments (index: dept, internal edges):")
    print("  " + ", ".join(f"{idx}: {d} ({internal[d]})" for idx, d in enumerate(top20)))

    results = {}
    for tag, d in (("A", dA), ("B", dB)):
        # ---- T2: build the department subgraph ----
        nodes, sub_edges = department_subgraph(edges, dept, d)
        print(f"\n=== T2: department {tag} = {d}: {len(nodes)} nodes, {len(sub_edges)} edges ===")

        # ---- T4: count the 13 triad classes in the REAL subgraph ----
        real = motifs.triad_census(nodes, sub_edges)
        print("T4 real counts N1..N13:", real)
        if verify_nx:
            _check_with_networkx(nodes, sub_edges, real)

        # ---- T5: make random graphs with the same degrees ----
        in0, out0 = motifs.degree_sequences(nodes, sub_edges)
        attempts = factor * len(sub_edges)    # swap attempts per random graph
        master = random.Random(seed)          # one rng -> whole run reproducible from R
        rnd_counts = []
        for _ in range(n_random):
            # each random graph starts from the ORIGINAL edges (spec rule)
            rnd_edges = motifs.randomize(sub_edges, attempts, master.randrange(2**31))
            in1, out1 = motifs.degree_sequences(nodes, rnd_edges)
            assert in1 == in0 and out1 == out0, "degree sequence changed!"   # the T5 check
            assert len(rnd_edges) == len(set(rnd_edges)) == len(sub_edges)   # no dupes lost
            assert all(u != v for u, v in rnd_edges)                         # no self loops
            rnd_counts.append(motifs.triad_census(nodes, set(rnd_edges)))
        print(f"T5 check passed: in/out-degrees unchanged for all {n_random} random graphs")

        # ---- T6: z-scores (real vs random) ----
        z, mu, sigma = motifs.z_scores(real, rnd_counts)
        results[tag] = dict(dept=d, real=real, mu=mu, sigma=sigma, z=z)
        print("T6 Z-scores:", [round(x, 2) for x in z])
        print("   motifs     (Z>2):", [k + 1 for k in range(13) if z[k] > 2])
        print("   anti-motifs(Z<-2):", [k + 1 for k in range(13) if z[k] < -2])

    # ---- save the table as csv ----
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"results_R{R}.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["class", "A_count", "A_mean_random", "A_std_random", "A_Z",
                    "B_count", "B_mean_random", "B_std_random", "B_Z"])
        for k in range(13):
            a, b = results["A"], results["B"]
            w.writerow([k + 1, a["real"][k], round(a["mu"][k], 3), round(a["sigma"][k], 3),
                        round(a["z"][k], 3), b["real"][k], round(b["mu"][k], 3),
                        round(b["sigma"][k], 3), round(b["z"][k], 3)])
    # ---- T7: the grouped bar chart ----
    plot_chart(R, params, results, os.path.join(out_dir, f"zscores_R{R}.png"))
    return params, results


def plot_chart(R, params, results, path):
    """T7: two bars per class (A and B), dashed lines at +-2, R in the title."""
    import matplotlib
    matplotlib.use("Agg")                     # draw to a file, no window needed
    import matplotlib.pyplot as plt
    import numpy as np
    x = np.arange(1, 14)                      # classes 1..13
    w = 0.38                                  # bar width
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(x - w / 2, results["A"]["z"], w, label=f"Dept A = {params['department_A']}")
    ax.bar(x + w / 2, results["B"]["z"], w, label=f"Dept B = {params['department_B']}")
    ax.axhline(2, ls="--", color="k", lw=1)   # motif threshold
    ax.axhline(-2, ls="--", color="k", lw=1)  # anti-motif threshold
    ax.axhline(0, color="gray", lw=0.6)
    ax.set_xticks(x)
    ax.set_xlabel("Triad class (1-13)")
    ax.set_ylabel("Z-score vs null model")
    ax.set_title(f"Triad motif Z-scores, departments {params['department_A']} vs "
                 f"{params['department_B']}  (R = {R})")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print("saved chart:", path)


def _check_with_networkx(nodes, edges, real):
    """sanity check ONLY (spec allows this for T4). networkx orders its classes
    differently so we map its names to our class numbers first."""
    import networkx as nx
    g = nx.DiGraph(); g.add_nodes_from(nodes); g.add_edges_from(edges)
    census = nx.triadic_census(g)
    nx_to_ours = {"021D": 1, "021C": 2, "111U": 3, "021U": 4, "030T": 5, "120U": 6, "111D": 7,
                  "201": 8, "030C": 9, "120C": 10, "120D": 11, "210": 12, "300": 13}
    mapped = [0] * 13
    for name, cls in nx_to_ours.items():
        mapped[cls - 1] = census[name]
    print("   networkx check:", "MATCH" if mapped == real else f"MISMATCH {mapped}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--rolls", nargs="*", help="roll numbers, e.g. 24i-0896 24i-0611")
    ap.add_argument("--R", type=int, help="override R directly (testing only)")
    ap.add_argument("--data", default=DATA_DIR)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "output"))
    ap.add_argument("--check-nx", action="store_true", help="compare T4 with nx.triadic_census")
    a = ap.parse_args()
    rolls = a.rolls or ROLL_NUMBERS
    if a.R is not None:
        R = a.R
    elif rolls:
        R = sum(int(r.strip()[-4:]) for r in rolls)   # last 4 digits of each roll no.
    else:
        sys.exit("set ROLL_NUMBERS at the top of main.py or pass --rolls")
    edges, dept = load_graph(os.path.join(a.data, "email-Eu-core.txt"),
                             os.path.join(a.data, "email-Eu-core-department-labels.txt"))
    print(f"loaded simple graph: {len(set(dept.values()))} depts, {len(dept)} nodes, {len(edges)} edges")
    run(R, edges, dept, a.out, verify_nx=a.check_nx)
