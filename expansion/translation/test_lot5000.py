"""Regression checks for actual large-lot terminology and data corruption risks."""
import unittest
from translation.review_lot5000 import prepare

class LargeLotTests(unittest.TestCase):
    def review(self,source,target,protected=()):
        inventory={'entries':[{'archive':'mes_common.fsys','id':999999,'source':'{F001}{F101}'+source}]}
        return prepare(inventory,{' '.join(source.split()):{'target':target}},list(protected))

    def test_switch_action_not_electrical_switch(self):
        r=self.review('SWITCH','INTERRUPTOR')
        self.assertEqual(r['entries'][0]['target'],'{F001}{F101}TROCAR')

    def test_stat_abbreviation_not_adverb(self):
        r=self.review('Sp. Def','Sp. Definitivamente')
        self.assertEqual(r['entries'][0]['target'],'{F001}{F101}Def. Esp.')

    def test_type_translation_preserves_move_name(self):
        r=self.review('A Fire-type move called Fire Punch.','Um movimento do tipo Fire chamado Fire Punch.',['Fire Punch'])
        text=r['entries'][0]['target']
        self.assertIn('tipo Fogo',text)
        self.assertIn('Fire Punch',text)

    def test_changed_effect_numbers_are_rejected(self):
        r=self.review('Restores 20 HP.','Recupera 200 HP.')
        self.assertFalse(r['entries'])
        self.assertEqual(r['issues'][0]['reason'],'changed-numeric-values')

    def test_localized_thousands_keep_numeric_value(self):
        r=self.review('Holds 50,000 coins.','Guarda 50.000 moedas.')
        self.assertEqual(len(r['entries']),1)

    def test_missing_dynamic_field_is_rejected(self):
        r=self.review('Choose {0015}.','Escolha o Pokémon.')
        self.assertFalse(r['entries'])
        self.assertEqual(r['issues'][0]['reason'],'changed-control-fields')

    def test_font_incompatible_punctuation_is_removed(self):
        r=self.review('Number 1.','Nº 1.\u200b')
        self.assertEqual(r['entries'][0]['target'],'{F001}{F101}N. 1.')

    def test_unchanged_text_is_not_new_translation(self):
        r=self.review('Pokémon\n','Pokémon',['Pokémon'])
        self.assertFalse(r['entries'])
        self.assertFalse(r['issues'])

if __name__=='__main__':unittest.main()
