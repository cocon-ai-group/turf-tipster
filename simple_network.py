# -*- coding: utf-8 -*-
import chainer
import chainer.functions as F
import chainer.links as L
from chainer import training, datasets, iterators, optimizers
from chainer.training import extensions
from chainer.functions.evaluation import accuracy
from chainer.links import caffe as C
from chainer import reporter
import numpy as np

nn_nodes = (200, 60, 5)

# ニューラルネットワークの定義をするクラス
class Turf_Tipster_NN(chainer.Chain):

	def __init__(self, n_horses, n_jockeys):
		n_units_r, n_units_s, n_units_d = nn_nodes
		super(Turf_Tipster_NN, self).__init__()
		with self.init_scope():
			# 馬モデルのレイヤー
			self.le = L.EmbedID(n_horses, n_horses)
			# 騎手モデルのレイヤー
			self.re = L.EmbedID(n_jockeys, n_jockeys)
			# レースモデルのレイヤー
			self.m1 = L.EmbedID(11, 11)
			self.m2 = L.EmbedID(8, 8)
			self.m3 = L.EmbedID(4, 4)
			self.m4 = L.EmbedID(4, 4)
			self.j1 = L.Linear(n_horses + n_jockeys + 11 + 8 + 4 + 4, n_units_r)
			self.j2 = L.Linear(n_units_r, n_units_s)
			self.j3 = L.Linear(n_units_s, n_units_d)

	# 引数は(レースメタ情報, グリッド情報)で着順になっている
	def __call__(self, t, train=True):
		grid = t[0]
		num_gates = len(grid)
		# 馬番号と騎手番号のゲート分
		cp = self.xp
		l_h1 = cp.zeros((num_gates), dtype=cp.int32)
		r_h1 = cp.zeros((num_gates), dtype=cp.int32)
		t_m1 = cp.zeros((num_gates), dtype=cp.int32)
		t_m2 = cp.zeros((num_gates), dtype=cp.int32)
		t_m3 = cp.zeros((num_gates), dtype=cp.int32)
		t_m4 = cp.zeros((num_gates), dtype=cp.int32)
		# ゲート分のデータを作る
		for i in range(num_gates):
			l, r, m1, m2, m3, m4 = grid[i]
			l_h1[i] = l
			r_h1[i] = r
			t_m1[i] = m1
			t_m2[i] = m2
			t_m3[i] = m3
			t_m4[i] = m4
		# レースモデルを計算
		l_h1 = self.le(l_h1)
		r_h1 = self.re(r_h1)
		j_m1 = self.m1(t_m1)
		j_m2 = self.m2(t_m2)
		j_m3 = self.m3(t_m3)
		j_m4 = self.m4(t_m4)
		j_h1 = F.concat([l_h1, r_h1, j_m1, j_m2, j_m3, j_m4], axis=1)
		j_h2 = F.dropout(F.sigmoid(self.j1(j_h1)))
		j_h3 = F.dropout(F.sigmoid(self.j2(j_h2)))
		j_h4 = F.sigmoid(self.j3(j_h3))
		return F.sigmoid(j_h4)

