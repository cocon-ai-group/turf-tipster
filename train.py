# -*- coding: utf-8 -*-
import codecs
import re
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
	parser.add_argument('--train', '-t', default='race_train.csv',
						help='Training file')
	parser.add_argument('--test', '-s', default='race_test.csv',
						help='Test file')
	parser.add_argument('--model', '-m', default='simple',
						help='Use model type (simple / rnn)')
	parser.add_argument('--epoch', '-e', type=int, default=50,
						help='Number of sweeps over the dataset to train')
	parser.add_argument('--gpu', '-g', type=int, default=-1,
						help='GPU ID (negative value indicates CPU)')
	parser.add_argument('--out', '-o', default='result',
						help='Directory to output the result')
	parser.add_argument('--gates', '-a', type=int, default=18,
						help='Number of gates')
	parser.add_argument('--horses', '-r', type=int, default=8000,
						help='Number of horses')
	parser.add_argument('--lossfunc', '-l', type=int, default=1,
						help='Type of loss function (1 / 2)')
	args = parser.parse_args()
	
	if args.model == 'rnn':
		import rnn_network as newralnet
	else:
		import simple_network as newralnet

	train_file = args.train
	test_file = args.test
	uses_device = args.gpu
	num_epoch = args.epoch
	num_gates = args.gates
	max_horses = args.horses
	loss_func = args.lossfunc

	random.seed(976)
	np.random.seed(976)

	# GPU使用時とCPU使用時でデータ形式が変わる
	if uses_device >= 0:
		import cupy as cp
	else:
		cp = np

	all_horses = {}
	all_jockeys = {}
	all_races_train = []
	all_races_test = []

	# 出走数 5〜18
	def read_file(file, all_races):
		with open(file, 'r') as csvfile:
			csvreader = csv.reader(csvfile)
			for race in csvreader:
				all_races.append(race)
				for e in range(1, len(race)):
					entry = race[e]
					result = entry.split('|')
					if len(result) >= 3:
						if not result[1] in all_horses:
							all_horses[result[1]] = 1
						else:
							all_horses[result[1]] += 1
						if not result[2] in all_jockeys:
							all_jockeys[result[2]] = 1
						else:
							all_jockeys[result[2]] += 1
	read_file(train_file, all_races_train)
	read_file(test_file, all_races_test)

	# 馬、騎手のリストと逆引き辞書
	horse_names = []
	jockey_names = list(all_jockeys.keys())
	jockey_names.append('その他')

	i = 0
	for k, v in sorted(all_horses.items(), key=lambda x:x[1], reverse=True):
		horse_names.append(k)
		i = i+1
		if i == max_horses-2:
			break
	horse_names.append('その他')
	horse_names.append('未出走')

	all_horses_i = {}
	all_jockeys_i = {}
	for k in range(len(horse_names)):
		all_horses_i[horse_names[k]] = k
	for k in range(len(jockey_names)):
		all_jockeys_i[jockey_names[k]] = k

	# 全てのラベルを保存する
	with open('horse_names.txt', 'w') as out_file:
		out_file.write('\n'.join(horse_names))
	with open('jockey_names.txt', 'w') as out_file:
		out_file.write('\n'.join(jockey_names))

	# 1 iter = 18gete
	# 1 epoch = 全レース
	all_races_gates_train = []
	all_races_gates_test = []
	def get_race_gets(all_races, all_races_gates):
		for ri in range(len(all_races)):
			results = []
			race = all_races[ri]
			meta = cp.array([0]*4,dtype=cp.int32)
			odds_i = cp.array([0]*12,dtype=cp.int32)
			# メタデータ
			race_meta = race[0].split('|')
			if len(race_meta) > 5:
				where_str = race_meta[1]
				baba_str = race_meta[2]
				len_str = race_meta[3]
				tenki_str = race_meta[4]
				odds_str = race_meta[5]
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
				odds = odds_str.split(':')
				odds_i = cp.array([
					int(odds[0]), # 単勝
					int(odds[1].split('_')[0]), # 複勝
					int(odds[1].split('_')[1]), # 複勝
					int(odds[1].split('_')[2]), # 複勝
					int(odds[2]), # 枠連
					int(odds[3]), # 馬連
					int(odds[4].split('_')[0]), # ワイド
					int(odds[4].split('_')[1]), # ワイド
					int(odds[4].split('_')[2]), # ワイド
					int(odds[5]), # 馬単
					int(odds[6]), # 三連複
					int(odds[7]) # 三連単
					], dtype=cp.int32)

			# 出走した馬、騎手を着順に入れる
			for e in range(1, len(race)):
				entry = race[e]
				result = entry.split('|')
				if len(result) >= 3:
					r_horse = len(horse_names)-2
					r_jockey = len(jockey_names)-1
					if result[1] in all_horses_i:
						r_horse = all_horses_i[result[1]]
					if result[2] in all_jockeys_i:
						r_jockey = all_jockeys_i[result[2]]
					results.append((cp.array([r_horse] ,dtype=cp.int32), cp.array([r_jockey] ,dtype=cp.int32), cp.array([where_i if random.random() > 0.5 else 0] ,dtype=cp.int32), cp.array([len_i if random.random() > 0.5 else 0] ,dtype=cp.int32), cp.array([baba_i if random.random() > 0.5 else 0] ,dtype=cp.int32), cp.array([tenki_i if random.random() > 0.5 else 0] ,dtype=cp.int32)))
			# gete数に足りない分は未出走で登録
			for j in range(len(results), num_gates):
				results.append((cp.array([len(horse_names)-1] ,dtype=cp.int32), cp.array([len(jockey_names)-1] ,dtype=cp.int32), cp.array([where_i if random.random() > 0.5 else 0] ,dtype=cp.int32), cp.array([len_i if random.random() > 0.5 else 0] ,dtype=cp.int32), cp.array([baba_i if random.random() > 0.5 else 0] ,dtype=cp.int32), cp.array([tenki_i if random.random() > 0.5 else 0] ,dtype=cp.int32)))
			
			tr = cp.array(results, dtype=cp.int32)
			sc = odds_i
				
			all_races_gates.append((tr, sc))
	get_race_gets(all_races_train, all_races_gates_train)
	get_race_gets(all_races_test, all_races_gates_test)
	
	# 損失関数
	def loss_gate1(t, ext):
		loss = 0
		s = []
		for i in range(num_gates):
			s.append(F.sum(t[i]))
		for x in range(num_gates):
			for y in range(num_gates):
				loss += num_gates + F.softplus(s[y] - s[x]) * math.atan(y - x)
		return loss / (num_gates * num_gates)
		
	def loss_gate2(t, ext):
		loss = 0
		s = []
		for i in range(num_gates):
			s.append(F.sum(t[i]))
		for x in range(num_gates):
			for y in range(num_gates):
				loss += num_gates + F.sigmoid(s[y] - s[x]) * (y - x)
		return loss / (num_gates * num_gates)
	
	# 評価関数
	def acc_gate(t, ext):
		s = []
		for i in range(num_gates):
			s.append(F.sum(t[i]).data)
		# オッズを元にリターンベースで評価
		v = cp.argsort(cp.array(s, dtype=cp.float32))
		v = cp.flip(v, axis=0)
		tansho = 0
		if v[0] == 0:
			tansho = ext[0][0] # 単勝
		fukusho1 = 0
		if v[0] == 0:
			fukusho1 = ext[0][1] # 複勝（1枚買ったとき）
		if v[0] == 1:
			fukusho1 = ext[0][2] # 複勝（1枚買ったとき）
		if v[0] == 2:
			fukusho1 = ext[0][3] # 複勝（1枚買ったとき）
		fukusho2 = 0
		if v[0] == 0 or v[1] == 0:
			fukusho2 += ext[0][1] # 複勝（2枚買ったとき）
		if v[0] == 1 or v[1] == 1:
			fukusho2 += ext[0][2] # 複勝（2枚買ったとき）
		fukusho2 = fukusho2 / 2
		fukusho3 = 0
		if v[0] == 0 or v[1] == 0 or v[2] == 0:
			fukusho3 += ext[0][1] # 複勝（3枚買ったとき）
		if v[0] == 1 or v[1] == 1 or v[2] == 1:
			fukusho3 += ext[0][2] # 複勝（3枚買ったとき）
		if v[0] == 2 or v[1] == 2 or v[2] == 2:
			fukusho3 += ext[0][3] # 複勝（3枚買ったとき）
		fukusho3 = fukusho3 / 3
		umaren = 0
		if v[0] == 0 and v[1] == 1:
			umaren = ext[0][5]
		elif v[0] == 1 and v[1] == 0:
			umaren = ext[0][5] # 馬連
		wide = 0
		if (v[0] == 0 and v[1] == 1) or (v[0] == 1 and v[1] == 0):
			wide = ext[0][6] # ワイド
		elif (v[0] == 0 and v[1] == 2) or (v[0] == 2 and v[1] == 0):
			wide = ext[0][7] # ワイド
		elif (v[0] == 1 and v[1] == 2) or (v[0] == 2 and v[1] == 1):
			wide = ext[0][8] # ワイド
		umatan = 0
		if v[0] == 0 and v[1] == 1:
			umatan = ext[0][9] # 馬単
		triren = 0
		if v[0] <= 2 and v[1] <= 2 and v[2] <= 2:
			triren = ext[0][10] # 3連複
		tritan = 0
		if v[0] == 0 and v[1] == 1 and v[2] == 2:
			tritan = ext[0][11] # 3単連
		return (tansho,fukusho1,fukusho2,fukusho3,umaren,wide,umatan,triren,tritan)

	class An_Classifier(L.Classifier):
		def __init__(self, nn, lossfun, accfun):
			super(An_Classifier, self).__init__(nn, lossfun, accfun)
		def __call__(self, *args, **kwargs):
			r = super(An_Classifier, self).__call__(*args, **kwargs)
			if self.compute_accuracy:
				reporter.report({'tansho': self.accuracy[0]}, self)
				reporter.report({'fukusho1': self.accuracy[1]}, self)
				reporter.report({'fukusho2': self.accuracy[2]}, self)
				reporter.report({'fukusho3': self.accuracy[3]}, self)
				reporter.report({'umaren': self.accuracy[4]}, self)
				reporter.report({'wide': self.accuracy[5]}, self)
				reporter.report({'umatan': self.accuracy[6]}, self)
				reporter.report({'triren': self.accuracy[7]}, self)
				reporter.report({'tritan': self.accuracy[8]}, self)
			return r

	nn = newralnet.Turf_Tipster_NN(len(horse_names), len(jockey_names))
	# ニューラルネットワークの作成
	model = An_Classifier(nn, lossfun=(loss_gate1 if loss_func==1 else loss_gate2), accfun=acc_gate)

	if uses_device >= 0:
		# GPUを使う
		chainer.cuda.get_device_from_id(0).use()
		chainer.cuda.check_cuda_available()
		# GPU用データ形式に変換
		model.to_gpu()

	# 誤差逆伝播法アルゴリズムを選択
	optimizer = optimizers.AdaGrad()
	optimizer.setup(model)

	# Iteratorを作成
	to_shuffle = True
	if args.model == 'rnn':
		to_shuffle = False
	train_iter = iterators.SerialIterator(all_races_gates_train, 1, shuffle=to_shuffle)
	test_iter = iterators.SerialIterator(all_races_gates_test, 1, repeat=False, shuffle=to_shuffle)

	# Updaterを作成する
	if args.model == 'rnn':
		class MyUpdater(training.StandardUpdater):
			def __init__(self, train_iter, optimizer, device):
				super(MyUpdater, self).__init__(
					train_iter,
					optimizer,
					device=device
				)
		def update_core(self):
			train_iter = self.get_iterator('main')
			optimizer = self.get_optimizer('main')
			if train_iter.is_new_epoch:
				optimizer.target.reset_state()
			batch = train_iter.next()[0]
			result = optimizer.target(batch)
			loss = optimizer.target(result)
			optimizer.target.cleargrads()
			loss.backward()
			loss.unchain_backward()
			optimizer.update()
			chainer.report({'loss': loss}, self)
		updater = MyUpdater(train_iter, optimizer, device=uses_device)
	else:
		updater = training.StandardUpdater(train_iter, optimizer, device=uses_device)

	# デバイスを選択してTrainerを作成する
	trainer = training.Trainer(updater, (num_epoch, 'epoch'), out="result")
	# テストを実行
	trainer.extend(extensions.Evaluator(test_iter, model, device=uses_device))
	# 学習の進展を表示するようにする
	trainer.extend(extensions.LogReport())
	trainer.extend(extensions.ProgressBar(update_interval=1))
	trainer.extend(extensions.PrintReport(['epoch','main/loss',
		'validation/main/loss','main/tansho', 'validation/main/tansho',
		'main/fukusho1', 'validation/main/fukusho1',
		'main/fukusho2', 'validation/main/fukusho2',
		'main/fukusho3', 'validation/main/fukusho3',
		'main/umaren', 'validation/main/umaren',
		'main/wide', 'validation/main/wide',
		'main/triren', 'validation/main/triren',
		'main/tritan', 'validation/main/tritan',]))
	# 中間結果を保存する
	@chainer.training.make_extension(trigger=(5, 'epoch'))
	def save_model(trainer):
		global n_save
		# NNのデータを保存
		n_save = n_save+1
		chainer.serializers.save_npz( 'turf-tipster-'+str(n_save)+'.npz', nn )
	trainer.extend(save_model)
	# 機械学習を実行する
	trainer.run()

	# 学習結果を保存する
	chainer.serializers.save_npz( 'turf-tipster.npz', nn )

n_save = 0

if __name__ == '__main__':
	main()
