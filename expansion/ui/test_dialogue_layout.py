import unittest
from translation.messages import TOKEN
from ui.dialogue_layout import (PAGE,can_paginate,protected_words,reflow,validate_layout,paginate_words)
from ui.dialogue_editorial import concise,validate_editorial


def metric(text):
    lines=TOKEN.sub('',text).split('\n')
    return max(map(len,lines))*8,len(lines)*20


class DialogueLayoutTests(unittest.TestCase):
    def test_extra_pages_only_in_interactive_common_messages(self):
        source='{F001}{F101}{0027}Text.{0028}{0067}'
        self.assertTrue(can_paginate('common',source))
        self.assertFalse(can_paginate('battle',source))
        self.assertFalse(can_paginate('tutorial',source))
        self.assertFalse(can_paginate('common',source.replace('{0067}','')))
        self.assertFalse(can_paginate('common',source+'{0002:000A}'))
        self.assertFalse(can_paginate('common',source+'{0003:0002}'))

    def test_layout_cannot_rewrite_names_or_numbers(self):
        before='{F001}{F101}Fire Punch causa 20 de dano.'
        validate_layout(before,before.replace(' causa','\ncausa'))
        for after in (before.replace('Fire Punch','Soco de Fogo'),before.replace('20','30')):
            with self.assertRaises(ValueError):validate_layout(before,after)

    def test_added_page_requires_explicit_gate(self):
        before='{F001}{F101}Uma frase inteira.{0067}'
        after=before.replace('frase ', 'frase'+PAGE+'\n')
        with self.assertRaises(ValueError):validate_layout(before,after)
        validate_layout(before,after,allow_pages=True)
        with self.assertRaises(ValueError):validate_layout(after,before,allow_pages=True)

    def test_parameter_order_must_not_change(self):
        before='{F001}{F101}{0025} ataca {002C}.'
        with self.assertRaises(ValueError):
            validate_layout(before,'{F001}{F101}{002C} ataca {0025}.')

    def test_multiword_native_names_are_atomic(self):
        words=protected_words('Usa Energy Ball e segura Black Sludge.',{'Energy Ball','Black Sludge'})
        self.assertIn('Energy Ball',words)
        self.assertIn('Black Sludge.',words)
        self.assertNotIn('Energy',words)

    def test_native_style_is_not_repeated_on_added_pages(self):
        source='{F001}{F101}{0027}One two\nthree four.{0028}{0067}'
        target='{F001}{F101}{0027}Um dois três quatro cinco seis sete oito nove dez.{0028}{0067}'
        result,report=reflow('common',9000,source,target,metric)
        self.assertEqual(report['status'],'bounded')
        self.assertGreater(report['extra_pages'],0)
        for token in ('{F001}','{F101}','{0067}'):
            self.assertEqual(result.count(token),1)
        self.assertEqual(result.count('{0027}'),1+report['extra_pages'])
        self.assertEqual(result.count('{0028}'),1+report['extra_pages'])
        self.assertIn('{0028}{000D}\n{0027}',result)
        validate_layout(target,result,allow_pages=True)

    def test_static_description_cannot_gain_pages(self):
        source='{F001}{F101}Short text.'
        target='{F001}{F101}Uma descrição muito comprida para esta caixa fixa.'
        result,report=reflow('common',3200,source,target,metric)
        self.assertNotIn(PAGE,result)
        self.assertEqual(report['status'],'needs-editorial-review')

    def test_button_alignment_is_preserved(self):
        source='{F001}{F101}{0003:0002}First\n{0003:0002}Second'
        target='{F001}{F101}{0003:0002}Um {0003:0002}Dois'
        result,_=reflow('common',9000,source,target,metric)
        self.assertIn('\n{0003:0002}',result)
        self.assertNotIn(PAGE,result)

    def test_word_longer_than_box_is_not_truncated(self):
        text='Supercalifragilisticexpialidocious'
        self.assertIsNone(paginate_words('{F001}{F101}','',[text],40,40,metric,False))

    def test_concise_description_preserves_mechanics_and_names(self):
        before='{F001}{F101}O usuário ataca com Fire Punch por 5 turnos.'
        after,rules=concise(before)
        self.assertIn('Ataca com Fire Punch por 5 turnos.',after)
        self.assertTrue(rules)
        validate_editorial(before,after,{'Fire Punch'})
        with self.assertRaises(ValueError):validate_editorial(before,after.replace('5','3'),{'Fire Punch'})
        with self.assertRaises(ValueError):validate_editorial(before,after.replace('Fire Punch','Soco'),{'Fire Punch'})

    def test_editorial_can_use_validated_continuation(self):
        before='{F001}{F101}{0027}O usuário usa Energy Ball.{0028}{0067}'
        after='{F001}{F101}{0027}Usa{0028}{000D}\n{0027}Energy Ball.{0028}{0067}'
        validate_editorial(before,after,{'Energy Ball'},allow_pages=True)
        with self.assertRaises(ValueError):validate_editorial(before,after,{'Energy Ball'})

    def test_reflow_reuses_only_pages_of_same_dialogue(self):
        source='{F001}{F101}{0027}Hi.{0028}{000D}\n{0027}A longer source\nwith two lines.{0028}{0067}'
        target='{F001}{F101}{0027}Olá, tudo bem?{0028}{000D}\n{0027}Outro trecho.{0028}{0067}'
        result,report=reflow('common',9000,source,target,metric)
        self.assertEqual(report['status'],'bounded')
        self.assertEqual(report['extra_pages'],0)

    def test_editorial_cannot_drop_negation(self):
        before='{F001}{F101}O usuário não pode agir por 2 turnos.'
        with self.assertRaises(ValueError):validate_editorial(before,before.replace('não ',''))


if __name__=='__main__':unittest.main()
