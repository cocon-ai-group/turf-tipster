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
import datetime
from bs4 import BeautifulSoup
import csv

url_base = 'http://db.netkeiba.com'
url_list = []
race_url_list = []
holidays = ['2015/1/1','2015/1/12','2015/2/11','2015/4/29','2015/5/4','2015/5/5','2015/5/6','2015/7/20','2015/9/21','2015/9/22','2015/9/23',
'2015/10/12','2015/11/3','2015/11/23','2015/12/23','2016/1/1','2016/1/11','2016/2/11','2016/3/21','2016/4/29','2016/5/3','2016/5/4',
'2016/5/5','2016/7/18','2016/8/11','2016/9/19','2016/9/22','2016/10/10','2016/11/3','2016/11/23','2016/12/23','','2017/1/2','2017/1/9',
'2017/3/20','2017/5/3','2017/5/4','2017/5/5','2017/7/17','2017/8/11','2017/9/18','2017/10/9','2017/11/3','2017/11/23','2018/1/1',
'2018/1/8','2018/2/12','2018/3/21','2018/4/30','2018/5/3','2018/5/4','2018/7/16','2018/9/17','2018/9/24','2018/10/8','2018/11/23','2018/12/24']

today_year = datetime.datetime.today().year
today_month = datetime.datetime.today().month

#for y in [2015,2016,2017]: # 競走馬が走るのは2歳から4歳位なので、3年分で十分
for y in [2016,2017,2018]:
	for m in range(1,13):
		if y == today_year and m >= today_month:
			break
			
		c = calendar.monthcalendar(y, m)
		days = [x[calendar.SUNDAY] for x in c]
		days.extend([x[calendar.SATURDAY] for x in c])

		for d in days:
			url = '/race/list/%d%02d%02d/'%(y,m,d)
			url_list.append((url, '%d%02d%02d'%(y,m,d)))
		
		for d in range(1,32):
			s = '%d%02d%02d/'%(y,m,d)
			if s in holidays:
				url = '/race/list/%d%02d%02d/'%(y,m,d)
				url_list.append((url, '%d%02d%02d'%(y,m,d)))

def get_odds_str(a, num):
	if num == 1:
		if a.string and len(a.string) > 0:
			return a.string.replace(u',', '').replace(u'\\xe5\\x86\\x86', '')
		else:
			return '0'
	else:
		if a.contents and len(a.contents) == num * 2 - 1:
			r = []
			for i in range(num):
				r.append(str(a.contents[i * 2]).replace(u',', '').replace(u'\\xe5\\x86\\x86', ''))
			return r
		else:
			r = []
			for i in range(int((len(a.contents)+1) / 2)):
				r.append(str(a.contents[i * 2]).replace(u',', '').replace(u'\\xe5\\x86\\x86', ''))
			for j in range(num - len(r)):
				r.append('0')
			return r

def get_odds_str_c(a, num):
	if a and len(a) > 0 and a[0].parent:
		a = a[0].parent.find_all('td')
	else:
		a = None
	if a and len(a) >= 2:
		return get_odds_str(a[1], num)
	else:
		if num == 1:
			return '0'
		else:
			return ['0']*num

# タイムアウトを設定
socket.setdefaulttimeout(10)

for url, datestr in url_list:
	with urllib.request.urlopen(url_base+url) as response:
		# URLから読み込む
		html = str(response.read())
		# ギャラリー表示部分のタグを取得する
		race = re.findall(\
			r'<a href=\"(/race/[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]/)\"',\
			html, re.DOTALL)
		race_data = [(x, datestr) for x in race]
		race_url_list.extend(race_data)

