# -*- coding: utf-8 -*-
import codecs
import re
import urllib.parse
import urllib.request
import os
import socket
import sys
import math
import calendar
import csv
import argparse
import chainer
import chainer.functions as F
import chainer.links as L
from chainer import training, datasets, iterators, optimizers
from chainer.training import extensions
from chainer.functions.evaluation import accuracy
from chainer.links import caffe as C
from chainer import reporter
import numpy as np
import random
from PIL import Image


def main():
	parser = argparse.ArgumentParser(description='Chainer example: Prefigure horse rase')
	parser.add_argument('--race', '-r', default='',
						help='All Gates')
	parser.add_argument('--meta', '-e', default='',
						help='Race Data')
	parser.add_argument('--model', '-m', default='simple',
						help='Use model type (simple / rnn)')
	parser.add_argument('--modelfile', '-f', default='turf-tipster.npz',
						help='Trained model file')
	parser.add_argument('--gpu', '-g', type=int, default=-1,
						help='GPU ID (negative value indicates CPU)')
	parser.add_argument('--gates', '-a', type=int, default=18,
						help='Number of gates')
	parser.add_argument('--horsefile', '-o', default='horse_names.txt',
						help='Train horse names file')
	parser.add_argument('--jockeyfile', '-j', default='jockey_names.txt',
						help='Train jockey names file')
	args = parser.parse_args()
	
	if args.model == 'rnn':
		import rnn_network as newralnet
	else:
		import simple_network as newralnet

	uses_device = args.gpu
	in_data = args.race  # 入力データ = 馬名|騎手名,馬名|騎手名,馬名|騎手名・・・
	in_meta = args.meta  # メタデータ = 場所|馬場|天気|距離
	num_gates = args.gates
	src_file = args.modelfile
	hoses_file = args.horsefile
	jockeys_file = args.jockeyfile

	# GPU使用時とCPU使用時でデータ形式が変わる
	if uses_device >= 0:
		import cupy as cp
	else:
		cp = np

	horse_names = []
	jockey_names = []
	horse_names_i = {}
	jockey_names_i = {}

	# 名前を読み込む
	f = codecs.open(hoses_file, 'r', 'utf8')
	line = f.readline()
	while line:
		l = line.strip()
		horse_names_i[l] = len(horse_names)
		horse_names.append(l)
		line = f.readline()
	f.close()
	f = codecs.open(jockeys_file, 'r', 'utf8')
	line = f.readline()
	while line:
		l = line.strip()
		jockey_names_i[l] = len(jockey_names)
		jockey_names.append(l)
		line = f.readline()
	f.close()

	# メタ情報を読み込む
	in_meta_sp = in_meta.split('|')
	where_str = in_meta_sp[0]
	baba_str = in_meta_sp[1]
	len_str = in_meta_sp[2]
	tenki_str = in_meta_sp[3]
	where_i = 0
	if where_str == '小倉':
		where_i = 1
	elif where_str == '阪神':
		where_i = 2
	elif where_str == '京都':
		where_i = 3
	elif where_str == '中京':
		where_i = 4
	elif where_str == '中山':
		where_i = 5
	elif where_str == '東京':
		where_i = 6
	elif where_str == '新潟':
		where_i = 7
	elif where_str == '福島':
		where_i = 8
	elif where_str == '函館':
		where_i = 9
	elif where_str == '札幌':
		where_i = 10
	baba_i = 0
	if baba_str == '芝':
		baba_i = 1
	elif baba_str == 'ダ':
		baba_i = 2
	elif baba_str == '障':
		baba_i = 3
	tenki_i = 0
	if tenki_str == '晴':
		tenki_i = 1
	elif tenki_str == '曇':
		tenki_i = 2
	elif tenki_str == '雨':
		tenki_i = 3
	len_l = int(len_str)
	if len_l <= 1200:
		len_i = 1
	elif len_l <= 1400:
		len_i = 2
	elif len_l <= 1600:
		len_i = 3
	elif len_l <= 1800:
		len_i = 4
	elif len_l <= 2000:
		len_i = 5
	elif len_l <= 2400:
		len_i = 6
	elif len_l <= 2800:
		len_i = 7
	else:
		len_i = 0

	pair_datas = in_data.split(',')
	if len(pair_datas) <= 0:
		print('No Data')
		quit()
	horse_datas = []
	jockey_datas = []
	for i in range(min(18,len(pair_datas))):
		pd = pair_datas[i].split('|')
		if not len(pd) == 2:
			print('Invalid Data')
			quit()
		if pd[0] in horse_names_i:
			horse_datas.append(horse_names_i[pd[0]])
		else:
			horse_datas.append(horse_names_i['その他'])
		if pd[1] in jockey_names_i:
			jockey_datas.append(jockey_names_i[pd[1]])
		else:
			jockey_datas.append(jockey_names_i['その他'])
	for i in range(len(pair_datas),18):
		horse_datas.append(horse_names_i['未出走'])
		jockey_datas.append(jockey_names_i['その他'])
	
	# 学習結果を読み込む
	nn = newralnet.Turf_Tipster_NN(len(horse_names), len(jockey_names))
	chainer.serializers.load_npz( src_file, nn )

	# 予想を実行する
	data = [([horse_datas[x]],[jockey_datas[x]],[where_i],[len_i],[baba_i],[tenki_i]) for x in range(18)]
	data = np.array([data], dtype=np.int32)
	with chainer.using_config('train', False):
		r = nn(data, train=False)
	result_data = []
	for i in range(18):
		result_data.append(F.sum(r[i]).data)
	result_data = np.array([result_data], dtype=np.float32)
	result_soft = F.softmax(result_data)
	result_set = []
	for i in range(18):
		x = result_soft.data[0][i]
		n = horse_names[horse_datas[i]]
		result_set.append((n,x))
	p = 0
	print('予想順位\t馬名\tAccuracy')
	for n, x in sorted(result_set, key=lambda x:x[1], reverse=True):
		p = p + 1
		print(str(p) + '\t' + n + '\t' + str(x))


if __name__ == '__main__':
	main()
