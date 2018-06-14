#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import numpy as np
import networkx as nx
import matplotlib.pyplot as plt
from scipy.spatial import distance
from scipy import interpolate
from sklearn.decomposition import KernelPCA
from sklearn.manifold import Isomap
import pickle

exec(open("./recovery.py").read())
exec(open("./conbshapecontext.py").read())
exec(open("./matchingnetwork.py").read())
exec(open("./stroke_correspond.py").read())

