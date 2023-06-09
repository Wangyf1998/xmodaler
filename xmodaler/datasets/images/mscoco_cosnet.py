# Copyright 2022 JD.com, Inc., JD AI
"""
@author: Yehao Li
@contact: yehaoli.sysu@gmail.com
"""
import os
import copy
import torch
from torch import nn
import pickle
import random
from tqdm import tqdm
import numpy as np
from xmodaler.config import configurable
from xmodaler.config import kfg
from xmodaler.functional import read_np, dict_as_tensor, boxes_to_locfeats
from .mscoco import MSCoCoDataset
from ..build import DATASETS_REGISTRY
import itertools

__all__ = ["MSCoCoCOSNetDataset"]

@DATASETS_REGISTRY.register()
class MSCoCoCOSNetDataset(MSCoCoDataset):
    @configurable
    def __init__(
        self,
        stage: str,
        anno_file: str,
        seq_per_img: int,
        max_feat_num: int,
        max_seq_len: int,
        obj_classes: int,
        feats_folder: str,
        relation_file: str,
        gv_feat_file: str,
        attribute_file: str,
        sample_prob: float,
    ):
        super(MSCoCoCOSNetDataset, self).__init__(
            stage,
            anno_file,
            seq_per_img, 
            max_feat_num,
            max_seq_len,
            feats_folder,
            relation_file,
            gv_feat_file,
            attribute_file
        )
        self.obj_classes = obj_classes
        self.sample_prob = sample_prob

    @classmethod
    def from_config(cls, cfg, stage: str = "train"):
        # ann_files = {
        #     "train": os.path.join(cfg.DATALOADER.ANNO_FOLDER, "artemis_caption_anno_train.pkl"),
        #     "val": os.path.join(cfg.DATALOADER.ANNO_FOLDER, "artemis_caption_anno_val.pkl"),
        #     "test": os.path.join(cfg.DATALOADER.ANNO_FOLDER, "artemis_caption_anno_test.pkl")
        # }
        ann_files = {
            "train": os.path.join(cfg.DATALOADER.ANNO_FOLDER, "artemis_caption_anno_train.pkl"),
            "val": os.path.join(cfg.DATALOADER.ANNO_FOLDER, "artemis_caption_anno_val.pkl"),
            "test": os.path.join(cfg.DATALOADER.ANNO_FOLDER, "artemis_caption_anno_test.pkl")
        }
        ret = {
            "stage": stage,
            "anno_file": ann_files[stage],
            "seq_per_img": cfg.DATALOADER.SEQ_PER_SAMPLE,
            "max_feat_num": cfg.DATALOADER.MAX_FEAT_NUM,
            "feats_folder": cfg.DATALOADER.FEATS_FOLDER,
            "relation_file": cfg.DATALOADER.RELATION_FILE,
            "gv_feat_file": cfg.DATALOADER.GV_FEAT_FILE,
            "attribute_file": cfg.DATALOADER.ATTRIBUTE_FILE,
            "max_seq_len": cfg.MODEL.MAX_SEQ_LEN,
            "obj_classes": cfg.MODEL.COSNET.NUM_CLASSES,
            "sample_prob": cfg.DATALOADER.SAMPLE_PROB,
        }
        return ret

    # def sampling(self, semantics_ids_arr, semantics_labels_arr, semantics_miss_labels_arr):
    #     for i in range(len(semantics_ids_arr)):
    #         semantics_ids = semantics_ids_arr[i]
    #         semantics_labels = semantics_labels_arr[i]
    #         semantics_miss_labels = semantics_miss_labels_arr[i]
    #
    #         num_classes = len(semantics_miss_labels) - 1
    #         gt_labels1 = list(np.where(semantics_miss_labels > 0)[0])
    #         gt_labels2 = list(semantics_ids[semantics_labels != num_classes])
    #         gt_labels = set(gt_labels1 + gt_labels2)
    #
    #         for j in range(len(semantics_ids)):
    #             if random.random() < self.sample_prob:
    #                 ori_semantics_id = semantics_ids_arr[i][j]
    #                 rnd_idx = np.random.randint(num_classes)
    #                 semantics_ids_arr[i][j] = rnd_idx
    #
    #                 if rnd_idx in gt_labels:
    #                     semantics_labels_arr[i][j] = rnd_idx
    #                     semantics_miss_labels_arr[i][ori_semantics_id] = 1
    #                     semantics_miss_labels_arr[i][rnd_idx] = 0
    #                 else:
    #                     semantics_labels_arr[i][j] = num_classes
    #                     if ori_semantics_id in gt_labels:
    #                        semantics_miss_labels_arr[i][ori_semantics_id] = 1
    #
    #     return semantics_ids_arr, semantics_labels_arr, semantics_miss_labels_arr

    def __call__(self, dataset_dict):
        dataset_dict = copy.deepcopy(dataset_dict)
        image_id = dataset_dict['image_id']

        def get_pool(datasetdict):
            art_style = datasetdict['art_style']
            if art_style in {'Realism', 'Impressionism'}:
                art = '0'
            elif art_style in {'Romanticism', 'Baroque', 'Color_Field_Painting', 'Art_Nouveau_Modern'}:
                art = '1'
            elif art_style in {'Post_Impressionism', 'Northern_Renaissance', 'High_Renaissance', 'Fauvism'}:
                art = '2'
            else:
                art = '3'
            return art
        art_style = get_pool(dataset_dict)

        if len(self.feats_folder) > 0:
            feat_path = os.path.join(self.feats_folder, image_id + '.npz')
            content = read_np(feat_path)
            att_feats = content['features'][0:self.max_feat_num].astype('float32')
            global_feat = content['g_feature']

            ret = { 
                kfg.IDS: image_id, 
                kfg.ATT_FEATS: att_feats,
                kfg.GLOBAL_FEATS: global_feat,
                kfg.ART_STYLE: art_style
            }

        else:
            # dummy ATT_FEATS
            ret = { kfg.IDS: image_id, kfg.ATT_FEATS: np.zeros((1,1)) }


        # semantics_ids = dataset_dict['attr_pred']
        # semantics_labels = dataset_dict['attr_labels']
        # semantics_miss_labels_arr = dataset_dict['missing_labels']
        # semantics_miss_labels = np.zeros((self.obj_classes+1, )).astype(np.int64)
        # for sem in semantics_miss_labels_arr:
        #     semantics_miss_labels[sem] = 1
        
        # if self.stage != 'train':
        #     semantics_ids = [ semantics_ids.astype(np.int64) ]

            # ret.update({
            #     kfg.SEMANTICS_IDS: semantics_ids,
            # })

            g_tokens_type = np.ones((self.max_seq_len,), dtype=np.int64)
            ret.update({ kfg.G_TOKENS_TYPE: g_tokens_type })
            dict_as_tensor(ret)
            return ret
        
        sent_num = len(dataset_dict['tokens_ids'])
        if sent_num >= self.seq_per_img:
            selects = []
            while len(selects) <= self.seq_per_img:
                i = random.randint(0, sent_num - 1)
                if dataset_dict['emo_label'][i] != 8 and i not in selects:
                    selects.append(i)

        else:
            selects = []
            while len(selects) < self.seq_per_img:
                i = random.randint(0, sent_num - 1)
                if dataset_dict['emo_label'][i] != 8 and i not in selects:
                    selects.append(i)
            selects += random.sample(list(range(sent_num)), self.seq_per_img - sent_num)

        # semantics_ids = [ semantics_ids.astype(np.int64) for i in selects ]
        # semantics_labels = [ semantics_labels.astype(np.int64) for i in selects ]
        # semantics_miss_labels = [ semantics_miss_labels.astype(np.int64) for i in selects ]
        #
        # semantics_ids, semantics_labels, semantics_miss_labels = self.sampling(semantics_ids, semantics_labels, semantics_miss_labels)
        # ret.update({
        #     kfg.SEMANTICS_IDS: semantics_ids,
        #     kfg.SEMANTICS_LABELS: semantics_labels,
        #     kfg.SEMANTICS_MISS_LABELS: semantics_miss_labels,
        # })
        
        # tokens_ids = [ dataset_dict['tokens_ids'][i,:].astype(np.int64) for i in selects ]
        def get_token(datasetdict, select):
            tokens_ids = []
            for i in select:
                tokens = datasetdict['tokens_ids'][i].astype(np.int64)
                token_table = np.array(list(itertools.chain.from_iterable(tokens)))
                tokens_ids.append(token_table)
            return tokens_ids
        tokens_ids = get_token(dataset_dict, selects)

        def get_emo(datasetdict, select):
            g_emo_label = []
            for i in select:
                label = datasetdict['emo_label'][i]
                g_emo_label.append(label)
            return g_emo_label
        g_emo_label = get_emo(dataset_dict, selects)
        # g_emotion_ids = [dataset_dict['emotion_embedding'][i,:].astype("float32") for i in selects]

        # def get_style(datasetdict, select):
        # # 获取art_style
        #     art_style = []
        #     for i in select:
        #         style = datasetdict['art_style']
        #         art_style.append(style)
        #     return art_style
        # art_style = get_style(dataset_dict, selects)

        def get_target(datasetdict, select):
            target_ids = []
            for i in select:
                targets = datasetdict['target_ids'][i].astype(np.int64)
                target_table = np.array(list(itertools.chain.from_iterable(targets)))
                target_ids.append(target_table)
            return target_ids
        target_ids = get_target(dataset_dict, selects)

        def get_token_type(datasetdict, select):
            g_tokens_type = []
            for i in select:
                type = np.ones(datasetdict['tokens_ids'][i].size, dtype=np.int64)
                g_tokens_type.append(type)
            return g_tokens_type
        g_tokens_type = get_token_type(dataset_dict, selects)

        def get_concept(datasetdict, select):
            # 得到作为label的concepts_ids
            attr_gt = []
            supp = np.array([[0,0,0,0,0]])
            for i in select:
                emo_label = dataset_dict['emo_label'][i]
                if emo_label in [0,1,2,3]:
                    word = datasetdict['concept_ids'].get(0, supp)
                    word = np.squeeze(word)
                    attr_gt.append(word)
                elif emo_label in [4,5,6,7]:
                    word = datasetdict['concept_ids'].get(1, supp)
                    word = np.squeeze(word)
                    attr_gt.append(word)
                else:
                    word = datasetdict['concept_ids'].get(2, supp)
                    word = np.squeeze(word)
                    attr_gt.append(word)
            return attr_gt
        concepts_ids = get_concept(dataset_dict, selects)

        def get_emoword(datasetdict, select):
            attr_gt = []
            supp = np.array([[0,0,0,0,0]])
            for i in select:
                emo_label = dataset_dict['emo_label'][i]
                word = datasetdict['emoword_ids'].get(emo_label, supp)
                word = np.squeeze(word)
                attr_gt.append(word)
            return attr_gt
        emoword_ids = get_emoword(dataset_dict, selects)




        # target_ids = [ dataset_dict['target_ids'][i,:].astype(np.int64) for i in selects ]
        # g_tokens_type = [ np.ones((len(dataset_dict['tokens_ids'][i,:]), ), dtype=np.int64) for i in selects ]
        # g_emo_type = [np.ones((len(dataset_dict['emotion_embedding'][0])), dtype=np.int64)]

        ret.update({
            kfg.SEQ_PER_SAMPLE: self.seq_per_img,
            kfg.G_TOKENS_IDS: tokens_ids,
            kfg.G_TARGET_IDS: target_ids,
            kfg.G_TOKENS_TYPE: g_tokens_type,
            kfg.G_ATTR_IDS: concepts_ids,
            # kfg.G_CONCEPTS_IDS: concepts_ids,
            # kfg.G_EMO_WORD_IDS: emoword_ids

        })
        dict_as_tensor(ret)

        ret.update({
            kfg.G_EMO_LABEL: g_emo_label,
            kfg.ART_STYLE: art_style,

        }
        )
        return ret
