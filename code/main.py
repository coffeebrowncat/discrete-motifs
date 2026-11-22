"""
main.py - this file runs the whole project

what happens, in order:
load the data -> pick our 2 departments -> count the triads in each ->
make random shuffled copies -> compare real vs random (z-scores) -> draw the chart

group: merub absar khan (24i-0611) and muhammad ibragim (24i-0896)
R = 896 + 611 = 1507  (add up the last 4 digits of both roll numbers)
everything else comes from R:
  pair number     = R mod 190             = 177 -> pair (14, 17) -> top-20[14] and top-20[17]
  random networks = 20 + (R mod 31)       = 39
  swap attempts   = (5 + R mod 6) x edges = 6 x number of edges
  seed            = R                     = 1507
the code also prints all of these when it runs
"""

# argparse lets us pass options from the terminal, csv writes the results table,
# os handles file paths, random is for the shuffling, sys lets us quit with a message
import argparse, csv, os, random, sys
# Counter is a dictionary that starts every count at 0, super handy for tallying
from collections import Counter

# motifs.py is the other file, it has the triad maths. we use it as motifs.something
import motifs

# our roll numbers, R gets worked out from these (only the last 4 digits matter)
ROLL_NUMBERS = ["24i-0896", "24i-0611"]
# where the data folder is: go up one folder from this file (..) then into data
DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")


def load_graph(edge_file, label_file):
    """reads the two data files and cleans the graph (no self loops, no duplicate edges)"""
    # a set can't hold the same thing twice, so duplicate edges disappear automatically
    edges = set()
    # open the file that says who emailed who
    with open(edge_file) as f:
        # go through the file one line at a time
        for line in f:
            # split the line into pieces, "5 12" becomes ["5", "12"]
            parts = line.split()
            # skip empty lines and comment lines (those start with #)
            if len(parts) < 2 or line.startswith("#"):
                continue
            # turn the two pieces into numbers: u emailed v
            u, v = int(parts[0]), int(parts[1])
            # only keep it if the person didn't email themselves (removes self loops)
            if u != v:
                # add the edge u -> v to our set
                edges.add((u, v))
    # dictionary that will say which department each person is in
    dept = {}
    # open the file with the department labels
    with open(label_file) as f:
        # again go through line by line
        for line in f:
            # split the line into pieces
            parts = line.split()
            # only use lines that actually have 2 pieces
            if len(parts) >= 2:
                # person number -> their department number
                dept[int(parts[0])] = int(parts[1])
    # hand both things back to whoever called this function
    return edges, dept


def top20_departments(edges, dept):
    """ranks departments by how many emails stay inside the department (biggest first)

    if two departments tie, the smaller department number goes first
    gives back the top 20 list and the internal edge counts
    """
    # tally of internal edges for each department, starts at 0
    internal = Counter()
    # check every email edge
    for u, v in edges:
        # is the sender and the receiver in the same department?
        if dept[u] == dept[v]:
            # yes, so add 1 to that department's tally
            internal[dept[u]] += 1
    # sort all departments: most internal edges first (the minus flips it), ties by smaller id
    ranked = sorted(set(dept.values()), key=lambda d: (-internal[d], d))
    # keep only the first 20 and also return the tally
    return ranked[:20], internal


def pair_from_number(n):
    """finds the n-th pair (i, j) where 0 <= i < j <= 19, counting from 0 in dictionary order

    (0,1) is number 0, (0,2) is 1, ... (0,19) is 18, (1,2) is 19, ... (18,19) is 189
    """
    # k counts which pair number we are on
    k = 0
    # i is the first number of the pair
    for i in range(20):
        # j is the second number, always bigger than i
        for j in range(i + 1, 20):
            # is this the pair we were looking for?
            if k == n:
                # yes, give it back
                return i, j
            # no, move on to the next pair number
            k += 1


def department_subgraph(edges, dept, d):
    """takes department d only: its people + only the emails between those people"""
    # list of everyone in department d, sorted
    nodes = sorted(v for v, dd in dept.items() if dd == d)
    # same people as a set so checking "is this person in it" is fast
    node_set = set(nodes)
    # keep an email only if BOTH the sender and the receiver are in the department
    sub_edges = {(u, v) for (u, v) in edges if u in node_set and v in node_set}
    # give back the people and their emails
    return nodes, sub_edges


