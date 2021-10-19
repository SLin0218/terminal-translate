#!/usr/bin/env python
# -*- coding: utf-8 -*
import urwid
import os
import re
import time
import hashlib
import requests
from urllib.parse import quote, urlencode


# j = open('./lin.json').read()
# response = json.loads(j)
# message = response['message']
# baes_info = message['baesInfo']

url = 'http://dict.iciba.com/dictionary/word/query/web'
sentence_url = 'http://ifanyi.iciba.com/index.php' \
    '?c=trans&m=fy&client=6&auth_user=key_ciba&sign='

query = {
    'client': '6',
    'key': '1000006',
}

'''
句子翻译签名位置 _app-****.js
t = {from: 'en' q: '要翻译的句子' to: 'zh'}
takeResult: function(e) {
   var t = f().parse(e)
     , r = c()('6key_cibaifanyicjbysdlove1'
      .concat(t.q)
      .toString().substring(0, 16);
   return y('/index.php?c=trans&m=fy&client=6&auth_user=key_ciba&sign='
      .concat(r), {
       baseURL: '//ifanyi.iciba.com',
       method: 'post',
       headers: {
           'Content-Type': 'application/x-www-form-urlencoded'
       },
       data: e
   })
},
md5(6key_cibaifanyicjbysdlove1 + 翻译文本).substring(0, 16)
http://ifanyi.iciba.com/index.php?c=trans&m=fy&client=6&auth_user=key_ciba&sign=cf831dec5b7d01a1
'''


def signature(params):
    code = '/dictionary/word/query/web' + \
        params['client'] + params['key'] + params['timestamp'] + \
        params['word'] + '7ece94d9f9c202b0d2ec557dg4r9bc'
    md5 = hashlib.md5()
    md5.update(code.encode('utf-8'))
    return md5.hexdigest()


def sentence_signature(q):
    code = '6key_cibaifanyicjbysdlove1' + q
    md5 = hashlib.md5()
    md5.update(code.encode('utf-8'))
    return md5.hexdigest()[:16]


def translate(word):
    zh_re = re.compile('^[\u4e00-\u9fa5，。]+$')
    if word.count(' ') > 0:
        return translate_sentence(word)
    elif zh_re.search(word):
        return translate_sentence(word, True)
    else:
        return translate_word(word)


def translate_sentence(word, zh=False):
    post_data = {'from': 'en', 'to': 'zh', 'q': word}
    if zh:
        post_data = {'from': 'zh', 'to': 'en', 'q': word}
    r = requests.post(sentence_url + sentence_signature(word), data=post_data)
    response = r.json()
    data = {
        'phonation': response['content']['out'],
        'paraphrase_content': '',
        'synonym_content': '',
        'sentence_content': '',
        'phrase_content': ''
    }
    return data


