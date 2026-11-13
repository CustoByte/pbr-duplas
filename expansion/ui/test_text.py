import re,struct,unittest
from ui.accent_text import lexicon,restore
from ui.font_ptbr import prepare,blocks,records,bitmap
from ui.layout_text import wrap
from translation.messages import TOKEN,encoded

def metric(text):
    text=TOKEN.sub('',text);lines=text.split('\n')
    return max(map(len,lines))*8,len(lines)*20

def fixture_font():
    chars='AaOoâÂôÔ~'
    rows=[];glyphs=[];at=8+len(chars)*10
    for c in sorted(chars):
        top=3 if c in 'AaOo' else 0
        data=bytes([0xCC]*((8-top)*2))
        rows.append(struct.pack('>HBBBBI',ord(c),4,top,7,8,at));glyphs.append(data);at+=len(data)
    block=b'FONT'+struct.pack('>H',len(rows))+b'\x55\x20'+b''.join(rows)+b''.join(glyphs)
    return struct.pack('>I',4)+block

class TextFixTests(unittest.TestCase):
    def test_supported_accents_and_names(self):
        self.assertEqual(restore('{F001}Voce nao fara isso com Fire Punch.',lexicon(),['Fire Punch']),'{F001}Você não fará isso com Fire Punch.')
    def test_ambiguous_e_is_not_globally_replaced(self):
        self.assertEqual(restore('Atk e Def',lexicon()),'Atk e Def')
    def test_new_font_letters_keep_original_glyphs(self):
        original=fixture_font();result,report=prepare(original)
        a,b=blocks(original)[0],blocks(result)[0];ra,rb=records(a),records(b)
        self.assertEqual(len(rb),len(ra)+4)
        for c,r in ra.items():self.assertEqual(bitmap(a,r),bitmap(b,rb[c]))
        for c in 'ãõÃÕ':self.assertIn(ord(c),rb)
    def test_button_anchor_newline_is_preserved(self):
        source='{F001}{F101}{8011}{FFEF}\n{0003:0002}Colosseum Battle'
        target='{F001}{F101}{8011}{FFEF} {0003:0002}Coliseu'
        result,cases=wrap(source,target,metric)
        self.assertEqual(result,'{F001}{F101}{8011}{FFEF}\n{0003:0002}Coliseu')
    def test_pages_and_colors_are_preserved(self):
        source='{F001}{F101}{0027}In {0005:0001}Free Battle{0005:0005}, play\nwith a friend.{0028}{000D}\n{0027}Two players.{0028}{000D}'
        target='{F001}{F101}{0027}Na {0005:0001}Batalha Livre{0005:0005}, jogue com um amigo.{0028}{000D}\n{0027}Dois jogadores.{0028}{000D}'
        result,cases=wrap(source,target,metric)
        self.assertEqual(TOKEN.findall(source),TOKEN.findall(result))
        self.assertEqual(result.count('{000D}'),2)
        self.assertIn('{000D}\n{0027}',result)

if __name__=='__main__':unittest.main()