def run(R, edges, dept, out_dir, verify_nx=False):
    # find the top 20 departments and how many internal edges each has
    top20, internal = top20_departments(edges, dept)
    # which pair number is ours (R mod 190)
    pair_no = R % 190
    # turn that number into the pair (i, j)
    i, j = pair_from_number(pair_no)
    # department A is the i-th in the top 20, department B is the j-th
    dA, dB = top20[i], top20[j]
    # how many random networks to make
    n_random = 20 + (R % 31)
    # swap attempts per random network = this factor x number of edges
    factor = 5 + (R % 6)
    # the random seed is just R, so the results are the same every run
    seed = R
    # put all the parameters in one dictionary so we can print them
    params = {"R": R, "pair_number": pair_no, "pair": (i, j),
              "department_A": dA, "department_B": dB, "random_networks": n_random,
              "swap_attempts_factor": factor, "seed": seed}
    print("=== T1: parameters ===")
    # print each parameter on its own line, aligned nicely
    for k, v in params.items():
        print(f"{k:22s} {v}")
    print("top-20 departments (index: dept, internal edges):")
    # print the whole top 20 list in one line
    print("  " + ", ".join(f"{idx}: {d} ({internal[d]})" for idx, d in enumerate(top20)))

    # this will hold the results for both departments
    results = {}
    # do the same steps twice: once for department A, once for B
    for tag, d in (("A", dA), ("B", dB)):
        # get this department's people and emails
        nodes, sub_edges = department_subgraph(edges, dept, d)
        print(f"\n=== T2: department {tag} = {d}: {len(nodes)} nodes, {len(sub_edges)} edges ===")

        # count how many triads of each of the 13 classes are in the REAL data
        real = motifs.triad_census(nodes, sub_edges)
        print("T4 real counts N1..N13:", real)
        # only if we asked for it: double check our counts against networkx
        if verify_nx:
            _check_with_networkx(nodes, sub_edges, real)

        # save every person's in-degree and out-degree before shuffling (to compare after)
        in0, out0 = motifs.degree_sequences(nodes, sub_edges)
        # how many swap attempts each random network gets
        attempts = factor * len(sub_edges)
        # one random number generator for the whole run, started from the seed
        master = random.Random(seed)
        # list that will collect the triad counts of each random network
        rnd_counts = []
        # make n_random random networks
        for _ in range(n_random):
            # shuffle the ORIGINAL edges by swapping (always start from the real graph)
            rnd_edges = motifs.randomize(sub_edges, attempts, master.randrange(2**31))
            # measure the degrees again after the shuffle
            in1, out1 = motifs.degree_sequences(nodes, rnd_edges)
            # crash loudly if anyone's in or out degree changed (it shouldn't)
            assert in1 == in0 and out1 == out0, "degree sequence changed!"
            # crash if we lost or doubled any edge
            assert len(rnd_edges) == len(set(rnd_edges)) == len(sub_edges)
            # crash if a self loop snuck in
            assert all(u != v for u, v in rnd_edges)
            # count the triads in this random network and save it
            rnd_counts.append(motifs.triad_census(nodes, set(rnd_edges)))
        print(f"T5 check passed: in/out-degrees unchanged for all {n_random} random graphs")

        # compare real vs random to get a z-score for each class
        z, mu, sigma = motifs.z_scores(real, rnd_counts)
        # store everything for this department
        results[tag] = dict(dept=d, real=real, mu=mu, sigma=sigma, z=z)
        # print the z-scores rounded to 2 decimals
        print("T6 Z-scores:", [round(x, 2) for x in z])
        # classes with z above 2 are motifs (class numbers start at 1, list index at 0, hence +1)
        print("   motifs     (Z>2):", [k + 1 for k in range(13) if z[k] > 2])
        # classes with z below -2 are anti-motifs
        print("   anti-motifs(Z<-2):", [k + 1 for k in range(13) if z[k] < -2])

    # make the output folder if it isn't there yet
    os.makedirs(out_dir, exist_ok=True)
    # open the results csv file for writing
    with open(os.path.join(out_dir, f"results_R{R}.csv"), "w", newline="") as f:
        # csv writer helps us write rows
        w = csv.writer(f)
        # first row is the column names
        w.writerow(["class", "A_count", "A_mean_random", "A_std_random", "A_Z",
                    "B_count", "B_mean_random", "B_std_random", "B_Z"])
        # one row for each of the 13 classes
        for k in range(13):
            # shortcuts for the two departments' results
            a, b = results["A"], results["B"]
            # write: class number, then A's numbers, then B's numbers (rounded to 3 decimals)
            w.writerow([k + 1, a["real"][k], round(a["mu"][k], 3), round(a["sigma"][k], 3),
                        round(a["z"][k], 3), b["real"][k], round(b["mu"][k], 3),
                        round(b["sigma"][k], 3), round(b["z"][k], 3)])
    # draw and save the bar chart
    plot_chart(R, params, results, os.path.join(out_dir, f"zscores_R{R}.png"))
    # give everything back (not used for much, just nice to have)
    return params, results


