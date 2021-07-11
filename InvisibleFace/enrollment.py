#!/usr/bin/env python
import sys
import numpy as np
import phe.paillier as paillier
from gmpy2 import mpz
import argparse
import os
import time
import random
from itertools import repeat

# parse the args
parser = argparse.ArgumentParser(description='Enrollment in InvisibleFace')
parser.add_argument('--K', default=128, type=int)
parser.add_argument('--file', type=str)
parser.add_argument('--folder', type=str, help='use to store the keys and encrypted features')
parser.add_argument('--public_key', default='/face/irving/eval_feats/invisibleface/publickey', type=str, help='path to the public key')
parser.add_argument('--key_size', default=2048, type=int)
args = parser.parse_args() 


def load_features(feature_file):
    """
    load the features. 
    index (0,1,2,...), features
    """
    features = []
    with open(feature_file, 'r') as f:
        lines = f.readlines()
    for line in lines:
        parts = line.strip().split(' ')
        feature = [float(e) for e in parts[1:]]
        feature = feature/np.linalg.norm(feature)
        features.append(feature)
    return features

def enroll(feature, K, L, M, public_key):
    """
    enroll a feature
    """
    start = time.time()
    u_list = [int(e) for e in np.random.rand(K)*(2*L)]
    v_list = [int(e) for e in np.random.rand(K)*(2*L)]
    s_list = [1 if v%2==0 else -1 for v in v_list]

    # generate c_f
    n = len(feature)
    scale = [s_list[i] * np.e**((u_list[i]-L)/M)  for i in range(K)]
    b_f = [x for item in  scale for x in repeat(item, n//K)] * feature
    W_f = np.linalg.norm(b_f)
    c_f = b_f/W_f

    # encrypt
    base = [(4*L)**(K-1-i) for i in range(K)]
    w_f = int((np.log(W_f) + L/M)/(2*L/M) * 2**15 * L**8)
    C_f = np.dot(u_list, base) + \
            np.dot(v_list, base) * (4*L)**(K) + \
              w_f * (4*L)**(2*K)
    duration1 = time.time() - start

    start = time.time()
    C_tilde_f = public_key.encrypt(C_f)
    duration2 = time.time() - start 
    return [c_f, C_tilde_f], [duration1, duration2]

def main(K, L, M, feature_file, folder, public_key):
    """
    enrollment in invisibleface
    """
    print('Pailllier init...')
    publickey = np.load(public_key, allow_pickle=True)[0]  # Optional param.: bit size (default = 2048)

    print('loading features...')
    features = load_features(feature_file)
    n, dim = len(features), len(features[0])
    # L_list = [i for i in range(0, 2*L)]

    print('Encrypting features...')
    start = time.time()
    enroll_duration = []
    paillier_duration = []    
    for i, feature in enumerate(features):        
        result, durations = enroll(feature, K, L, M, publickey)
        np.save('{}/{}.npy'.format(folder, i), result)
        # measure time
        enroll_duration.append(durations[0])
        paillier_duration.append(durations[1])
        if i % 1000 == 0:
            print('{}/{}'.format(i, n))
        if i > 100:
            break
    duration = time.time() - start
    print('total duration {}, permutation duration {}, paillier duration {}, encrypted {} features'.format(duration, sum(enroll_duration), sum(paillier_duration), n))


if __name__ == '__main__':
    L = int(np.ceil(2**(args.key_size/(2*args.K+9)-2) - 1))
    M = L/128
    security_level = 2*args.K + args.K*np.log2(L)

    print('K: {}   L: {}   M: {}'.format(args.K, L, M))
    print('the security level is: {}'.format(security_level))
    assert L > 1
    if not os.path.exists(args.folder):
        os.makedirs(args.folder)

    main(args.K, L, M, args.file, args.folder, '{}_{}.npy'.format(args.public_key, args.key_size))

