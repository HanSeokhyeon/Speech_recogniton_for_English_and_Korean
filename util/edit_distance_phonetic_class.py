import editdistance as ed
import operator

INSERT = 'insert'
DELETE = 'delete'
EQUAL = 'equal'
REPLACE = 'replace'

phonemes = ["b", "bcl", "d", "dcl", "g", "gcl", "p", "pcl", "t", "tcl",
                "k", "kcl", "dx", "q", "jh", "ch", "s", "sh", "z", "zh",
                "f", "th", "v", "dh", "m", "n", "ng", "em", "en", "eng",
                "nx", "l", "r", "w", "y", "hh", "hv", "el", "iy", "ih",
                "eh", "ey", "ae", "aa", "aw", "ay", "ah", "ao", "oy", "ow",
                "uh", "uw", "ux", "er", "ax", "ix", "axr", "ax-h", "pau", "epi", "h#"]

phonemes2index = {k: (v+2) for v, k in enumerate(phonemes)}
index2phonemes = {(v+2): k for v, k in enumerate(phonemes)}

phoneme_reduce_mapping = {"b": "b", "bcl": "h#", "d": "d", "dcl": "h#", "g": "g",
                          "gcl": "h#", "p": "p", "pcl": "h#", "t": "t", "tcl": "h#",
                          "k": "k", "kcl": "h#", "dx": "dx", "q": "q", "jh": "jh",
                          "ch": "ch", "s": "s", "sh": "sh", "z": "z", "zh": "sh",
                          "f": "f", "th": "th", "v": "v", "dh": "dh", "m": "m",
                          "n": "n", "ng": "ng", "em": "m", "en": "n", "eng": "ng",
                          "nx": "n", "l": "l", "r": "r", "w": "w", "y": "y",
                          "hh": "hh", "hv": "hh", "el": "l", "iy": "iy", "ih": "ih",
                          "eh": "eh", "ey": "ey", "ae": "ae", "aa": "aa", "aw": "aw",
                          "ay": "ay", "ah": "ah", "ao": "aa", "oy": "oy", "ow": "ow",
                          "uh": "uh", "uw": "uw", "ux": "uw", "er": "er", "ax": "ah",
                          "ix": "ih", "axr": "er", "ax-h": "ah", "pau": "h#", "epi": "h#",
                          "h#": "h#"}

reduce_phonemes = set([phoneme_reduce_mapping[ch] for ch in phonemes])
reduce_phonemes.remove('q')
reduce_phonemes2index = {ch: phonemes2index[ch] for ch in reduce_phonemes}
index2reduce_phonemes = {phonemes2index[ch]: ch for ch in reduce_phonemes}


def lowest_cost_action(ic, dc, sc, cost):
    """Given the following values, choose the action (insertion, deletion,
    or substitution), that results in the lowest cost (ties are broken using
    the 'match' score).  This is used within the dynamic programming algorithm.
    * ic - insertion cost
    * dc - deletion cost
    * sc - substitution cost
    * im - insertion match (score)
    * dm - deletion match (score)
    * sm - substitution match (score)
    """
    best_action = None
    min_cost = min(ic, dc, sc)
    if min_cost == sc and cost == 0:
        best_action = EQUAL
    elif min_cost == sc and cost == 1:
        best_action = REPLACE
    elif min_cost == ic:
        best_action = INSERT
    elif min_cost == dc:
        best_action = DELETE
    return best_action


def edit_distance(seq1, seq2, action_function=lowest_cost_action, test=operator.eq):
    """Computes the edit distance between the two given sequences.
    This uses the relatively fast method that only constructs
    two columns of the 2d array for edits.  This function actually uses four columns
    because we track the number of matches too.
    """
    m = len(seq1)
    n = len(seq2)
    # Special, easy cases:
    if seq1 == seq2:
        return 0, n
    if m == 0:
        return n, 0
    if n == 0:
        return m, 0
    v0 = [0] * (n + 1)     # The two 'error' columns
    v1 = [0] * (n + 1)
    for i in range(1, n + 1):
        v0[i] = i
    for i in range(1, m + 1):
        v1[0] = i
        for j in range(1, n + 1):
            cost = 0 if test(seq1[i - 1], seq2[j - 1]) else 1
            # The costs
            ins_cost = v1[j - 1] + 1
            del_cost = v0[j] + 1
            sub_cost = v0[j - 1] + cost

            action = action_function(ins_cost, del_cost, sub_cost, cost)

            if action in [EQUAL, REPLACE]:
                v1[j] = sub_cost
            elif action == INSERT:
                v1[j] = ins_cost
            elif action == DELETE:
                v1[j] = del_cost
            else:
                raise Exception('Invalid dynamic programming option returned!')
                # Copy the columns over
        for k in range(0, n + 1):
            v0[k] = v1[k]
    return v1[n]


def edit_distance_by_phoneme(seq1, seq2, action_function=lowest_cost_action, test=operator.eq):
    """Computes the edit distance between the two given sequences.
    This uses the relatively fast method that only constructs
    two columns of the 2d array for edits.  This function actually uses four columns
    because we track the number of matches too.
    """
    def get_class(idx):
        broad_class_shorter = [[32, 34, 36, 33, 35, 37, 21],
                               [22, 23],
                               [25, 26, 24, 29, 31, 28, 30],
                               [14, 15, 16, 17, 27],
                               [18, 19, 20],
                               [0, 1, 2, 8, 3, 7, 11, 9, 4, 10, 12, 6, 5, 13],
                               [38]]

        for c, line in enumerate(broad_class_shorter):
            if idx-2 in line:
                return c

    m = len(seq1)
    n = len(seq2)
    # Special, easy cases:
    if seq1 == seq2:
        return 0, n
    if m == 0:
        return n, 0
    if n == 0:
        return m, 0
    v0 = [0] * (n + 1)     # The two 'error' columns
    v1 = [0] * (n + 1)
    p0 = [[0]*7 for _ in range(n+1)]
    p1 = [[0]*7 for _ in range(n+1)]

    for i in range(1, n + 1):
        v0[i] = i
        p0[get_class(seq2)] += 1

    for i in range(1, m + 1):
        v1[0] = i
        for j in range(1, n + 1):
            cost = 0 if test(seq1[i - 1], seq2[j - 1]) else 1
            # The costs
            ins_cost = v1[j - 1] + 1
            del_cost = v0[j] + 1
            sub_cost = v0[j - 1] + cost

            action = action_function(ins_cost, del_cost, sub_cost, cost)

            if action in [EQUAL, REPLACE]:
                v1[j] = sub_cost
            elif action == INSERT:
                v1[j] = ins_cost
            elif action == DELETE:
                v1[j] = del_cost
            else:
                raise Exception('Invalid dynamic programming option returned!')
                # Copy the columns over
        for k in range(0, n + 1):
            v0[k] = v1[k]
    return v1[n]


if __name__ == '__main__':
    pred = [10, 2, 23, 8, 15, 0]
    true = [1, 2, 3, 4, 5]
    # print(ed.eval(pred, true)/len(true))
    # print(edit_distance(pred, true)/len(true))
    print(edit_distance_by_phoneme(pred, true)/len(true))