with open('race_database.csv', 'w') as csvfile:
	csvwriter = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)
	for url, datestr in race_url_list:
		with urllib.request.urlopen(url_base+url) as response:
			where = ''
			if url[10:12] == '10':
				where = '小倉'
			elif url[10:12] == '09':
				where = '阪神'
			elif url[10:12] == '08':
				where = '京都'
			elif url[10:12] == '07':
				where = '中京'
			elif url[10:12] == '06':
				where = '中山'
			elif url[10:12] == '05':
				where = '東京'
			elif url[10:12] == '04':
				where = '新潟'
			elif url[10:12] == '03':
				where = '福島'
			elif url[10:12] == '02':
				where = '函館'
			elif url[10:12] == '01':
				where = '札幌'
			# URLから読み込む
			html = str(response.read())
			# 馬場距離天気
			soup = BeautifulSoup(html, 'html.parser')
			tl = eval('b"{}"'.format(str(soup.title.string))).decode('EUC_JP')
			diary = soup.find('dl', 'racedata')
			spans = diary.find_all('span')
			exstr = '||'
			if len(spans) >= 1:
				ext = str(spans[0].string).split('m')
				hg = eval('b"{}"'.format(ext[0][0:-4])).decode('EUC_JP')
				l = ext[0][-4:] # 距離
				br = hg[0:1] # ダ 芝 障
				t = ext[1][22:30] # 天気
				tr = eval('b"{}"'.format(t)).decode('EUC_JP')
				if tr == '小':
					tr = '小雨'
				exstr = br+'|'+l+'|'+tr # 馬場距離天気
			# オッズ
			paystr = ''
			pays = soup.find_all('table', 'pay_table_01')
			pays_all = pays[0].find_all('th', 'tan')
			paystr += get_odds_str_c(pays_all,1) + ':' # 単勝
			pays_all = pays[0].find_all('th', 'fuku')
			paystr += '_'.join(get_odds_str_c(pays_all,3)) + ':' # 複勝
			pays_all = pays[0].find_all('th', 'waku')
			paystr += get_odds_str_c(pays_all,1) + ':' # 枠連
			pays_all = pays[0].find_all('th', 'uren')
			paystr += get_odds_str_c(pays_all,1) + ':' # 馬連
			pays_all = pays[1].find_all('th', 'wide')
			paystr += '_'.join(get_odds_str_c(pays_all,3)) + ':' # ワイド
			pays_all = pays[1].find_all('th', 'utan')
			paystr += get_odds_str_c(pays_all,1) + ':' # 馬単
			pays_all = pays[1].find_all('th', 'sanfuku')
			paystr += get_odds_str_c(pays_all,1) + ':' # 三連複
			pays_all = pays[1].find_all('th', 'santan')
			paystr += get_odds_str_c(pays_all,1) # 三連単
			# タイトル
			race_title = re.sub(r'[\s]|(-.*$)', '', tl).replace(u'｜', '|')
			race_title = '|'.join(race_title.split('|')[0:1])
			race_title += '|' + where + '|' + exstr + '|' + paystr + '|' + datestr
			race_results = [race_title]
			table = soup.find('table', 'race_table_01')
			rows = table.find_all('tr')
			bef_r = '1'
			for row in rows:
				td = row.find_all('td')
				if len(td) > 10:
					hr = eval('b"{}"'.format(str(td[3].find('a').string))).decode('EUC_JP')
					jk = eval('b"{}"'.format(str(td[6].find('a').string))).decode('EUC_JP')
					hr = hr.replace(u'(地)', '').replace(u'[地]', '').replace(u'(外)', '').replace(u'[外]', '')
					jk = jk.replace(u'▲', '').replace(u'☆', '').replace(u'△', '')
					if jk == 'Mデムーロ':
						jk = 'Ｍ．デム'
					if jk == 'Cデムーロ':
						jk = 'Ｃ．デム'
					if jk == 'Cルメール':
						jk = 'ルメール'
					if jk == 'Vシュミノ':
						jk = 'シュミノ'
					if jk == 'Hボウマン':
						jk = 'ボウマン'
					if jk == 'Fベリー':
						jk = 'ベリー'
					if jk == 'Gブノワ':
						jk = 'ブノワ'
					if jk == 'Aシュタル':
						jk = 'シュタル'
					if jk == 'Dバルジュ':
						jk = 'バルジュ'
					if jk == 'Dホワイト':
						jk = 'ホワイト'
					if jk == 'Rムーア':
						jk = 'ムーア'
					if jk == 'Kティータ':
						jk = 'ティータ'
					if jk == 'Aクラスト':
						jk = 'クラスト'
					if jk == 'Aアッゼニ':
						jk = 'アッゼニ'
					if jk == 'Bプレブル':
						jk = 'プレブル'
					if jk == 'Cウィリア':
						jk = 'ウィリア'
					if jk == 'Cパリッシ':
						jk = 'パリッシ'
					if jk == 'Dポルク':
						jk = 'ポルク'
					if jk == 'Dマクドノ':
						jk = 'マクドノ'
					if jk == 'Eウィルソ':
						jk = 'ウィルソ'
					if jk == 'Eダシルヴ':
						jk = 'ダシルヴ'
					if jk == 'Fミナリク':
						jk = 'ミナリク'
					if jk == 'Fヴェロン':
						jk = 'ヴェロン'
					if jk == 'Gモッセ':
						jk = 'モッセ'
					if jk == 'Hターナー':
						jk = 'ターナー'
					if jk == 'Iファーガ':
						jk = 'ファーガ'
					if jk == 'Jモレイラ':
						jk = 'モレイラ'
					if jk == 'Jスペンサ':
						jk = 'スペンサ'
					if jk == 'Kマカヴォ':
						jk = 'マカヴォ'
					if jk == 'Kマリヨン':
						jk = 'マリヨン'
					if jk == 'Lオールプ':
						jk = 'オールプ'
					if jk == 'Lコントレ':
						jk = 'コントレ'
					if jk == 'Mデュプレ':
						jk = 'デュプレ'
					if jk == 'Mバルザロ':
						jk = 'バルザロ'
					if jk == 'Pブドー':
						jk = 'ブドー'
					if jk == 'Rベイズ':
						jk = 'ベイズ'
					if jk == 'Sパスキエ':
						jk = 'パスキエ'
					if jk == 'Sフォーリ':
						jk = 'フォーリ'
					if jk == 'Tベリー':
						jk = 'ベリー'
					if jk == 'Tジャルネ':
						jk = 'ジャルネ'
					if jk == 'Tクウィリ':
						jk = 'クウィリ'
					if jk == 'Zパートン':
						jk = 'パートン'
					if jk == '竹之下智昭':
						jk = '竹之下智'
					if jk == '石川裕紀人':
						jk = '石川裕紀'
					if jk == '五十嵐雄祐':
						jk = '五十嵐雄'
					if jk == '野中悠太郎':
						jk = '野中悠太'
					if jk == '藤田菜七子':
						jk = '藤田菜七'
					if jk == '武士沢友治':
						jk = '武士沢友'
					if jk == '西田雄一郎':
						jk = '西田雄一'
					if jk == '小野寺祐太':
						jk = '小野寺祐'
					if jk == '佐久間寛志':
						jk = '佐久間寛'
					if jk == '五十嵐冬樹':
						jk = '五十嵐冬'
					if jk == '秋山真一郎':
						jk = '秋山真一'
					if jk == '竹之下智昭':
						jk = '竹之下智'
					if jk == '藤井勘一郎':
						jk = '藤井勘一'
					if jk == '浜野谷憲尚':
						jk = '浜野谷憲'
					if jk == '御神本訓史':
						jk = '御神本訓'
					if jk == '山本咲希到':
						jk = '山本咲希'
					if jk == '佐々木国明':
						jk = '佐々木国'
					if jk == '三津谷隼人':
						jk = '三津谷隼'
					r = str(td[0].string)
					r = r.replace('\\xe5\\x8f\\x96\\xe6\\xb6\\x88', '16')
					r = r.replace('\\xe9\\x99\\xa4\\xe5\\xa4\\x96', '16')
					r = r.replace('\\xe4\\xb8\\xad\\xe6\\xad\\xa2', '14')
					if r.startswith('\\x'):
						r = str(int(bef_r)+1)
					bef_r = r
					result = (r,hr,jk)
					race_results.append('|'.join(result))
			csvwriter.writerow(race_results)
