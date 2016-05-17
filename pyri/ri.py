"""
Random Indexing
re-implementation April 2016
"""
import math
from collections import Counter
from enum import Enum
import numpy as np
import pyri.util as util


def words(line):
    """
    Make a generator from a line, yielding each whitespace delimited word.
    """
    yield from iter(line.strip().split())


class Direction(Enum):
    """
    An enum encoding direction: left, or right.
    """
    left = 0
    right = 1


class WordSpace(object):
    """
    A WordSpace where word usage statistics are aggregated, and parameters
    specfied. Saves raw collocation data that is distilled into a dense
    matrix if the collocation is "dense" enougn.
    """
    def __init__(self, theta, mincount, projection):
        self.projection = projection
        self.mincount = mincount
        self.theta = theta
        self.total = 0              # Total number of tokens
        self.collocation = {}       # focus o=> (context counter)
        self.wordcount = Counter()  # focus counter
        self.vecs = {}              # Dense vectors

# I'd prefer the following, as it is semantically simpler.
# Following the structure of the old code, the other variant should be used.
#    def add_count(self, focus, context):
#        if focus not in self.collocation:
#            self.collocation[focus] = Counter()
#        self.collocation[focus].update(context)
#        self.wordcount[focus] += 1
#        self.total += 1

    def add_counts(self, focus, contexts):
        """
        Add collocation counts to the wordspace.
        """
        self.wordcount[focus] += 1
        self.total += 1
        if focus not in self.collocation:
            self.collocation[focus] = Counter()
        for context in contexts:
            self.collocation[focus][(Direction.left, context)] += \
                self.get_weight(context)
            self.collocation[context][(Direction.right, focus)] += \
                self.get_weight(focus)

    def get_weight(self, word):
        """
        Online weight scheme as defined in:
        Sahlgren et al. (2016) The Gavagai Living Lexicon, LREC
        """
        return math.exp(-self.theta*(self.wordcount[word] /
                                     self.get_uniq()))

    def get_uniq(self):
        """
        Get the number of unique tokens this wordspace has seen.
        """
        return len(self.wordcount)

    def distill(self):
        """
        Distill the raw collocation into distributional vectors using the
        projection function.
        """
        for focus, counts in self.collocation.items():
            if len(self.collocation[focus]) > self.mincount:
                for context, weight in counts:
                    self.vecs[focus] += self.projection(context) * weight
                del self.collocation[focus]


def dsm(infile, size, wordspace):
    """
    Add the contents of infile to the wordspace,
    with contexts windows of size "size".
    """
    with open(infile, 'r') as handle:
        for line in handle:
            for (focus, left_context) in util.left_windows(words(line), size):
                wordspace.add_counts(focus, left_context)
    return wordspace


def prune_high_variance(row_vecs, nrstd):
    """
    Remove columns with high variance: the columns whose
    variance deviates more than nrstd standard deviations
    from the mean (of all column variances).
    """
    varvec = np.var(row_vecs, 0)
    varmean = np.mean(varvec)
    varstd = np.std(varvec)
    return row_vecs * (np.absolute(varvec - varmean) < varstd * nrstd)


def prune_low_variance(row_vecs, nrstd):
    """
    Remove columns with low variance: the columns whose
    variance deviates less than nrstd standard deviations
    from the mean (of all column variances).
    """
    varvec = np.var(row_vecs, 0)
    varmean = np.mean(varvec)
    varstd = np.std(varvec)
    return row_vecs * (np.absolute(varvec - varmean) > varstd * nrstd)

"""
def update_vecs_ngrams(wrdlst,win,wordtokens,wordtypes):
    global distvecs
    global worddict
    localtoken = 0
    ind = 0
    stop = len(wrdlst)
    for w in wrdlst:
        localtoken += 1
        wordtypes += check_reps(w,wordtypes)
        wind = worddict[w][0]
        wvec = distvecs[wind]
        wri = rivecs[wind]
        worddict[w][1] += 1
        lind = 1
        while (lind < win+1) and ((ind+lind) < stop):
            c = wrdlst[ind+lind]
            wordtypes += check_reps(c,wordtypes)
            cind = worddict[c][0]
            cvec = distvecs[cind]
            np.add.at(wvec,rivecs[cind][:,0]+1,rivecs[cind][:,1]*weight_func(worddict[c][1],wordtypes))
            np.add.at(cvec,rivecs[wind][:,0]-1,rivecs[wind][:,1]*weight_func(worddict[w][1],wordtypes))
            lind += 1
        ind += 1
    return localtoken, wordtypes

# TODO
# def make_very_sparse_index():

####################################
# Vector operations
####################################


# remove dimensions with low variance

def isvd(upper,lower):
    global distvecs
    tmpmat = np.asmatrix(distvecs)
    u, s, v_t = sp.linalg.svds(tmpmat, k=upper, which='LM')
    dimred = u * s
    return dimred[:,lower:]

####################################
# Similarity
####################################

def sim(word1,word2):
    global worddict
    global distvecs
    return 1-st.distance.cosine(distvecs[worddict[word1][0]],distvecs[worddict[word2][0]])

def nns(word, num):
    global distvecs
    global worddict
    matrix = np.asmatrix(distvecs)
    v = distvecs[worddict[word][0]].reshape(1, -1)
    nns = st.distance.cdist(matrix, v, 'cosine').reshape(-1)
    indices = [i for i in sorted(enumerate(nns), key=lambda x:x[1])]
    cnt = 1
    while cnt <= num:
        ele = [key for (key,value) in worddict.items() if value[0] == indices[cnt][0]]
        print(ele[0] + ' ' + str(1-indices[cnt][1]))
        cnt += 1

####################################
# Evaluation
####################################

def similarity_test(testfile,verb=True):
    global worddict
    global distvecs
    inp = open(testfile,"r")
    gold = {}
    model = {}
    cnt = 1
    for line in inp.readlines():
        word1, word2, sim = line.split()
        gold[cnt] = sim
        if (word1 in worddict) and (word2 in worddict):
            model[cnt] = 1-sp.distance.cosine(distvecs[worddict[word1][0]], distvecs[worddict[word2][0]])
        else:
            model[cnt] = 0
        cnt += 1
    inp.close()
    res = st.spearmanr(list(gold.values()),list(model.values()))
    if verb:
        print("Spearman rank correlation (coefficient, p-value): " + ", ".join([str(x) for x in res]))
    else:
        return res[0]

def vocabulary_test(testfile,verb=True):
    global worddict
    global distvecs
    inp = open(testfile,"r")
    corr = 0
    tot = 0
    unknown_target = []
    unknown_answer = []
    incorrect = []
    for line in inp.readlines():
        linelist = line.split()
        target = linelist[0]
        winner = ["",0]
        tot += 1
        if target in worddict:
            for a in linelist[1:]:
                if a in worddict:
                    sim = 1-sp.distance.cosine(distvecs[worddict[target][0]],distvecs[worddict[a][0]])
                    if sim > winner[1]:
                        winner = [a,sim]
                else:
                    if a is linelist[1]:
                        unknown_answer.append(a)
            if linelist[1] == winner[0]:
                corr += 1
            else:
                incorrect.append(target)
        else:
            unknown_target.append(target)
    inp.close()
    if verb:
        print("TOEFL synonym score: " + str(float(corr)/float(tot)))
        print("Incorrect: " + str(incorrect))
        print("Unknown targets: " + str(unknown_target))
        print("Unknown answers: " + str(unknown_answer))
    else:
        return float(corr)/float(tot)
=======
def weightFunc(freq,words,theta):
    return math.exp(-theta*(freq/words))
"""