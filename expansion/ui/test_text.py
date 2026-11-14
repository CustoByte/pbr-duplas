import re,struct,unittest
from ui.accent_text import lexicon,restore
from ui.font_ptbr import prepare,blocks,records,bitmap
from ui.layout_text import wrap,preserve_alignment_breaks
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
    def test_seed_verb_accent_preserves_conjunction(self):
        text='Uma semente e plantada e drena HP para curar o usuario.'
        self.assertEqual(restore(text,lexicon()),'Uma semente é plantada e drena HP para curar o usuário.')
    def test_negative_possible_verb_accent(self):
        self.assertEqual(restore('Não e possível salvar HP e PP.',lexicon()),'Não é possível salvar HP e PP.')
    def test_ambiguous_e_is_not_globally_replaced(self):
        self.assertEqual(restore('Atk e Def',lexicon()),'Atk e Def')
    def test_new_font_letters_keep_original_glyphs(self):
        original=fixture_font();result,report=prepare(original)
        a,b=blocks(original)[0],blocks(result)[0];ra,rb=records(a),records(b)
        self.assertEqual(len(rb),len(ra)+4)
        for c,r in ra.items():self.assertEqual(bitmap(a,r),bitmap(b,rb[c]))
        for c in 'ãõÃÕ':
            self.assertIn(ord(c),rb)
            self.assertGreaterEqual(rb[ord(c)][3],1)
    def test_button_anchor_newline_is_preserved(self):
        source='{F001}{F101}{8011}{FFEF}\n{0003:0002}Colosseum Battle'
        target='{F001}{F101}{8011}{FFEF} {0003:0002}Coliseu'
        result,cases=wrap(source,target,metric)
        self.assertEqual(result,'{F001}{F101}{8011}{FFEF}\n{0003:0002}Coliseu')
    def test_mid_caption_alignment_restores_line(self):
        source='{F001}{F101}{0003:0002}Check{8011}{FFFA}\n{0003:0002}Moves'
        target='{F001}{F101}{0003:0002}Ver{8011}{FFFA} {0003:0002}golpes'
        fixed=preserve_alignment_breaks(source,target)
        self.assertIn('{FFFA}\n{0003:0002}',fixed)
        self.assertEqual(preserve_alignment_breaks(source,fixed),fixed)
    def test_alignment_keeps_intentional_blank_line(self):
        source='{F001}{F101}{0003:0002}One\n \n{0003:0002}Two'
        target='{F001}{F101}{0003:0002}Um\n\n{0003:0002}Dois'
        self.assertEqual(preserve_alignment_breaks(source,target),target)
    def test_inline_alignment_is_not_broken(self):
        source='{F001}{F101}{0003:0002}Check Moves'
        target='{F001}{F101}{0003:0002}Golpes'
        self.assertEqual(preserve_alignment_breaks(source,target),target)
    def test_pages_and_colors_are_preserved(self):
        source='{F001}{F101}{0027}In {0005:0001}Free Battle{0005:0005}, play\nwith a friend.{0028}{000D}\n{0027}Two players.{0028}{000D}'
        target='{F001}{F101}{0027}Na {0005:0001}Batalha Livre{0005:0005}, jogue com um amigo.{0028}{000D}\n{0027}Dois jogadores.{0028}{000D}'
        result,cases=wrap(source,target,metric)
        self.assertEqual(TOKEN.findall(source),TOKEN.findall(result))
        self.assertEqual(result.count('{000D}'),2)
        self.assertIn('{000D}\n{0027}',result)


class ScreenshotReviewTests(unittest.TestCase):
    def test_centering_keeps_native_control_set(self):
        from ui.apply_screenshot_review import validate
        source=encoded('{F001}{F101}{0005:0003}No Pokémon.\nCopy Pokémon first.')
        target='{F001}{F101}{0005:0003}   Sem Pokémon.\n   Copie Pokémon.'
        self.assertEqual(validate(source,target,8442,{}),encoded(target))
        with self.assertRaises(ValueError):validate(source,target.replace('   Sem','{0003:0002}Sem'),8442,{})
        with self.assertRaises(ValueError):validate(source,target.replace('{0005:0003}',''),8442,{})
    def test_name_and_level_fields_cannot_disappear(self):
        from ui.apply_screenshot_review import validate
        source=encoded('{F002}{F101}{0060} {0061}, {005F}\n{0062}\nMet at {FFFB} {0063}.')
        target='{F002}{F101}{0061} {0060} {005F}\n{0062}\nObtido no {FFFB} {0063}.'
        self.assertEqual(validate(source,target,8307,{}),encoded(target))
        with self.assertRaises(ValueError):validate(source,target.replace('{0063}',''),8307,{})

if __name__=='__main__':unittest.main()