def translate_word(word):
    query['word'] = quote(word)
    query['timestamp'] = str(int(round(time.time() * 1000)))
    query['signature'] = signature(query)
    r = requests.get(url + '?' + urlencode(query))
    response = r.json()
    message = response['message']
    baes_info = message['baesInfo']
    data = {
        'phonation': '',
        'paraphrase_content': '',
        'synonym_content': '',
        'sentence_content': '',
        'phrase_content': ''
    }
    if 'symbols' in baes_info:
        symbols = baes_info['symbols'][0]
        phonation = ''
        if 'ph_en' in symbols:
            phonation = '英[' + symbols['ph_en'] + ']'
        if 'ph_am' in symbols:
            if phonation:
                phonation += '  '
            phonation = '美[' + symbols['ph_am'] + ']'
        if 'word_symbol' in symbols:
            phonation = '[' + symbols['word_symbol'] + ']'
        if phonation:
            data['phonation'] = phonation

        parts_txt = ''
        if 'fromSymbolsMean' in baes_info \
                and len(baes_info['fromSymbolsMean']) > 0:
            fromSymbolsMean = baes_info['fromSymbolsMean'][0]
            for word in fromSymbolsMean['word'][0]['word']:
                if parts_txt:
                    parts_txt += '\n'
                parts_txt += word['word_name'] + '：' + \
                    '；'.join(word['symbols'][0]['parts'][0]['means'])
        else:
            for part in symbols['parts']:
                parts_txt += part['part'] + '  ' + \
                    '；'.join(part['means']) + '\n'
        data['paraphrase_content'] = parts_txt

    if 'exchange' in baes_info:
        exchange = baes_info['exchange']
        exchange_txt = ''
        if 'word_pl' in exchange:
            exchange_txt += '复数：' + exchange['word_pl'][0] + '；'
        if 'word_third' in exchange:
            exchange_txt += '第三人称单数：' + exchange['word_third'][0] + '；'
        if 'word_past' in exchange:
            exchange_txt += '过去式：' + exchange['word_past'][0] + '；'
        if 'word_done' in exchange:
            exchange_txt += '过去分词：' + exchange['word_done'][0] + '；'
        if 'word_ing' in exchange:
            exchange_txt += '现在分词：' + exchange['word_ing'][0] + '；'

        data['paraphrase_content'] += '\n' + exchange_txt

    if 'sameAnalysis' in message:
        sameAnalysis = message['sameAnalysis']
        sameAnalysis_txt = ''
        for s in sameAnalysis:
            if sameAnalysis_txt:
                sameAnalysis_txt += '\n\n'
            sameAnalysis_txt += s['part_name']
            for mean in s['means']:
                sameAnalysis_txt += '\n    ' + mean
        data['synonym_content'] = sameAnalysis_txt
    elif 'synonym' in message:
        synonym = message['synonym']
        synonym_txt = ''
        for sy in synonym:
            if 'means' in sy:
                for mean in sy['means']:
                    if synonym_txt:
                        synonym_txt += '\n\n'
                    synonym_txt += sy['part_name'] + mean['word_mean'] + '\n'
                    for c in mean['cis']:
                        synonym_txt += c + '  '
            else:
                if synonym_txt:
                    synonym_txt += '  '
                synonym_txt += sy['ci_name']
        data['synonym_content'] = synonym_txt

    if 'new_sentence' in message:
        sentences = message['new_sentence'][0]['sentences']
        sentence_txt = ''
        for sentence in sentences:
            if sentence_txt:
                sentence_txt += '\n'
            sentence_txt += sentence['en'] + ' ' + sentence['cn']
        data['sentence_content'] = sentence_txt

    if 'phrase' in message:
        phrase_txt = ''
        for phrase in message['phrase']:
            if phrase_txt:
                phrase_txt += '\n'
            phrase_txt += phrase['cizu_name']
            if len(phrase['jx']) > 0:
                jx = phrase['jx'][0]
                jx_cn_mean = jx['jx_cn_mean']
                if 'lj' in jx:
                    lj = jx['lj']
                    if jx_cn_mean:
                        phrase_txt += ' ' + jx_cn_mean
                    if len(lj) > 0:
                        phrase_txt += '\n    ' + lj[0]['lj_ly']
                        phrase_txt += '\n    ' + lj[0]['lj_ls']
            data['phrase_content'] = phrase_txt

    return data


terminal_size = os.get_terminal_size()
lines = terminal_size.lines
columns = terminal_size.columns - 7
div_line = '─' * columns

# 样式
palette = [('INPUT', 'light green', ''),
           ('BOX_BORDER', 'light blue', ''),
           ('TITLE', 'light magenta', '', ''),
           ('PH', 'brown', ''),
           ('SY', '', '', '', '#E8DAEF', ''), ]

word_input = urwid.Edit(('INPUT', u''))

word_input_padding = urwid.Padding(
    urwid.AttrWrap(word_input, 'INPUT'), left=2, right=2)

word_input_box = urwid.LineBox(
    word_input_padding, tlcorner='╭', trcorner='╮', blcorner='╰', brcorner='╯')
word_input_box = urwid.AttrWrap(word_input_box, '', 'BOX_BORDER')

phonation = urwid.Text('')
paraphrase_content = urwid.Text('')
phrase_title = urwid.Text('')
phrase_div = urwid.Text('')
paraphrase_title = urwid.Text('')
paraphrase_div = urwid.Text('')
phrase_content = urwid.Text('')
synonym_title = urwid.Text('')
synonym_div = urwid.Text('')
synonym_content = urwid.Text('')
sentence_title = urwid.Text('')
sentence_div = urwid.Text('')
sentence_content = urwid.Text('')


