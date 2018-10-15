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

nn_nodes = (1500, 350, 45, 300, 150)

# ニューラルネットワークの定義をするクラス
class Turf_Tipster_NN(chainer.Chain):

	def __init__(self, n_horses, n_jockeys):
		n_units_h, n_units_v, n_units_j, n_units_r, n_units_d = nn_nodes
		super(Turf_Tipster_NN, self).__init__()
		with self.init_scope():
			# 馬モデルのステータス（モデルを保存できるようにParameterで保持しておく）
			self.vc = chainer.Parameter(np.zeros((n_horses, n_units_v), dtype=np.float32))
			self.vh = chainer.Parameter(np.zeros((n_horses, n_units_v), dtype=np.float32))
			# 馬モデルのレイヤー
			self.le = L.EmbedID(n_horses, n_horses)
			self.l1 = L.Linear(n_horses, n_units_h)
			self.l2 = L.LSTM(n_units_h, n_units_v)
			# 騎手モデルのレイヤー
			self.re = L.EmbedID(n_jockeys, n_jockeys)
			self.r1 = L.Linear(n_jockeys, n_units_j)
			# レースモデルのレイヤー
			self.m1 = L.EmbedID(11, 11)
			self.m2 = L.EmbedID(8, 8)
			self.m3 = L.EmbedID(4, 4)
			self.m4 = L.EmbedID(4, 4)
			self.j1 = L.Linear(n_units_v + n_units_j + 11 + 8 + 4 + 4, n_units_r)
			self.j2 = L.Linear(n_units_r, n_units_r)
			self.j3 = L.Linear(n_units_r, n_units_d)

	# 引数は(レースメタ情報, グリッド情報)で着順になっている
	def __call__(self, t, train=True):
		grid = t[0]
		num_gates = len(grid)
		cp = self.xp
		# 馬モデルのステータス
		l_vc = cp.zeros((num_gates, self.vc.data.shape[1]), dtype=cp.float32)
		l_vh = cp.zeros((num_gates, self.vh.data.shape[1]), dtype=cp.float32)
		# ゲート分のステータスを作る
		for i in range(num_gates):
			l, r, m1, m2, m3, m4 = grid[i] # l, rは(馬番号, 騎手番号)
			_l = l
			if cp != np:
				l = chainer.cuda.to_cpu(l)
			l = int(l[0])
			l_vc[i][:] = self.vc.data[l]
			l_vh[i][:] = self.vh.data[l]
		l_h1 = cp.zeros((num_gates), dtype=cp.int32)
		r_h1 = cp.zeros((num_gates), dtype=cp.int32)
		t_m1 = cp.zeros((num_gates), dtype=cp.int32)
		t_m2 = cp.zeros((num_gates), dtype=cp.int32)
		t_m3 = cp.zeros((num_gates), dtype=cp.int32)
		t_m4 = cp.zeros((num_gates), dtype=cp.int32)
		# ゲート分のデータを作る
		for i in range(num_gates):
			l, r, m1, m2, m3, m4 = grid[i]
			l_h1[i] = l[0]
			r_h1[i] = r[0]
			t_m1[i] = m1[0]
			t_m2[i] = m2[0]
			t_m3[i] = m3[0]
			t_m4[i] = m4[0]
		# 馬モデルを計算
		self.l2.set_state(chainer.Variable(l_vc), chainer.Variable(l_vh))
		l_l1 = F.tanh(self.le(l_h1))
		l_l2 = F.tanh(self.l1(l_l1))
		l_l3 = F.tanh(self.l2(l_l2))
		# 馬モデルのステータスを保存
		if train == True:
			l_wc = cp.copy(self.vc.data)
			l_wh = cp.copy(self.vh.data)
			for i in range(num_gates):
				l, r, m1, m2, m3, m4 = grid[i] # l, rは(馬番号, 騎手番号)
				if cp != np:
					l = chainer.cuda.to_cpu(l)
				l = int(l[0])
				l_wc[l][:] = self.l2.c.data[i]
				l_wh[l][:] = self.l2.h.data[i]
			self.vc.copydata(chainer.Variable(l_wc))
			self.vh.copydata(chainer.Variable(l_wh))
		# レースモデルを計算
		r_h1 = F.tanh(self.re(r_h1))
		r_h2 = F.tanh(self.r1(r_h1))
		j_m1 = self.m1(t_m1)
		j_m2 = self.m2(t_m2)
		j_m3 = self.m3(t_m3)
		j_m4 = self.m4(t_m4)
		j_h1 = F.concat([l_l3, r_h2, j_m1, j_m2, j_m3, j_m4], axis=1)
		j_h2 = F.dropout(F.sigmoid(self.j1(j_h1)))
		j_h3 = F.sigmoid(self.j2(j_h2))
		return F.sigmoid(j_h3)

	def reset_state(self):
		self.l2.reset_state()
		self.vc.copydata(chainer.Variable(cp.zeros(self.vc.data.shape, dtype=cp.float32)))
		self.vh.copydata(chainer.Variable(cp.zeros(self.vh.data.shape, dtype=cp.float32)))