def plot_chart(R, params, results, path):
    """draws 2 bars per class (A and B) with dashed lines at +2 and -2, R is in the title"""
    # matplotlib is the drawing library
    import matplotlib
    # "Agg" means draw straight into a file, no pop up window
    matplotlib.use("Agg")
    # pyplot is the part of matplotlib we actually call
    import matplotlib.pyplot as plt
    # numpy for making the list of numbers for the x axis
    import numpy as np
    # x positions for the 13 classes: 1, 2, ... 13
    x = np.arange(1, 14)
    # how wide each bar is
    w = 0.38
    # make an empty chart, 11 wide and 5 tall
    fig, ax = plt.subplots(figsize=(11, 5))
    # department A bars, shifted a bit left so they don't sit on top of B
    ax.bar(x - w / 2, results["A"]["z"], w, label=f"Dept A = {params['department_A']}")
    # department B bars, shifted a bit right
    ax.bar(x + w / 2, results["B"]["z"], w, label=f"Dept B = {params['department_B']}")
    # dashed line at +2 (above this = motif)
    ax.axhline(2, ls="--", color="k", lw=1)
    # dashed line at -2 (below this = anti-motif)
    ax.axhline(-2, ls="--", color="k", lw=1)
    # thin grey line at 0
    ax.axhline(0, color="gray", lw=0.6)
    # put a tick on each class number
    ax.set_xticks(x)
    # label the x axis
    ax.set_xlabel("Triad class (1-13)")
    # label the y axis
    ax.set_ylabel("Z-score vs null model")
    # title has both departments and R (the project says R has to be in the title)
    ax.set_title(f"Triad motif Z-scores, departments {params['department_A']} vs "
                 f"{params['department_B']}  (R = {R})")
    # show the legend box (which colour is which department)
    ax.legend()
    # stop labels getting cut off
    fig.tight_layout()
    # save the chart as a png
    fig.savefig(path, dpi=150)
    # close the chart so it doesn't hog memory
    plt.close(fig)
    print("saved chart:", path)


def _check_with_networkx(nodes, edges, real):
    """just a sanity check (the project allows it): does networkx count the same triads as us?

    networkx numbers its classes in a different order, so we translate first
    """
    # import networkx only here, it's only used for this check
    import networkx as nx
    # build a directed graph with our people and emails
    g = nx.DiGraph(); g.add_nodes_from(nodes); g.add_edges_from(edges)
    # networkx counts all triad types for us
    census = nx.triadic_census(g)
    # translation table: networkx's name for a shape -> our class number
    nx_to_ours = {"021D": 1, "021C": 2, "111U": 3, "021U": 4, "030T": 5, "120U": 6, "111D": 7,
                  "201": 8, "030C": 9, "120C": 10, "120D": 11, "210": 12, "300": 13}
    # list of 13 zeros to fill in our order
    mapped = [0] * 13
    # go through the table and put each networkx count in the right slot
    for name, cls in nx_to_ours.items():
        mapped[cls - 1] = census[name]
    # same counts as ours = MATCH
    print("   networkx check:", "MATCH" if mapped == real else f"MISMATCH {mapped}")


# this part only runs when you do "python main.py" (not when another file imports it)
if __name__ == "__main__":
    # set up the terminal options
    ap = argparse.ArgumentParser()
    # option: give roll numbers from the terminal instead of using the list at the top
    ap.add_argument("--rolls", nargs="*", help="roll numbers, e.g. 24i-0896 24i-0611")
    # option: set R directly (only for testing)
    ap.add_argument("--R", type=int, help="override R directly (testing only)")
    # option: where the data folder is (default is the one we defined at the top)
    ap.add_argument("--data", default=DATA_DIR)
    # option: where to save the results (default is the output folder)
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "output"))
    # option: also run the networkx double check
    ap.add_argument("--check-nx", action="store_true", help="compare T4 with nx.triadic_census")
    # read what was typed in the terminal
    a = ap.parse_args()
    # use roll numbers from the terminal if given, otherwise the ones at the top
    rolls = a.rolls or ROLL_NUMBERS
    # if R was given directly, just use it
    if a.R is not None:
        R = a.R
    # otherwise work out R from the roll numbers
    elif rolls:
        # take the last 4 digits of each roll number, turn into a number, add them all up
        R = sum(int(r.strip()[-4:]) for r in rolls)
    # no roll numbers and no R = we can't continue
    else:
        sys.exit("set ROLL_NUMBERS at the top of main.py or pass --rolls")
    # load and clean the data
    edges, dept = load_graph(os.path.join(a.data, "email-Eu-core.txt"),
                             os.path.join(a.data, "email-Eu-core-department-labels.txt"))
    # quick summary of what we loaded
    print(f"loaded simple graph: {len(set(dept.values()))} depts, {len(dept)} nodes, {len(edges)} edges")
    # run everything
    run(R, edges, dept, a.out, verify_nx=a.check_nx)