out_list = [
    urwid.AttrWrap(phonation, 'INPUT'),

    urwid.AttrWrap(paraphrase_title, 'TITLE'),
    urwid.AttrWrap(paraphrase_div, 'BOX_BORDER'),
    urwid.AttrWrap(paraphrase_content, 'PH'),

    urwid.AttrWrap(synonym_title, 'TITLE'),
    urwid.AttrWrap(synonym_div, 'BOX_BORDER'),
    urwid.AttrWrap(synonym_content, 'SY'),

    urwid.AttrWrap(phrase_title, 'TITLE'),
    urwid.AttrWrap(phrase_div, 'BOX_BORDER'),
    urwid.AttrWrap(phrase_content, 'PH'),

    urwid.AttrWrap(sentence_title, 'TITLE'),
    urwid.AttrWrap(sentence_div, 'BOX_BORDER'),
    urwid.AttrWrap(sentence_content, 'SY'),
]

list_box = urwid.ListBox(out_list)
box = urwid.Padding(list_box, left=2, right=2)
box = urwid.LineBox(box, tlcorner='╭', trcorner='╮',
                    blcorner='╰', brcorner='╯')
box = urwid.AttrWrap(box, '', 'BOX_BORDER')

result_out_box = urwid.BoxAdapter(box, height=lines - 3)

pile = urwid.Pile([
    word_input_box,
    result_out_box
])

top = urwid.Filler(pile, valign='top')
top = urwid.AttrWrap(top, 'body')


last_input = ''
last_out = ''

count = 0


def unhandled_input(k):
    global last_input
    global last_out
    if isinstance(k, str):
        if k in ('q', 'Q'):
            raise urwid.ExitMainLoop()
        if k == 'esc':
            pile.set_focus(result_out_box)
        if k == 'ctrl k':
            word_input.edit_text = ''
            pile.set_focus(word_input_box)
            clear()
        if k == 'ctrl d':
            list_box.keypress((200, lines - 8), 'page down')
        if k == 'ctrl u':
            list_box.keypress((200, lines - 8), 'page up')
        if k in 'enter':
            current_input = word_input.get_edit_text().strip()
            if current_input:
                if current_input != last_input:
                    clear()
                    data = translate(current_input)
                    last_input = current_input
                    last_out = data
                else:
                    data = last_out
                if data['phonation']:
                    phonation.set_text(data['phonation'])
                if data['paraphrase_content']:
                    paraphrase_title.set_text('\n释义')
                    paraphrase_div.set_text(div_line)
                    paraphrase_content.set_text(
                        data['paraphrase_content'])
                if data['synonym_content']:
                    synonym_title.set_text('\n同义词')
                    synonym_div.set_text(div_line)
                    synonym_content.set_text(data['synonym_content'])
                if data['sentence_content']:
                    sentence_title.set_text('\n例句')
                    sentence_div.set_text(div_line)
                    sentence_content.set_text(data['sentence_content'])
                if data['phrase_content']:
                    phrase_title.set_text('\n词组')
                    phrase_div.set_text(div_line)
                    phrase_content.set_text(data['phrase_content'])
    else:
        if k[0] == 'mouse press':
            global count
            if k[1] == 5.0:
                count += 1
                if count > 5:
                    list_box.keypress((200, 8), 'down')
                    count = 0
            elif k[1] == 4.0:
                count += 1
                if count > 5:
                    list_box.keypress((200, 8), 'up')
                    count = 0


def clear():
    phonation.set_text('')
    paraphrase_title.set_text('')
    paraphrase_div.set_text('')
    paraphrase_content.set_text('')
    phrase_title.set_text('')
    phrase_div.set_text('')
    phrase_content.set_text('')
    synonym_title.set_text('')
    synonym_div.set_text('')
    synonym_content.set_text('')
    sentence_title.set_text('')
    sentence_div.set_text('')
    sentence_content.set_text('')


screen = urwid.raw_display.Screen()
screen.register_palette(palette)
screen.set_terminal_properties(256)

if __name__ == '__main__':
    urwid.MainLoop(top, screen=screen, unhandled_input=unhandled_input).run()
