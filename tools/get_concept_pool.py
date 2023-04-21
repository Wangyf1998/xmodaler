
import os
import json
import argparse
from random import shuffle, seed
import string
import itertools

import numpy as np
import torch

import pickle as pkl
import nltk
from collections import Counter, defaultdict
import sng_parser
from nltk.corpus import stopwords


def get_concept(list, stopwords):
    concept_pool = defaultdict(lambda: defaultdict(Counter))             # counter方法的特殊性，update会更新计数而不是替代内容
    # concept_pool = defaultdict(Counter)
    concept_dict = defaultdict(lambda: defaultdict(Counter))
    count_thr = 5
    for imgs in list:
        art_style = imgs['art_style']
        for img in imgs['utterance_result']:
            emotion_label = img['emotion_label']
            spell = img['utterance_spelled']
            graph = sng_parser.parse(spell)
            # object = {i: [] for i in range(9)}
            positive_set = {0, 2, 3, 1}
            negative_set = {4, 6, 7, 5}
            for entity in graph['entities']:             # 得到场景图中的head，并将其写入对应的positive/negative字典中
                word = entity['lemma_head'].split(' ')   # lemma head有可能是多个词组成的词组，将其split并分别送入list中
                for w in word:
                    if w not in stopwords:
                        # object[emotion_label].append(w)
                        if emotion_label in positive_set:
                            concept_pool[art_style][0].update([w])
                        elif emotion_label in negative_set:
                            concept_pool[art_style][1].update([w])
    for style in concept_pool:
        concept_pool[style] = {k: v.most_common() for k, v in concept_pool[style].items()}
        # concept_dict = {key: [words[0] for words in list] for key, list in concept_pool[style].items()}
        # 把counter类型的词典转化为普通词典
    return concept_pool
        # concept_pool是counter类型的词典，concept_dict是普通类型的词典


def main(params):
    if not os.path.exists(params["output_dir"]):
        os.makedirs(params["output_dir"])

    new_words = ['painting', 'painter', 'picture', 'look', 'day', 'colours', 'sense', 'color', 'colour', 'colours',
                 'colour', 'background', 'I', 'colouring', 'artwork', 'beginning', 'end', 'ending', 'begin',
                 'atmosphere', 'image', 'activity', 'something', 'nothing', 'anything', 'emotion', 'feeling',
                 'size', 'scene', 'use', 'work', 'lack', 'detail', 'place', 'landscape', 'environment', 'posture',
                 'distance', 'one', 'situation', 'right', 'what', 'whatever', 'wherever', 'however', 'therefore']
    stopword = stopwords.words('english')
    stopword.extend(new_words)

    imgs = json.load(open(params['input_json'], 'r'))
    concept_pool = get_concept(imgs, stopword)
    # concept_pool：counter类型，concept_dict，dict类型，依照出现次数排序
    json.dump(concept_pool, open(os.path.join(params['output_dir'], "concept_pool.json"), "w"))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()

    # input json
    parser.add_argument('--input_json', default="/home/wyf/artemis_fullcombined.json", help='input json file to process into hdf5')
    parser.add_argument('--output_dir', default="/home/wyf/open_source_dataset/artemis_dataset/4.19/", help='output directory')


    # options


    args = parser.parse_args()
    params = vars(args)  # convert to ordinary dict
    print('parsed input parameters:')
    print(json.dumps(params, indent=2))
    main(params)