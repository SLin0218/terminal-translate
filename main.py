#!/usr/bin/env python3
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
    # 翻译句子
    if word.count(' ') > 0:
        # 中文
        if zh_re.search(word):
            return translate_sentence(word, True)
        else:
            return translate_sentence(word)
    # 翻译单词
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


class Translate:

    palette = [('INPUT', 'light green', ''),
               ('BOX_BORDER', 'light blue', ''),
               ('TITLE', 'light magenta', '', ''),
               ('PH', 'brown', ''),
               ('SY', '', '', '', '#E8DAEF', ''), ]

    def line(self):
        terminal_size = os.get_terminal_size()
        return '─' * (terminal_size.columns - 7)

    def setup_top(self):
        self.edit_original = urwid.Edit(('INPUT', u''))
        self.edit_original = urwid.AttrWrap(self.edit_original, 'INPUT')
        self.edit = urwid.Padding(self.edit_original, left=2, right=2)
        self.edit = urwid.LineBox(
            self.edit, tlcorner='╭', trcorner='╮',
            blcorner='╰', brcorner='╯')
        self.edit = urwid.AttrWrap(self.edit, '', 'BOX_BORDER')

    def setup_result(self):
        self.phonation = urwid.Text('')
        self.paraphrase_content = urwid.Text('')
        self.phrase_title = urwid.Text('')
        self.phrase_div = urwid.Text('')
        self.paraphrase_title = urwid.Text('')
        self.paraphrase_div = urwid.Text('')
        self.phrase_content = urwid.Text('')
        self.synonym_title = urwid.Text('')
        self.synonym_div = urwid.Text('')
        self.synonym_content = urwid.Text('')
        self.sentence_title = urwid.Text('')
        self.sentence_div = urwid.Text('')
        self.sentence_content = urwid.Text('')

        self.list_box = urwid.ListBox([
            urwid.AttrWrap(self.phonation, 'INPUT'),
            urwid.AttrWrap(self.paraphrase_title, 'TITLE'),
            urwid.AttrWrap(self.paraphrase_div, 'BOX_BORDER'),
            urwid.AttrWrap(self.paraphrase_content, 'PH'),
            urwid.AttrWrap(self.synonym_title, 'TITLE'),
            urwid.AttrWrap(self.synonym_div, 'BOX_BORDER'),
            urwid.AttrWrap(self.synonym_content, 'SY'),
            urwid.AttrWrap(self.phrase_title, 'TITLE'),
            urwid.AttrWrap(self.phrase_div, 'BOX_BORDER'),
            urwid.AttrWrap(self.phrase_content, 'PH'),
            urwid.AttrWrap(self.sentence_title, 'TITLE'),
            urwid.AttrWrap(self.sentence_div, 'BOX_BORDER'),
            urwid.AttrWrap(self.sentence_content, 'SY'),
        ])
        box = urwid.LineBox(urwid.Padding(self.list_box, left=2, right=2),
                            tlcorner='╭', trcorner='╮',
                            blcorner='╰', brcorner='╯')
        self.result_out_box = urwid.AttrWrap(box, '', 'BOX_BORDER')

    def setup_view(self):
        self.setup_top()
        self.setup_result()
        self.view = urwid.Frame(self.result_out_box, self.edit, None, 'header')

    def main(self):
        self.setup_view()
        screen = urwid.raw_display.Screen()
        screen.register_palette(self.palette)
        screen.set_terminal_properties(256)
        mainloop = urwid.MainLoop(self.view, screen=screen,
                                  unhandled_input=self.unhandled_input)
        try:
            mainloop.run()
        except KeyboardInterrupt:
            pass

    # def refresh(self, loop=None, data=None):
    #     self.setup_view()
    #     loop.widget = self.view
    #     loop.set_alarm_in(1, self.refresh)

    def unhandled_input(self, k):
        # global last_input
        # global last_out
        if isinstance(k, str):
            if k in ('q', 'Q'):
                raise urwid.ExitMainLoop()
            if k == 'esc':
                self.view.set_focus('body')
            if k == 'ctrl k':
                self.edit_original.set_edit_text('')
                self.view.set_focus('header')
                self.clear()

            if k == 'up' and self.view.get_focus() == 'body':
                self.view.set_focus('header')

            if k == 'down' and self.view.get_focus() == 'header':
                self.view.set_focus('body')

            if k in 'enter':
                current_input = self.edit_original.get_edit_text().strip()
                if current_input:
                    data = translate(current_input)
                    if data['phonation']:
                        self.phonation.set_text(data['phonation'])
                    if data['paraphrase_content']:
                        self.paraphrase_title.set_text('\n释义')
                        self.paraphrase_div.set_text(self.line())
                        self.paraphrase_content.set_text(
                            data['paraphrase_content'])
                    if data['synonym_content']:
                        self.synonym_title.set_text('\n同义词')
                        self.synonym_div.set_text(self.line())
                        self.synonym_content.set_text(data['synonym_content'])
                    if data['sentence_content']:
                        self.sentence_title.set_text('\n例句')
                        self.sentence_div.set_text(self.line())
                        self.sentence_content.set_text(
                            data['sentence_content'])
                    if data['phrase_content']:
                        self.phrase_title.set_text('\n词组')
                        self.phrase_div.set_text(self.line())
                        self.phrase_content.set_text(data['phrase_content'])

    def clear(self):
        self.phonation.set_text('')
        self.paraphrase_title.set_text('')
        self.paraphrase_div.set_text('')
        self.paraphrase_content.set_text('')
        self.phrase_title.set_text('')
        self.phrase_div.set_text('')
        self.phrase_content.set_text('')
        self.synonym_title.set_text('')
        self.synonym_div.set_text('')
        self.synonym_content.set_text('')
        self.sentence_title.set_text('')
        self.sentence_div.set_text('')
        self.sentence_content.set_text('')


if __name__ == '__main__':
    translat = Translate()
    translat.main()
